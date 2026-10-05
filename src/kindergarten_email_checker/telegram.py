"""Telegram Bot API client (docs/ARCHITECTURE.md, section 9)."""

from __future__ import annotations

from kindergarten_email_checker.config import Settings
from kindergarten_email_checker.content import EmailContent
from kindergarten_email_checker.summarize import Summary

API = "https://api.telegram.org"
MAX_MESSAGE_CHARS = 4096
URGENCY_MARK = {"high": "🔴", "normal": "🟡", "low": "🟢"}


def format_message(summary: Summary, content: EmailContent) -> str:
    """Render the HTML message: header, title, summary, action, attachments, original, footer."""
    raise NotImplementedError


def send_summary(summary: Summary, content: EmailContent, settings: Settings) -> int:
    """sendMessage with HTML parse mode. Returns the message id."""
    raise NotImplementedError


def send_original(content: EmailContent, settings: Settings) -> int:
    """Fallback when the model output is unusable: subject, sender and the original text."""
    raise NotImplementedError


def send_error(subject: str, error: str, settings: Settings) -> None:
    """Post a processing error to the group, at most once per message."""
    raise NotImplementedError
