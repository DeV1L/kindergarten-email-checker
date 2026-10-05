"""The model call (docs/ARCHITECTURE.md, section 8).

One Anthropic Messages API request to DeepSeek with thinking enabled. The summary comes back
as the input of a forced `report_summary` tool call and is validated against `Summary`.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from kindergarten_email_checker.config import Settings
from kindergarten_email_checker.content import EmailContent

TOOL_NAME = "report_summary"
SYSTEM_PROMPT = (Path(__file__).parent / "prompt.md").read_text(encoding="utf-8")

Urgency = Literal["low", "normal", "high"]
Category = Literal["info", "event", "action_required", "payment", "closure", "health", "other"]


class Summary(BaseModel):
    """What the model reports for one email. Field descriptions are part of the tool schema."""

    title_ru: str = Field(description="Заголовок одной строкой, до 60 символов")
    summary_ru: str = Field(description="Суть письма в 2–4 предложениях")
    urgency: Urgency = Field(
        description=(
            "high: действовать в ближайшие 2 дня, отмена или закрытие, здоровье и безопасность; "
            "normal: есть действие или событие позже; low: только информация"
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


def tool_definition() -> dict:
    """Tool whose input schema is the Summary model, for the `tools` request parameter."""
    return {
        "name": TOOL_NAME,
        "description": "Report the structured Russian summary of the kindergarten email.",
        "input_schema": Summary.model_json_schema(),
    }


def summarize(content: EmailContent, settings: Settings) -> Summary:
    """Call the model with thinking on and a forced tool call, validate, retry once. Pending."""
    raise NotImplementedError
