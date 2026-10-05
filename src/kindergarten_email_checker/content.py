"""Turn one email into model inputs (docs/ARCHITECTURE.md, section 7)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from imap_tools import MailMessage

from kindergarten_email_checker.config import Settings

IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
MIN_IMAGE_BYTES = 20 * 1024  # smaller images are logos and signature graphics
MAX_PDF_PAGES_RENDERED = 10


@dataclass
class EmailContent:
    sender: str
    subject: str
    sent_at: datetime
    text: str
    pdf_texts: list[str] = field(default_factory=list)
    images: list[tuple[str, bytes]] = field(default_factory=list)  # (media type, bytes)
    attachment_names: list[str] = field(default_factory=list)  # listed in the Telegram post
    not_sent_to_model: list[str] = field(default_factory=list)  # file names listed in the prompt


def extract(message: MailMessage, settings: Settings) -> EmailContent:
    """Body to text, PDFs to text or page images, photos as images. Collect attachment names."""
    raise NotImplementedError


def html_to_text(html: str) -> str:
    raise NotImplementedError


def pdf_to_text_or_images(data: bytes) -> tuple[str | None, list[bytes]]:
    """Extracted text when the PDF has a text layer, otherwise rendered PNG pages."""
    raise NotImplementedError
