from helpers import make_settings


def test_app_password_spaces_are_stripped():
    assert make_settings().imap_password == "abcdefghijklmnop"


def test_allowlist_matches_exact_address_only():
    settings = make_settings()
    assert settings.sender_allowed("direccion@kinder.example")
    assert settings.sender_allowed("Secretaria@KINDER.example")
    assert not settings.sender_allowed("someone@kinder.example")
    assert not settings.sender_allowed("someone@else.example")


def test_domain_is_not_a_rule():
    settings = make_settings(allowed_senders="@kinder.example")
    assert not settings.sender_allowed("direccion@kinder.example")


def test_empty_allowlist_allows_nobody():
    assert not make_settings(allowed_senders="").sender_allowed("direccion@kinder.example")
