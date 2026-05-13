"""
Centralized application settings loaded from environment variables and `.env` files.

Design decisions:
- Pydantic's `BaseSettings` is used for automatic env-var mapping, validation, and
  type coercion.
- `SettingsConfigDict(extra="ignore")` prevents startup failures when the environment
  contains unrelated variables (e.g., in container orchestration).
- The singleton pattern via `functools.lru_cache` on `get_settings()` guarantees that
  validations only run once and that all parts of the application share the same
  configuration instance.
- Cross-field validation (e.g., requiring a token when a platform is selected) lives
  in a `model_validator` to keep the logic close to the data it governs.
"""

from functools import lru_cache

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.enums import Platform, RunMode


class Settings(BaseSettings):
    """Application-wide configuration loaded from the environment and `.env`."""

    # Tell Pydantic to read a `.env` file, use UTF-8 encoding, and silently skip
    # any extra keys that are not declared as fields.
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Platform & connection settings ---
    bot_platform: Platform = Platform.BALE
    """Target platform for the bot (Bale or Telegram). Defaults to Bale."""

    telegram_api_base_url: str = ""
    """Custom base URL for the Telegram Bot API, useful for proxies or local servers."""

    bale_api_base_url: str = ""
    """Custom base URL for the Bale Bot API (similar purpose)."""

    telegram_bot_token: str = ""
    """Bot token issued by @BotFather when using Telegram."""

    bale_bot_token: str = ""
    """Bot token issued by Bale when using Bale."""

    # --- Run mode ---
    run_mode: RunMode = RunMode.POLLING
    """Execution mode: polling (long-poll) or webhook."""

    webhook_url: str = ""
    """Public URL for the webhook. Required when run_mode is WEBHOOK."""

    webhook_host: str = "0.0.0.0"
    """Host interface the webhook server binds to."""

    webhook_port: int = 8080
    """Port the webhook server listens on."""

    # --- Database ---
    database_url: str = "sqlite:///./cafebot.db"
    """Database connection string. Defaults to a local SQLite file."""

    # --- Admin identification ---
    admin_telegram_ids: list[int] = Field(default_factory=list)
    """Telegram user IDs of administrators. Can be a comma-separated string in env."""

    admin_bale_ids: list[int] = Field(default_factory=list)
    """Bale user IDs of administrators. Can be a comma-separated string in env."""

    # --- Business rules ---
    default_currency: str = "IRR"
    """Default currency for monetary operations. Only IRR is supported in the MVP."""

    # --- Logging ---
    log_level: str = "INFO"
    """Log level for the application (DEBUG, INFO, WARNING, ERROR, CRITICAL)."""

    # --- Feature flags ---
    github_search_enabled: bool = True
    """Toggle for GitHub code search functionality."""

    youtube_search_enabled: bool = True
    """Toggle for YouTube search functionality."""

    youtube_cookies_file: str = ""
    """Path to a cookies file for YouTube requests (required for some regions)."""

    # ------------------------------------------------------------------
    # Validators
    # ------------------------------------------------------------------

    @field_validator("admin_telegram_ids", mode="before")
    @classmethod
    def parse_telegram_admin_ids(cls, value: object) -> list[int]:
        """
        Normalise the admin Telegram IDs to a list of ints.

        Accepts:
        - ``None`` or an empty string → empty list
        - a list of strings/ints → converted to ints
        - a comma-separated string (e.g., ``"123,456"``) → parsed to [123, 456]

        Any other type raises a ``TypeError`` with a clear message.
        """
        if value in (None, ""):
            return []
        if isinstance(value, list):
            return [int(item) for item in value]
        if isinstance(value, str):
            return [int(item.strip()) for item in value.split(",") if item.strip()]
        raise TypeError("ADMIN_TELEGRAM_IDS must be a comma-separated string or list")

    @field_validator("admin_bale_ids", mode="before")
    @classmethod
    def parse_bale_admin_ids(cls, value: object) -> list[int]:
        """
        Normalise the admin Bale IDs to a list of ints.

        See ``parse_telegram_admin_ids`` for supported formats.
        """
        if value in (None, ""):
            return []
        if isinstance(value, list):
            return [int(item) for item in value]
        if isinstance(value, str):
            return [int(item.strip()) for item in value.split(",") if item.strip()]
        raise TypeError("ADMIN_BALE_IDS must be a comma-separated string or list")

    @field_validator("default_currency")
    @classmethod
    def validate_currency(cls, value: str) -> str:
        """
        Ensure the currency is uppercase and validate against supported options.

        Currently only ``IRR`` is allowed (MVP restriction). Any other value
        raises a ``ValueError``.
        """
        normalized = value.upper()
        if normalized != "IRR":
            raise ValueError("Only IRR is supported in the MVP")
        return normalized

    @model_validator(mode="after")
    def validate_runtime(self) -> "Settings":
        """
        Cross-field validation run after individual field validators.

        Checks:
        - A token is supplied for the active platform.
        - A webhook URL is supplied when the run mode is ``WEBHOOK``.

        Raises ``ValueError`` on any constraint violation.
        """
        if self.bot_platform == Platform.TELEGRAM and not self.telegram_bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN is required for Telegram")
        if self.bot_platform == Platform.BALE and not self.bale_bot_token:
            raise ValueError("BALE_BOT_TOKEN is required for Bale")
        if self.run_mode == RunMode.WEBHOOK and not self.webhook_url:
            raise ValueError("WEBHOOK_URL is required when RUN_MODE=webhook")
        return self


@lru_cache
def get_settings() -> Settings:
    """
    Retrieve the application settings as a cached singleton.

    The ``lru_cache`` decorator ensures that the ``Settings`` object is
    instantiated only once per process lifetime. This avoids re-reading
    environment variables and re-running validators on every call.
    """
    return Settings()