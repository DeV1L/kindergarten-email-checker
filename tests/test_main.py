import imaplib
import logging

import pytest
from helpers import make_message, make_settings

from kindergarten_email_checker import main


@pytest.fixture
def calls(monkeypatch):
    """Replace IMAP moves, the model and Telegram with recorders."""
    log = {"moves": [], "posts": []}
    monkeypatch.setattr(main.mail, "move", lambda mb, uids, folder: log["moves"].append(folder))
    monkeypatch.setattr(main, "summarize", lambda content, settings: "SUMMARY")
    monkeypatch.setattr(
        main.telegram,
        "send_summary",
        lambda summary, content, settings: log["posts"].append("summary") or 1,
    )
    monkeypatch.setattr(
        main.telegram,
        "send_original",
        lambda content, settings: log["posts"].append("original") or 2,
    )
    monkeypatch.setattr(
        main.telegram, "send_error", lambda subject, error, settings: log["posts"].append("error")
    )
    return log


class FakeSummary:
    urgency = "high"
    deadline = None


def test_allowed_sender_is_posted_and_processed(calls, monkeypatch):
    monkeypatch.setattr(main, "summarize", lambda content, settings: FakeSummary())
    main.process(None, make_message(), make_settings(), {})
    assert calls == {"moves": ["Processed"], "posts": ["summary"]}


def test_unknown_sender_is_ignored_without_post(calls):
    main.process(None, make_message(sender="spam@else.example"), make_settings(), {})
    assert calls == {"moves": ["Ignored"], "posts": []}


def test_no_summary_sends_original(calls, monkeypatch):
    monkeypatch.setattr(main, "summarize", lambda content, settings: None)
    main.process(None, make_message(), make_settings(), {})
    assert calls == {"moves": ["Processed"], "posts": ["original"]}


def test_failures_retry_then_move_to_failed(calls, monkeypatch):
    def broken(content, settings):
        raise TimeoutError("model timeout")

    monkeypatch.setattr(main, "summarize", broken)
    settings, attempts = make_settings(max_retries_per_message=3), {}
    for _ in range(2):
        main.process(None, make_message(), settings, attempts)
    assert calls == {"moves": [], "posts": []}  # still unseen, retried next cycle
    main.process(None, make_message(), settings, attempts)
    assert calls == {"moves": ["Failed"], "posts": ["error"]}
    assert attempts == {}


class DroppingMailbox:
    """A mailbox whose connection is already dead: every command fails."""

    def __init__(self, error):
        self.error = error
        self.logout_called = False

    def logout(self):
        self.logout_called = True
        raise imaplib.IMAP4.abort("socket error: EOF occurred in violation of protocol")


def run_session(monkeypatch, caplog, error):
    mailbox = DroppingMailbox(error)
    monkeypatch.setattr(main.mail, "connect", lambda settings: mailbox)

    def fetch(mb):
        raise error

    monkeypatch.setattr(main.mail, "fetch_unseen", fetch)
    with caplog.at_level(logging.INFO, logger="kindergarten_email_checker"):
        main.session(make_settings(), {})  # returns instead of raising
    return mailbox


def test_dropped_connection_logs_one_warning_line(monkeypatch, caplog):
    mailbox = run_session(monkeypatch, caplog, imaplib.IMAP4.abort("socket error: EOF"))
    assert mailbox.logout_called
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1
    assert "IMAP connection failed or lost (abort: socket error: EOF)" in warnings[0].getMessage()
    assert all(r.exc_info is None for r in caplog.records)  # no traceback


def test_other_imap_error_keeps_the_traceback(monkeypatch, caplog):
    run_session(monkeypatch, caplog, ValueError("unexpected"))
    errors = [r for r in caplog.records if r.levelno == logging.ERROR]
    assert len(errors) == 1 and errors[0].exc_info is not None
