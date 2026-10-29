import json
import logging
from datetime import date
from types import SimpleNamespace

import pytest
from helpers import make_message, make_settings

from kindergarten_email_checker import summarize as summarize_module
from kindergarten_email_checker.content import extract
from kindergarten_email_checker.summarize import Summary, summarize

TOOL_NAME = make_settings().llm_tool_name

VALID = {
    "title_ru": "Экскурсия в парк",
    "summary_ru": "В пятницу экскурсия.",
    "urgency": "high",
    "category": "action_required",
    "action_ru": "Подписать разрешение",
    "deadline": "2026-10-09",
    "event_date": "2026-10-20",
    "event_time": "10:00",
}


def tool_response(tool_input, name=TOOL_NAME):
    return SimpleNamespace(
        stop_reason="tool_use",
        content=[
            SimpleNamespace(type="thinking", thinking=""),
            SimpleNamespace(type="tool_use", name=name, id="toolu_1", input=tool_input),
        ],
    )


def text_response():
    return SimpleNamespace(
        stop_reason="end_turn", content=[SimpleNamespace(type="text", text="hi")]
    )


class FakeClient:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []
        self.messages = self

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.responses.pop(0)


def content():
    return extract(make_message(), make_settings())


def test_valid_tool_call_returns_summary():
    client = FakeClient(tool_response(VALID))
    summary = summarize(content(), make_settings(), client)
    assert summary.deadline == date(2026, 10, 9)
    request = client.calls[0]
    assert request["tool_choice"] == {"type": "auto"}
    assert request["thinking"]["type"] == "enabled"
    assert request["output_config"] == {"effort": "high"}
    assert "Sent: 2026-10-05 10:00, Monday" in request["messages"][0]["content"][0]["text"]


def test_invalid_input_is_retried_with_tool_result_error():
    client = FakeClient(tool_response({**VALID, "urgency": "urgent"}), tool_response(VALID))
    assert summarize(content(), make_settings(), client).urgency == "high"
    retry = client.calls[1]["messages"]
    assert retry[1]["role"] == "assistant"
    assert retry[2]["content"][0]["type"] == "tool_result"
    assert retry[2]["content"][0]["is_error"] is True


def test_invalid_input_is_logged_as_one_line_of_json(caplog):
    client = FakeClient(tool_response({}), tool_response(VALID))
    with caplog.at_level(logging.WARNING):
        summarize(content(), make_settings(), client)
    [record] = caplog.records
    message = record.getMessage()
    assert "\n" not in message
    logged = json.loads(message.split(": ", 1)[1])
    assert logged["problem"] == "invalid report_summary input"
    assert logged["input"] == {}
    assert {tuple(e["loc"]) for e in logged["errors"]} == {
        ("title_ru",),
        ("summary_ru",),
        ("urgency",),
        ("category",),
    }
    assert "url" not in logged["errors"][0]


def test_bad_answers_up_to_model_tries_return_none():
    client = FakeClient(text_response(), text_response(), text_response())
    assert summarize(content(), make_settings(llm_model_tries=3), client) is None
    assert len(client.calls) == 3


def test_text_null_means_no_value():
    summary = Summary.model_validate(
        {**VALID, "action_ru": "null", "deadline": "None", "event_date": " ", "event_time": ""}
    )
    fields = [summary.action_ru, summary.deadline, summary.event_date, summary.event_time]
    assert fields == [None, None, None, None]


class FakeResponse:
    def __init__(self, status_code, data):
        self.status_code = status_code
        self.data = data

    def json(self):
        return self.data


def balance_answer(monkeypatch, status_code, data):
    calls = []

    def get(url, headers, timeout):
        calls.append(str(url))
        return FakeResponse(status_code, data)

    monkeypatch.setattr(summarize_module.httpx2, "get", get)
    return calls


def balance(total):
    info = {
        "currency": "USD",
        "total_balance": total,
        "granted_balance": "0",
        "topped_up_balance": total,
    }
    return {"is_available": total != "0.00", "balance_infos": [info]}


def test_check_balance_returns_the_balance(monkeypatch):
    calls = balance_answer(monkeypatch, 200, balance("1.87"))
    assert summarize_module.check_balance(make_settings()) == "1.87 USD"
    assert calls == ["https://api.deepseek.com/user/balance"]


def test_check_balance_fails_when_not_available(monkeypatch):
    balance_answer(monkeypatch, 200, balance("0.00"))
    with pytest.raises(summarize_module.BalanceError, match="cannot call the API, balance 0.00"):
        summarize_module.check_balance(make_settings())


def test_check_balance_fails_on_a_wrong_key(monkeypatch):
    error = {"error": {"message": "Authentication Fails", "type": "authentication_error"}}
    balance_answer(monkeypatch, 401, error)
    with pytest.raises(summarize_module.BalanceError, match="401 Authentication Fails"):
        summarize_module.check_balance(make_settings())


def test_system_prompt_names_the_tool():
    client = FakeClient(tool_response(VALID, name="report_summary_v2"))
    summarize(content(), make_settings(llm_tool_name="report_summary_v2"), client)
    system = client.calls[0]["system"]
    assert "`report_summary_v2`" in system
    assert "{TOOL_NAME}" not in system
