import json
import logging
from datetime import date
from types import SimpleNamespace

from helpers import make_message, make_settings

from kindergarten_email_checker.content import extract
from kindergarten_email_checker.summarize import TOOL_NAME, Summary, summarize, tool_definition

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


def tool_response(tool_input):
    return SimpleNamespace(
        stop_reason="tool_use",
        content=[
            SimpleNamespace(type="thinking", thinking=""),
            SimpleNamespace(type="tool_use", name=TOOL_NAME, id="toolu_1", input=tool_input),
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


def test_two_bad_answers_return_none():
    client = FakeClient(text_response(), text_response())
    assert summarize(content(), make_settings(), client) is None
    assert len(client.calls) == 2


def test_text_null_means_no_value():
    summary = Summary.model_validate(
        {**VALID, "action_ru": "null", "deadline": "None", "event_date": " ", "event_time": ""}
    )
    fields = [summary.action_ru, summary.deadline, summary.event_date, summary.event_time]
    assert fields == [None, None, None, None]


def test_text_null_needs_no_retry():
    client = FakeClient(tool_response({**VALID, "deadline": "null", "event_date": "null"}))
    summary = summarize(content(), make_settings(), client)
    assert summary.deadline is None and summary.event_date is None
    assert len(client.calls) == 1


def test_tool_schema_matches_summary_model():
    schema = tool_definition()["input_schema"]
    assert set(schema["required"]) == {"title_ru", "summary_ru", "urgency", "category"}
    assert Summary.model_validate(VALID).event_time == "10:00"
