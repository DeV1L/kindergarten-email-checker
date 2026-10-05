"""IMAP access to the dedicated mailbox (docs/ARCHITECTURE.md, sections 4 and 6).

The mailbox is the only state: unseen mail in the inbox label is the queue, and moving a
message to Processed, Ignored or Failed is the commit. Fetching must not set the Seen flag.
"""

from __future__ import annotations

from collections.abc import Iterable

from imap_tools import MailBox, MailMessage

from kindergarten_email_checker.config import Settings


def connect(settings: Settings) -> MailBox:
    """Open an IMAP session on the inbox label and create the state labels if missing."""
    raise NotImplementedError


def wait_for_mail(mailbox: MailBox, timeout_seconds: int) -> None:
    """Block on IMAP IDLE until new mail arrives or the timeout passes."""
    raise NotImplementedError


def fetch_unseen(mailbox: MailBox) -> list[MailMessage]:
    """Return unseen messages without setting the Seen flag."""
    raise NotImplementedError


def move(mailbox: MailBox, uids: Iterable[str], folder: str) -> None:
    """Move messages to a label. This is the commit step for every outcome."""
    raise NotImplementedError
