"""Shared test data: settings, emails, PDFs."""

import io
from email.message import EmailMessage

import pypdfium2 as pdfium
from imap_tools import MailMessage

from kindergarten_email_checker.config import Settings


def make_settings(**overrides):
    values = dict(
        imap_user="dedicated@gmail.com",
        imap_password="abcd efgh ijkl mnop",
        llm_api_key="key",
        telegram_bot_token="token",
        telegram_chat_id="-1001",
        allowed_senders="Direccion@Kinder.example, @kinder.example",
    )
    values.update(overrides)
    return Settings(_env_file=None, **values)


def make_message(
    sender="direccion@kinder.example",
    subject="Excursión",
    text="Hola familias",
    html=None,
    attachments=(),
    uid="7",
):
    """A real MailMessage parsed from bytes. attachments: (filename, maintype/subtype, bytes)."""
    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = "dedicated@gmail.com"
    msg["Subject"] = subject
    msg["Date"] = "Mon, 05 Oct 2026 10:00:00 -0300"
    if text is not None:
        msg.set_content(text)
    if html is not None:
        if text is None:
            msg.set_content(html, subtype="html")
        else:
            msg.add_alternative(html, subtype="html")
    for filename, mime, data in attachments:
        maintype, subtype = mime.split("/")
        msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=filename)
    message = MailMessage.from_bytes(msg.as_bytes())
    message.__dict__["uid"] = uid  # uid is a cached_property; set it as a fetch would
    return message


def text_pdf(text: str) -> bytes:
    """A one-page PDF with a text layer, written by hand. pdfium rebuilds the missing xref."""
    stream = f"BT /F1 9 Tf 20 760 Td 11 TL ({text}) Tj ET".encode()
    return (
        b"%PDF-1.4\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Contents 4 0 R"
        b"/Resources<</Font<</F1 5 0 R>>>>>>endobj\n"
        b"4 0 obj<</Length "
        + str(len(stream)).encode()
        + b">>stream\n"
        + stream
        + b"\nendstream endobj\n"
        b"5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
        b"trailer<</Root 1 0 R>>\n%%EOF\n"
    )


def blank_pdf(pages: int = 1) -> bytes:
    """A PDF without a text layer, like a scan."""
    pdf = pdfium.PdfDocument.new()
    for _ in range(pages):
        pdf.new_page(595, 842)
    buffer = io.BytesIO()
    pdf.save(buffer)
    return buffer.getvalue()
