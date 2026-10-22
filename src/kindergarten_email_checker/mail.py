"""IMAP access to the dedicated mailbox (docs/ARCHITECTURE.md, sections 4 and 6).

The mailbox is the only state: unseen mail in the inbox label is the queue, and moving a
message to Processed, Ignored or Failed is the commit. Fetching does not set the Seen flag.
"""

from __future__ import annotations

from collections.abc import Iterable
from contextlib import suppress

from imap_tools import AND, MailBox, MailMessage

from kindergarten_email_checker.config import Settings


def connect(settings: Settings) -> MailBox:
    """Log in, open the inbox label and create the state labels if missing."""
    mailbox = MailBox(settings.imap_host, timeout=settings.imap_timeout_seconds)
    mailbox.login(
        settings.imap_user, settings.imap_password, initial_folder=settings.imap_folder_inbox
    )
    refresh_capabilities(mailbox)
    ensure_labels(
        mailbox,
        [settings.imap_folder_processed, settings.imap_folder_ignored, settings.imap_folder_failed],
    )
    return mailbox


def refresh_capabilities(mailbox: MailBox) -> None:
    """Read the capability list again after login.

    Gmail lists MOVE only after login. imap-tools keeps the list from before login, so without
    this it moves mail by copy and delete, which can send the email to Trash.
    """
    _, data = mailbox.client.capability()
    mailbox.client.capabilities = tuple(data[-1].decode().upper().split())


def ensure_labels(mailbox: MailBox, labels: list[str]) -> None:
    """Create each label that does not exist yet."""
    for label in labels:
        if not mailbox.folder.exists(label):
            mailbox.folder.create(label)


def close(mailbox: MailBox) -> None:
    """Log out. Errors are ignored: after a dropped connection, the logout fails too."""
    with suppress(Exception):
        mailbox.logout()


def fetch_unseen(mailbox: MailBox) -> list[MailMessage]:
    """Return unseen messages in the current folder without setting the Seen flag."""
    return list(mailbox.fetch(AND(seen=False), mark_seen=False, bulk=True))


def move(mailbox: MailBox, uids: Iterable[str], folder: str) -> None:
    """Move messages to a label. This is the commit step for every outcome."""
    mailbox.move(list(uids), folder)
