"""Telegram Bot API client (docs/ARCHITECTURE.md, section 9)."""

from __future__ import annotations

from datetime import date
from html import escape

import httpx

from kindergarten_email_checker.config import Settings
from kindergarten_email_checker.content import EmailContent
from kindergarten_email_checker.summarize import Summary

API = "https://api.telegram.org"
MAX_MESSAGE_CHARS = 4096
TIMEOUT_SECONDS = 30

URGENCY_LABEL = {"high": "🔴 High", "medium": "🟡 Medium", "low": "🟢 Low"}
CATEGORY_LABEL = {
    "info": "ℹ️ Информация",
    "event": "🎉 Мероприятие",
    "action_required": "✍️ Нужно действие",
    "payment": "💰 Оплата",
    "closure": "🔄 Изменение расписания",
    "health": "🩺 Здоровье",
    "other": "📌 Другое",
}
WEEKDAYS = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"]
MONTHS = ["янв", "фев", "мар", "апр", "мая", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"]


class TelegramError(Exception):
    pass


def ru_date(value: date) -> str:
    """2026-10-10 -> 'сб, 10 окт'."""
    return f"{WEEKDAYS[value.weekday()]}, {value.day} {MONTHS[value.month - 1]}"


def format_message(summary: Summary, content: EmailContent) -> str:
    """Render the HTML message: header, title, summary, action, attachments, footer.

    The original email is not quoted. It stays in the dedicated mailbox.
    """
    header = [URGENCY_LABEL[summary.urgency], CATEGORY_LABEL[summary.category]]
    if summary.deadline:
        header.append(f"⏰ Срок: {ru_date(summary.deadline)}")
    if summary.event_date:
        when = ru_date(summary.event_date)
        if summary.event_time:
            when += f" {summary.event_time}"
        header.append(f"📅 Событие: {when}")

    top = [" · ".join(header), f"<b>{escape(summary.title_ru)}</b>", "", escape(summary.summary_ru)]
    if summary.action_ru:
        top += ["", f"<b>Что сделать:</b> {escape(summary.action_ru)}"]
    if content.attachment_names:
        top.append("📎 Вложения: " + escape(", ".join(content.attachment_names)))
    top += ["", footer(content)]
    return "\n".join(top)[:MAX_MESSAGE_CHARS]


def footer(content: EmailContent) -> str:
    """Subject, sender and the email's send date in the configured timezone."""
    sent = f"{ru_date(content.sent_at.date())} {content.sent_at:%Y %H:%M}"
    parts = [
        f"Тема: {escape(content.subject)}",
        f"От: {escape(content.sender)}",
        f"Отправлено: {sent}",
    ]
    return f"<i>{' · '.join(parts)}</i>"


def format_original(content: EmailContent) -> str:
    """Fallback message when the model output is unusable. The only post that quotes the email."""
    top = ["⚠️ <b>Без сводки</b>: модель не вернула результат. Оригинал письма:"]
    if content.attachment_names:
        top.append("📎 Вложения: " + escape(", ".join(content.attachment_names)))
    return with_original("\n".join(top), content)


def with_original(top: str, content: EmailContent) -> str:
    """Add the original text in a collapsed quote and the footer, within Telegram's limit."""
    end_line = footer(content)
    start, end = "\n\n<blockquote expandable>", "</blockquote>\n"
    budget = MAX_MESSAGE_CHARS - len(top) - len(start) - len(end) - len(end_line)
    original = content.text
    if len(escape(original)) > budget:
        original = original[: max(budget - 1, 0)]
        while original and len(escape(original)) + 1 > budget:
            original = original[: len(original) - 50]
        original = original + "…" if original else ""
    if not original:
        return f"{top}\n\n{end_line}"[:MAX_MESSAGE_CHARS]
    return f"{top}{start}{escape(original)}{end}{end_line}"


def send_message(text: str, settings: Settings) -> int:
    """sendMessage with HTML parse mode. Returns the message id."""
    response = httpx.post(
        f"{API}/bot{settings.telegram_bot_token}/sendMessage",
        json={
            "chat_id": settings.telegram_chat_id,
            "text": text,
            "parse_mode": "HTML",
            "link_preview_options": {"is_disabled": True},
        },
        timeout=TIMEOUT_SECONDS,
    )
    data = response.json()
    if not data.get("ok"):
        # Build the error by hand: httpx errors include the URL, and the URL contains the token.
        raise TelegramError(f"sendMessage failed: {response.status_code} {data.get('description')}")
    return data["result"]["message_id"]


def send_summary(summary: Summary, content: EmailContent, settings: Settings) -> int:
    return send_message(format_message(summary, content), settings)


def send_original(content: EmailContent, settings: Settings) -> int:
    return send_message(format_original(content), settings)


def send_error(subject: str, error: str, settings: Settings) -> None:
    """Post a processing error to the group."""
    text = f"⚠️ Не удалось обработать письмо «{escape(subject)}»: {escape(error[:500])}"
    send_message(text, settings)
