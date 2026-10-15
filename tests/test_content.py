from helpers import blank_pdf, make_message, make_settings, text_pdf

from kindergarten_email_checker.content import (
    MIN_IMAGE_BYTES,
    extract,
    guess_media_type,
    html_to_text,
)

LONG_TEXT = "Autorizacion para la excursion al parque del viernes. " * 6
PHOTO = b"\xff\xd8\xff" + b"0" * (MIN_IMAGE_BYTES + 10)


def test_html_to_text_drops_tags_and_links():
    text = html_to_text('<p>Hola <b>familias</b></p><p><a href="https://x.example">ver</a></p>')
    assert "Hola **familias**" in text
    assert "https://x.example" not in text


def test_guess_media_type_from_file_name_when_octet_stream():
    assert guess_media_type("application/octet-stream", "foto.JPG") == "image/jpeg"
    assert guess_media_type("image/png", "x.bin") == "image/png"


def test_extract_metadata_and_html_only_body():
    message = make_message(text=None, html="<p>Reunión el <b>lunes</b></p>")
    content = extract(message, make_settings())
    assert content.uid == "7"
    assert content.sender == "direccion@kinder.example"
    assert "Reunión el **lunes**" in content.text
    assert content.sent_at.utcoffset().total_seconds() == -3 * 3600  # Buenos Aires


def test_extract_sorts_attachments():
    message = make_message(
        attachments=[
            ("autorizacion.pdf", "application/pdf", text_pdf(LONG_TEXT)),
            ("escaneo.pdf", "application/pdf", blank_pdf(2)),
            ("foto.jpg", "image/jpeg", PHOTO),
            ("logo.png", "image/png", b"\x89PNG" + b"0" * 100),
            ("menu.docx", "application/vnd.openxmlformats", b"PK"),
        ]
    )
    content = extract(message, make_settings())
    assert content.attachment_names == ["autorizacion.pdf", "escaneo.pdf", "foto.jpg", "menu.docx"]
    assert [name for name, _ in content.pdf_texts] == ["autorizacion.pdf"]
    assert "excursion al parque" in content.pdf_texts[0][1]
    media = [media_type for media_type, _ in content.images]
    assert media == ["image/png", "image/png", "image/jpeg"]  # two scanned pages, one photo
    assert content.not_sent_to_model == ["menu.docx"]


def test_extract_large_attachment_is_named_but_not_sent():
    message = make_message(attachments=[("foto.jpg", "image/jpeg", PHOTO)])
    content = extract(message, make_settings(max_attachment_mb=0))
    assert content.images == []
    assert content.not_sent_to_model == ["foto.jpg"]
    assert content.attachment_names == ["foto.jpg"]


def test_extract_broken_pdf_is_named_but_not_sent():
    message = make_message(attachments=[("roto.pdf", "application/pdf", b"not a pdf")])
    content = extract(message, make_settings())
    assert content.not_sent_to_model == ["roto.pdf"]
