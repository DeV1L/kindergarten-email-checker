"""Runtime configuration, read from environment variables. See .env.example for the full list.

Every setting except the credentials has its default value here.
"""

from __future__ import annotations

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Dedicated mailbox
    imap_host: str = "imap.gmail.com"
    imap_user: str
    imap_password: str
    imap_folder_inbox: str = "INBOX"
    imap_folder_processed: str = "Processed"
    imap_folder_ignored: str = "Ignored"
    imap_folder_failed: str = "Failed"
    allowed_senders: str = ""
    imap_timeout_seconds: float = 60

    # Model, Anthropic Messages API format served by DeepSeek
    llm_base_url: str = "https://api.deepseek.com/anthropic"
    llm_api_key: str
    llm_model: str = "deepseek-flash"
    llm_effort: str = "high"
    llm_timeout_seconds: float = 120
    llm_tool_name: str = "report_summary"
    llm_max_tokens: int = 16_000  # thinking and the tool call together
    llm_model_tries: int = 2  # model calls for one email when the answer is unusable
    llm_balance_timeout_seconds: float = 30

    # Telegram
    telegram_bot_token: str
    telegram_chat_id: str
    telegram_base_url: str = "https://api.telegram.org"
    telegram_max_message_chars: int = 4096
    telegram_max_error_chars: int = 500  # error text in an error post
    telegram_timeout_seconds: float = 30

    # Content extraction
    min_image_bytes: int = 20 * 1024  # smaller images are logos and signature graphics
    max_pdf_pages_rendered: int = 10
    pdf_text_min_chars_per_page: int = 200
    pdf_render_dpi: int = 110
    max_body_chars: int = 40_000
    max_pdf_text_chars: int = 20_000

    # Loop
    poll_minutes: int = 10
    max_attachment_mb: int = 10
    max_retries_per_message: int = 3
    log_level: str = "INFO"
    tz: str = "America/Argentina/Buenos_Aires"

    # Health checks
    health_port: int = 8080

    @field_validator("imap_password")
    @classmethod
    def _strip_spaces(cls, value: str) -> str:
        # Gmail shows app passwords in groups of four separated by spaces.
        return value.replace(" ", "")

    @property
    def allowed_sender_rules(self) -> list[str]:
        return [rule.strip().lower() for rule in self.allowed_senders.split(",") if rule.strip()]

    def sender_allowed(self, address: str) -> bool:
        """True when the address matches a rule exactly or ends with an @domain rule."""
        address = address.strip().lower()
        return any(
            address == rule or (rule.startswith("@") and address.endswith(rule))
            for rule in self.allowed_sender_rules
        )
