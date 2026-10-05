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


def test_app_password_spaces_are_stripped():
    assert make_settings().imap_password == "abcdefghijklmnop"


def test_allowlist_matches_exact_address_and_domain_suffix():
    settings = make_settings()
    assert settings.sender_allowed("direccion@kinder.example")
    assert settings.sender_allowed("Secretaria@KINDER.example")
    assert not settings.sender_allowed("someone@else.example")
    assert not settings.sender_allowed("kinder.example@evil.example")


def test_empty_allowlist_allows_nobody():
    assert not make_settings(allowed_senders="").sender_allowed("direccion@kinder.example")
