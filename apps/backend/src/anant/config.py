"""Application configuration.

All environment-driven settings live here.
Reading os.environ anywhere else is a code-review failure.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["dev", "staging", "prod"]
LogLevel = Literal["DEBUG", "INFO", "WARN", "ERROR"]


class Settings(BaseSettings):
    """Strongly-typed application settings.

    Missing required vars cause startup failure — never a silent default.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- environment ---
    environment: Environment = "dev"
    log_level: LogLevel = "INFO"
    service_name: str = "anant-backend"

    # --- HTTP server ---
    api_prefix: str = "/v1"
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:8081", "http://localhost:19006"]
    )

    # --- build metadata ---
    build_version: str = "0.1.0"
    build_commit: str = "dev"

    # --- Phase 2: database ---
    # PostgreSQL with the asyncpg driver. Default points at the docker-compose service.
    database_url: str = "postgresql+asyncpg://anant:anant@localhost:5432/anant"
    database_pool_size: int = 10
    database_max_overflow: int = 5

    # --- Phase 2: JWT ---
    # WARNING: jwt_secret MUST be overridden in any non-dev environment.
    jwt_secret: str = "dev-only-not-for-prod-please-rotate"
    jwt_algorithm: Literal["HS256"] = "HS256"
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 30

    # --- Phase 2: rate limiting ---
    rate_limit_signin_per_10min: int = 5
    rate_limit_signup_per_10min: int = 5
    lockout_threshold: int = 10
    lockout_minutes: int = 15

    # --- Phase 2: password policy ---
    password_min_length: int = 10

    # --- Phase 3: intake credentials encryption ---
    # WARNING: required (32+ bytes) wherever intake credentials are stored;
    # core/security/secrets.py refuses to run without it.
    intake_kms_key: str | None = None

    # --- Phase 3: Gmail OAuth ---
    gmail_client_id: str | None = None
    gmail_client_secret: str | None = None
    gmail_redirect_uri: str = "http://localhost:8000/v1/intake/oauth/gmail/callback"

    # --- Phase 3: scheduler + drainer processes (CR-7) ---
    scheduler_tick_seconds: float = 15.0
    scheduler_per_kind_concurrency: int = 4
    drainer_batch_size: int = 100
    # §14.3 — dev-only colocation of scheduler + drainer inside the API
    # process. Ignored outside environment=dev; production always runs
    # three separate processes.
    anant_dev_monoprocess: bool = False

    # CR-8 — manual ingest is platform-admin only and deliberately slow.
    manual_ingest_per_minute: int = 10

    # --- Phase 4: AI pipeline ---
    # Required for claim extraction/typing; without it AI calls raise
    # ProviderError(AUTH) and deliveries dead-letter after the retry budget.
    anthropic_api_key: str | None = None

    # AI provider selection — "anthropic" (default) or "ollama" (free local).
    # Switch by setting AI_PROVIDER=ollama in the environment or .env file.
    # See core/ai_provider.py for quality trade-offs.
    ai_provider: str = "anthropic"
    ollama_model: str = "qwen2.5:7b-instruct"
    ollama_base_url: str = "http://localhost:11434"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings accessor — call this everywhere instead of constructing Settings."""
    return Settings()
