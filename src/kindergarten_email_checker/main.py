"""Process entry point and the main loop.

At start: check Telegram, Gmail and DeepSeek. Stop when one of them fails.
Then every POLL_MINUTES: connect, process every unseen email, log out.
An IMAP error ends the poll. The next poll tries again.
"""

from __future__ import annotations

import imaplib
import logging
import sys
import time

from imap_tools import MailBox, MailMessage

from kindergarten_email_checker import __version__, health, mail, telegram
from kindergarten_email_checker.config import Settings
from kindergarten_email_checker.content import extract
from kindergarten_email_checker.summarize import check_balance, summarize

log = logging.getLogger("kindergarten_email_checker")

# A failed or dropped connection: the network is down, Gmail closed the session.
# The next poll tries again, so these get one warning line. Any other error gets a traceback.
CONNECTION_ERRORS = (imaplib.IMAP4.abort, OSError)


def run() -> int:
    """Console entry point."""
    settings = Settings()  # fails with a readable message when a required variable is missing
    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stdout,
    )
    log.info(
        "kindergarten-email-checker %s starting: mailbox=%s model=%s poll=%s min",
        __version__,
        settings.imap_user,
        settings.llm_model,
        settings.poll_minutes,
    )
    health.start(settings.health_port)
    check_services(settings)
    loop(settings)
    return 0


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
    health.ready = True
    log.info("start check passed: Telegram, Gmail and DeepSeek, DeepSeek balance %s", balance)


def loop(settings: Settings) -> None:
    """Run forever: one poll, then a pause of POLL_MINUTES."""
    attempts: dict[str, int] = {}  # uid -> failed attempts, reset on restart
    while True:
        poll(settings, attempts)
        time.sleep(settings.poll_minutes * 60)


def poll(settings: Settings, attempts: dict[str, int]) -> None:
    """Connect, process every unseen email and log out. An IMAP error ends the poll early."""
    mailbox = None
    try:
        mailbox = mail.connect(settings)
        log.debug("connected to %s", settings.imap_host)
        for message in mail.fetch_unseen(mailbox):
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
