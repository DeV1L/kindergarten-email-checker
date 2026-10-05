"""Runtime configuration, read from environment variables. See .env.example for the full list."""

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

    # Model, Anthropic Messages API format served by DeepSeek
    llm_base_url: str = "https://api.deepseek.com/anthropic"
    llm_api_key: str
    llm_model: str = "deepseek-flash"
    llm_effort: str = "high"
    llm_timeout_seconds: float = 120

    # Telegram
    telegram_bot_token: str
    telegram_chat_id: str

    # Loop
    sweep_minutes: int = 10
    max_attachment_mb: int = 10
    max_retries_per_message: int = 3
    log_level: str = "INFO"

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
