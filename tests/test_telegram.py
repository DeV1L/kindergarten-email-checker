from datetime import date

import pytest
from helpers import make_message, make_settings

from kindergarten_email_checker import telegram
from kindergarten_email_checker.content import extract
from kindergarten_email_checker.summarize import Summary
from kindergarten_email_checker.telegram import (
    format_message,
    format_original,
    ru_date,
)


def summary(**overrides):
    values = dict(
        title_ru="Экскурсия <в парк>",
        summary_ru="В пятницу экскурсия.",
        urgency="high",
        category="action_required",
        action_ru="Подписать разрешение",
        deadline="2026-10-09",
        event_date="2026-10-20",
        event_time="10:00",
    )
    values.update(overrides)
    return Summary.model_validate(values)


def content(text="Hola familias & niños"):
    message = make_message(text=text, attachments=[("autorizacion.pdf", "application/pdf", b"x")])
    return extract(message, make_settings())


def test_ru_date():
    assert ru_date(date(2026, 10, 9)) == "пт, 9 окт"


def test_message_layout_and_escaping():
    text = format_message(summary(), content(), make_settings())
    assert text.splitlines()[0] == (
        "🔴 High · ✍️ Нужно действие · ⏰ Срок: пт, 9 окт · 📅 Событие: вт, 20 окт 10:00"
    )
    assert "<b>Экскурсия &lt;в парк&gt;</b>" in text
    assert "<b>Что сделать:</b> Подписать разрешение" in text
    assert "📎 Вложения: autorizacion.pdf" in text
    assert "Hola familias" not in text  # the original is not quoted
    assert text.endswith(
        "<i>Тема: Excursión · От: direccion@kinder.example · Отправлено: пн, 5 окт 2026 10:00</i>"
    )


def test_absent_fields_are_left_out():
    text = format_message(
        summary(urgency="low", category="info", action_ru=None, deadline=None, event_date=None),
        content(),
        make_settings(),
    )
    assert text.splitlines()[0] == "🟢 Low · ℹ️ Информация"
    assert "Что сделать" not in text


def test_long_original_in_fallback_is_trimmed_to_the_limit():
    text = format_original(content(text="<&>" * 5000), make_settings())
    assert len(text) <= make_settings().telegram_max_message_chars
    assert "…</blockquote>" in text
    assert "&am</blockquote>" not in text  # no cut inside an escape


def test_fallback_message_keeps_original():
    text = format_original(content(), make_settings())
    assert "Без сводки" in text
    assert "Hola familias &amp; niños" in text


class FakeResponse:
    def __init__(self, status_code, data):
        self.status_code = status_code
        self.data = data

    def json(self):
        return self.data


def test_check_raises_without_the_token_in_the_message(monkeypatch):
    settings = make_settings()
    answer = FakeResponse(401, {"ok": False, "description": "Unauthorized"})
    monkeypatch.setattr(telegram.httpx2, "post", lambda url, json, timeout: answer)
    with pytest.raises(telegram.TelegramError) as error:
        telegram.check(settings)
    assert str(error.value) == "getChat failed: 401 Unauthorized"
    assert settings.telegram_bot_token not in str(error.value)


def test_send_message_returns_the_message_id(monkeypatch):
    calls = []

    def post(url, json, timeout):
        calls.append((url.rsplit("/", 1)[1], json["chat_id"]))
        return FakeResponse(200, {"ok": True, "result": {"message_id": 42}})

    monkeypatch.setattr(telegram.httpx2, "post", post)
    assert telegram.send_message("text", make_settings()) == 42
    assert calls == [("sendMessage", "-1001")]
