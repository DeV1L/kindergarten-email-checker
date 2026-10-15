"""Turn one email into model inputs (docs/ARCHITECTURE.md, section 7)."""

from __future__ import annotations

import io
import logging
import mimetypes
import re
from dataclasses import dataclass, field
from datetime import datetime
from zoneinfo import ZoneInfo

import html2text
import pypdfium2 as pdfium
from imap_tools import MailMessage

from kindergarten_email_checker.config import Settings

log = logging.getLogger(__name__)

IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
MIN_IMAGE_BYTES = 20 * 1024  # smaller images are logos and signature graphics
MAX_PDF_PAGES_RENDERED = 10
PDF_TEXT_MIN_CHARS_PER_PAGE = 200
PDF_RENDER_SCALE = 110 / 72  # about 110 dpi
MAX_BODY_CHARS = 40_000
MAX_PDF_TEXT_CHARS = 20_000


@dataclass
class EmailContent:
    uid: str
    sender: str
    subject: str
    sent_at: datetime
    text: str
    pdf_texts: list[tuple[str, str]] = field(default_factory=list)  # (file name, text)
    images: list[tuple[str, bytes]] = field(default_factory=list)  # (media type, bytes)
    attachment_names: list[str] = field(default_factory=list)  # listed in the Telegram post
    not_sent_to_model: list[str] = field(default_factory=list)  # file names listed in the prompt


def extract(message: MailMessage, settings: Settings) -> EmailContent:
    """Body to text, PDFs to text or page images, photos as images. Collect attachment names."""
    tz = ZoneInfo(settings.tz)
    sent_at = message.date
    if sent_at.year < 2000:  # imap-tools returns 1900-01-01 when the Date header is missing
        sent_at = datetime.now(tz)
    content = EmailContent(
        uid=message.uid,
        sender=message.from_,
        subject=message.subject or "(без темы)",
        sent_at=sent_at.astimezone(tz),
        text=body_text(message),
    )
    max_bytes = settings.max_attachment_mb * 1024 * 1024
    for att in message.attachments:
        name = att.filename or "без имени"
        data = att.payload
        media_type = guess_media_type(att.content_type, name)
        if media_type in IMAGE_TYPES and len(data) < MIN_IMAGE_BYTES:
            continue  # logo or signature graphic: not listed, not sent
        content.attachment_names.append(name)
        if len(data) > max_bytes:
            content.not_sent_to_model.append(name)
        elif media_type in IMAGE_TYPES:
            content.images.append((media_type, data))
        elif media_type == "application/pdf":
            text, pages = pdf_to_text_or_images(data)
            if text:
                content.pdf_texts.append((name, text[:MAX_PDF_TEXT_CHARS]))
            elif pages:
                content.images.extend(("image/png", page) for page in pages)
            else:
                content.not_sent_to_model.append(name)
        else:
            content.not_sent_to_model.append(name)
    return content


def body_text(message: MailMessage) -> str:
    """Plain text part when present, otherwise the HTML part converted to text."""
    text = message.text.strip() or html_to_text(message.html)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if len(text) > MAX_BODY_CHARS:
        text = text[:MAX_BODY_CHARS] + "\n[текст обрезан]"
    return text


def html_to_text(html: str) -> str:
    converter = html2text.HTML2Text()
    converter.ignore_images = True
    converter.ignore_links = True
    converter.body_width = 0  # no line wrapping
    return converter.handle(html).strip()


def guess_media_type(content_type: str, filename: str) -> str:
    """Content type from the email, or from the file name when the email says octet-stream."""
    content_type = (content_type or "").lower()
    if content_type in ("", "application/octet-stream"):
        content_type = (mimetypes.guess_type(filename)[0] or "").lower()
    return content_type


def pdf_to_text_or_images(data: bytes) -> tuple[str | None, list[bytes]]:
    """Extracted text when the PDF has a text layer, otherwise rendered PNG pages.

    Returns (None, []) when the PDF cannot be read.
    """
    try:
        pdf = pdfium.PdfDocument(data)
    except Exception as error:
        log.warning("cannot open PDF: %s", error)
        return None, []
    try:
        texts = [page.get_textpage().get_text_range() for page in pdf]
        if texts and sum(len(t.strip()) for t in texts) / len(texts) > PDF_TEXT_MIN_CHARS_PER_PAGE:
            return "\n\n".join(t.strip() for t in texts), []
        pages = []
        for index in range(min(len(pdf), MAX_PDF_PAGES_RENDERED)):
            image = pdf[index].render(scale=PDF_RENDER_SCALE).to_pil()
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            pages.append(buffer.getvalue())
        return None, pages
    except Exception as error:
        log.warning("cannot read PDF: %s", error)
        return None, []
    finally:
        pdf.close()
