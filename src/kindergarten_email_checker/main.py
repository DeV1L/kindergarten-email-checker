"""Process entry point and the main loop.

At start: check Telegram, Gmail and DeepSeek. Stop when one of them fails.
Then every POLL_MINUTES: connect, process every unseen email, log out.
An IMAP error ends the poll. The next poll tries again.
SIGTERM or SIGINT stops the loop after the current email, so a stop cannot fall between the
Telegram post and the move. The process then exits with code 0.

An HTTP server in a daemon thread answers the Kubernetes probes:
GET /readyz answers 200 after the start check, GET /livez answers 200 while the process runs.
"""

from __future__ import annotations

import imaplib
import logging
import re
import signal
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

from imap_tools import MailBox, MailMessage

from kindergarten_email_checker import __version__, mail, telegram
from kindergarten_email_checker.config import Settings
from kindergarten_email_checker.content import extract
from kindergarten_email_checker.summarize import check_balance, summarize

log = logging.getLogger("kindergarten_email_checker")

# A failed or dropped connection: the network is down, Gmail closed the session.
# The next poll tries again, so these get one warning line. Any other error gets a traceback.
CONNECTION_ERRORS = (imaplib.IMAP4.abort, OSError)

BOT_TOKEN = re.compile(r"/bot\d+:[\w-]+/")  # the bot token in a Telegram Bot API URL

ready = False  # /readyz: set by check_services(), read by the HTTP server thread
stop = threading.Event()  # set by request_stop(); the loop ends after the current email


def run() -> int:
    """Console entry point."""
    settings = Settings()  # fails with a readable message when a required variable is missing
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(MaskedFormatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logging.basicConfig(level=settings.log_level.upper(), handlers=[handler])
    log.info(
        "kindergarten-email-checker %s starting: mailbox=%s model=%s poll=%s min",
        __version__,
        settings.imap_user,
        settings.llm_model,
        settings.poll_minutes,
    )
    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)
    start_health(settings)
    check_services(settings)
    loop(settings)
    log.info("stopped")
    return 0


class MaskedFormatter(logging.Formatter):
    """Replace the Telegram bot token in every log line, tracebacks included.

    httpx2 logs the URL of each request at INFO, and Telegram URLs carry the token in the path.
    """

    def format(self, record: logging.LogRecord) -> str:
        return BOT_TOKEN.sub("/bot<token>/", super().format(record))


def request_stop(signum: int, frame: object) -> None:
    """Signal handler: ask the loop to stop. A blocking IMAP or HTTP call finishes first."""
    log.info("%s received, stopping after the current email", signal.Signals(signum).name)
    stop.set()


def check_services(settings: Settings) -> None:
    """Exit when Telegram, Gmail or DeepSeek fails: wrong credentials, no connection, no balance.

    The app must not poll then: every email would fail and end in Failed.
    Docker or Kubernetes restarts the container, with a growing delay. Until the check passes,
    /readyz answers 503.
    """
    try:
        telegram.check(settings)
        mail.close(mail.connect(settings))
        balance = check_balance(settings)
    except Exception as error:
        log.error("start check failed (%s: %s), exiting", type(error).__name__, error)
        raise SystemExit(1) from None
    global ready
    ready = True
    log.info("start check passed: Telegram, Gmail and DeepSeek, DeepSeek balance %s", balance)


def loop(settings: Settings) -> None:
    """Run until a stop is requested: one poll, then a pause of POLL_MINUTES."""
    attempts: dict[str, int] = {}  # uid -> failed attempts, reset on restart
    while not stop.is_set():
        poll(settings, attempts)
        stop.wait(settings.poll_minutes * 60)  # returns at once when a stop is requested


def poll(settings: Settings, attempts: dict[str, int]) -> None:
    """Connect, process every unseen email and log out. An IMAP error ends the poll early."""
    mailbox = None
    try:
        mailbox = mail.connect(settings)
        log.debug("connected to %s", settings.imap_host)
        for message in mail.fetch_unseen(mailbox):
            if stop.is_set():
                break  # the remaining emails wait for the next start
            process(mailbox, message, settings, attempts)
    except CONNECTION_ERRORS as error:
        log.warning(
            "IMAP connection failed or lost (%s: %s), next poll in %d min",
            type(error).__name__,
            error,
            settings.poll_minutes,
        )
    except Exception:
        log.exception("IMAP error, next poll in %d min", settings.poll_minutes)
    finally:
        if mailbox is not None:
            mail.close(mailbox)


def process(
    mailbox: MailBox, message: MailMessage, settings: Settings, attempts: dict[str, int]
) -> None:
    """Handle one email and move it to its outcome label.

    Errors in extraction, the model call or Telegram leave the email unseen, so the next poll
    tries again. IMAP errors are not caught here; they end the poll.
    """
    uid, sender, subject = message.uid, message.from_, message.subject
    if not settings.sender_allowed(sender):
        mail.move(mailbox, [uid], settings.imap_folder_ignored)
        log.info("uid=%s ignored: sender %s is not on the allowlist", uid, sender)
        return

    started = time.monotonic()
    try:
        content = extract(message, settings)
        summary = summarize(content, settings)
        if summary:
            message_id = telegram.send_summary(summary, content, settings)
        else:
            message_id = telegram.send_original(content, settings)
    except Exception as error:
        attempts[uid] = attempts.get(uid, 0) + 1
        log.exception("uid=%s attempt %d failed", uid, attempts[uid])
        if attempts[uid] < settings.max_retries_per_message:
            return
        try:
            telegram.send_error(subject, f"{type(error).__name__}: {error}", settings)
        except Exception:
            log.exception("uid=%s could not post the error to Telegram", uid)
        mail.move(mailbox, [uid], settings.imap_folder_failed)
        attempts.pop(uid, None)
        log.info("uid=%s moved to %s", uid, settings.imap_folder_failed)
        return

    mail.move(mailbox, [uid], settings.imap_folder_processed)
    attempts.pop(uid, None)
    log.info(
        "uid=%s processed: from=%s subject=%r urgency=%s deadline=%s telegram_id=%s in %.1f s",
        uid,
        sender,
        subject,
        summary.urgency if summary else "no summary",
        summary.deadline if summary else None,
        message_id,
        time.monotonic() - started,
    )


def health_status(path: str) -> int:
    """HTTP status code for a probe path."""
    if path == "/readyz":
        return 200 if ready else 503
    if path == "/livez":
        return 200
    return 404


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        self.send_response(health_status(self.path))
        self.end_headers()

    def log_message(self, format: str, *args: object) -> None:
        pass  # the probes call every few seconds; one line per call would fill the log


def start_health(settings: Settings) -> HTTPServer:
    """Start the HTTP server for the probes in a daemon thread. Port 0 picks a free port."""
    server = HTTPServer(("", settings.health_port), HealthHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server
