"""The model call (docs/ARCHITECTURE.md, section 8).

One Anthropic Messages API request to DeepSeek with thinking enabled. The summary comes back
as the input of a `report_summary` tool call and is validated against `Summary`.
The start check reads the DeepSeek balance.
"""

from __future__ import annotations

import base64
import json
import logging
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo

import anthropic
import httpx
from pydantic import BaseModel, Field, ValidationError, field_validator

from kindergarten_email_checker.config import Settings
from kindergarten_email_checker.content import EmailContent

log = logging.getLogger(__name__)

SYSTEM_PROMPT = (Path(__file__).parent / "prompt.md").read_text(encoding="utf-8")

Urgency = Literal["low", "medium", "high"]
Category = Literal["info", "event", "action_required", "payment", "closure", "health", "other"]
NO_VALUE = {"", "null", "none"}


class Summary(BaseModel):
    """What the model reports for one email. Field descriptions are part of the tool schema."""

    title_ru: str = Field(description="Заголовок одной строкой, до 60 символов")
    summary_ru: str = Field(description="Суть письма, до 3 коротких предложений, до 350 символов")
    urgency: Urgency = Field(
        description=(
            "high: действовать в ближайшие 2 дня или меняется посещение в ближайшие 2 дня; "
            "medium: действие или событие позже; low: ничего делать не нужно"
        )
    )
    category: Category
    action_ru: str | None = Field(
        default=None, description="Что должен сделать родитель, одной строкой; null если ничего"
    )
    deadline: date | None = Field(
        default=None, description="Дата, к которой нужно действовать: ответить, оплатить, принести"
    )
    event_date: date | None = Field(default=None, description="Дата самого события")
    event_time: str | None = Field(
        default=None, description="Время события в формате HH:MM, если указано"
    )

    @field_validator("action_ru", "deadline", "event_date", "event_time", mode="before")
    @classmethod
    def text_null_is_none(cls, value):
        """The model sometimes writes the text "null" instead of JSON null. Treat it as no value."""
        if isinstance(value, str) and value.strip().lower() in NO_VALUE:
            return None
        return value


def tool_definition(settings: Settings) -> dict:
    """Tool whose input schema is the Summary model, for the `tools` request parameter."""
    return {
        "name": settings.llm_tool_name,
        "description": "Report the structured Russian summary of the kindergarten email.",
        "input_schema": Summary.model_json_schema(),
    }


class BalanceError(Exception):
    pass


def check_balance(settings: Settings) -> str:
    """GET /user/balance. Fails on a wrong key or a zero balance. Returns the balance as text."""
    response = httpx.get(
        httpx.URL(settings.llm_base_url).join("/user/balance"),
        headers={"Authorization": f"Bearer {settings.llm_api_key}"},
        timeout=settings.llm_balance_timeout_seconds,
    )
    data = response.json()
    if response.status_code != 200:
        message = data.get("error", {}).get("message")
        raise BalanceError(f"user/balance failed: {response.status_code} {message}")
    balances = [
        f"{info['total_balance']} {info['currency']}"
        for info in data["balance_infos"]
        if Decimal(info["total_balance"]) > 0
    ]
    if not balances:
        raise BalanceError("the DeepSeek balance is zero")
    return ", ".join(balances)


def make_client(settings: Settings) -> anthropic.Anthropic:
    return anthropic.Anthropic(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        timeout=settings.llm_timeout_seconds,
    )


def summarize(
    content: EmailContent, settings: Settings, client: anthropic.Anthropic | None = None
) -> Summary | None:
    """Ask the model for a Summary. One retry on invalid output. None after two invalid outputs.

    API errors (timeout, 5xx, 429 after the SDK's own retries) are raised to the caller.
    """
    client = client or make_client(settings)
    tool_name = settings.llm_tool_name
    messages: list[dict] = [{"role": "user", "content": user_content(content, settings)}]
    for attempt in (1, 2):
        response = client.messages.create(
            model=settings.llm_model,
            max_tokens=settings.llm_max_tokens,
            system=SYSTEM_PROMPT.replace("{TOOL_NAME}", tool_name),
            messages=messages,
            tools=[tool_definition(settings)],
            # DeepSeek rejects a forced tool_choice with thinking on. prompt.md asks for the call.
            tool_choice={"type": "auto"},
            thinking={"type": "enabled", "budget_tokens": 8000},  # DeepSeek ignores the budget
            output_config={"effort": settings.llm_effort},
        )
        tool_use = next(
            (b for b in response.content if b.type == "tool_use" and b.name == tool_name), None
        )
        if tool_use is None:
            problem = {"problem": f"no {tool_name} call", "stop_reason": response.stop_reason}
            retry_turn = {"role": "user", "content": f"Call the {tool_name} tool."}
        else:
            try:
                return Summary.model_validate(tool_use.input)
            except ValidationError as error:
                problem = {
                    "problem": f"invalid {tool_name} input",
                    "input": tool_use.input,
                    "errors": json.loads(error.json(include_url=False)),
                }
                retry_turn = {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_use.id,
                            "is_error": True,
                            "content": f"{error}\nCall {tool_name} again with corrected input.",
                        }
                    ],
                }
        # One line with a JSON object, so the log stays one line per event.
        log.warning(
            "uid=%s attempt %d: %s", content.uid, attempt, json.dumps(problem, ensure_ascii=False)
        )
        messages += [{"role": "assistant", "content": response.content}, retry_turn]
    return None


def user_content(content: EmailContent, settings: Settings) -> list[dict]:
    """Metadata, body and PDF texts as one text block, then the images."""
    today = datetime.now(ZoneInfo(settings.tz))
    parts = [
        f"From: {content.sender}",
        f"Subject: {content.subject}",
        f"Sent: {content.sent_at:%Y-%m-%d %H:%M, %A} ({settings.tz})",
        f"Today: {today:%Y-%m-%d, %A}",
        "",
        "Body:",
        content.text or "(empty)",
    ]
    for name, text in content.pdf_texts:
        parts += ["", f"PDF attachment {name}:", text]
    if content.not_sent_to_model:
        parts += ["", "Attachments not shown to you: " + ", ".join(content.not_sent_to_model)]
    if content.images:
        parts += ["", "Images from attachments and scanned PDF pages follow."]
    blocks: list[dict] = [{"type": "text", "text": "\n".join(parts)}]
    for media_type, data in content.images:
        blocks.append(
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": base64.b64encode(data).decode(),
                },
            }
        )
    return blocks
