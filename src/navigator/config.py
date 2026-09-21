from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: Literal["local", "test", "production"] = "local"
    log_level: str = "INFO"

    postgres_db: str = "benefit_navigator"
    postgres_user: str = "benefit"
    postgres_password: SecretStr = Field(default=SecretStr("change_me"))
    database_url: str = "postgresql+asyncpg://benefit:change_me@localhost:5432/benefit_navigator"

    redis_url: str = "redis://localhost:6379/0"

    max_api_base_url: AnyHttpUrl = AnyHttpUrl("https://platform-api2.max.ru")
    max_bot_token: SecretStr | None = None
    max_transport: Literal["polling", "webhook"] = "polling"
    max_webhook_public_url: AnyHttpUrl | None = None
    max_webhook_secret: SecretStr | None = None
    max_poll_timeout_seconds: int = 30
    max_http_timeout_seconds: int = 10

    fns_provider: Literal["rmsp_portal", "local_snapshot", "mock"] = "rmsp_portal"
    fns_lookup_enabled: bool = True
    fns_timeout_seconds: int = 4
    fns_cache_ttl_seconds: int = 21600
    fns_lookup_limit_10m: int = 5
    fns_lookup_limit_1h: int = 30

    openrouter_enabled: bool = False
    openrouter_api_key: SecretStr | None = None
    openrouter_base_url: AnyHttpUrl = AnyHttpUrl("https://openrouter.ai/api/v1")
    openrouter_model: str | None = None
    openrouter_timeout_seconds: int = 12

    miniapp_enabled: bool = False
    miniapp_compare_url: AnyHttpUrl | None = None

    reminders_enabled: bool = False
    reminder_days: tuple[int, ...] = (7, 3, 1)
    reminder_scan_interval_seconds: int = 600

    debug_endpoints_enabled: bool = False

    @field_validator("reminder_days", mode="before")
    @classmethod
    def parse_reminder_days(cls, value: object) -> tuple[int, ...] | object:
        if isinstance(value, str):
            return tuple(int(part.strip()) for part in value.split(",") if part.strip())
        return value

    @model_validator(mode="after")
    def validate_enabled_features(self) -> Settings:
        if self.max_transport == "webhook":
            if self.max_webhook_public_url is None or self.max_webhook_secret is None:
                raise ValueError(
                    "webhook transport requires MAX_WEBHOOK_PUBLIC_URL and MAX_WEBHOOK_SECRET"
                )
            if self.max_bot_token is None:
                raise ValueError("webhook transport requires MAX_BOT_TOKEN")
        if self.openrouter_enabled and (
            self.openrouter_api_key is None or not self.openrouter_model
        ):
            raise ValueError(
                "OpenRouter requires OPENROUTER_API_KEY and OPENROUTER_MODEL when enabled"
            )
        if self.miniapp_enabled and self.miniapp_compare_url is None:
            raise ValueError("miniapp requires MINIAPP_COMPARE_URL when enabled")
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
