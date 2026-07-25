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
# Every valid AI_PROVIDER value. A Literal (not plain str) so a typo'd or
# unknown value fails at startup with a pydantic validation error instead of
# silently falling through to the factory's Anthropic default branch.
AIProviderName = Literal["anthropic", "ollama", "openai_compatible"]


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
    service_name: str = "oryx-backend"

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

    # --- Phase 5 Wave D: publish-target credential encryption ---
    # AES-256-GCM master key for publish_targets.credentials (§10.3). Stored
    # base64-encoded so a raw 32-byte key survives .env transport (same shape
    # the secret would take in a real secrets manager). core/credential_crypto.py
    # refuses to run without a 32-byte key after decoding.
    # WARNING: the local .env value is an OBVIOUS dev-only placeholder — it MUST
    # be replaced with a securely-generated 32-byte secret before staging/prod.
    oryx_publish_key: str | None = None

    # Local output directory for the Export channel (§10.2). No external API —
    # publish() writes a Markdown file here and returns its path as external_url.
    publish_export_dir: str = "outputs/publish"

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
    oryx_dev_monoprocess: bool = False

    # CR-8 — manual ingest is platform-admin only and deliberately slow.
    manual_ingest_per_minute: int = 10

    # --- Phase 4: AI pipeline ---
    # Required for claim extraction/typing; without it AI calls raise
    # ProviderError(AUTH) and deliveries dead-letter after the retry budget.
    anthropic_api_key: str | None = None

    # AI provider selection — "anthropic" (default), "ollama" (free local),
    # or "openai_compatible" (any /chat/completions vendor: NVIDIA NIM, vLLM,
    # LM Studio, ...). Switch by setting AI_PROVIDER in the environment or
    # .env file. Typed as AIProviderName so an unrecognized value is a
    # STARTUP failure, never a silent fall-through to Anthropic.
    # See core/ai_provider.py for quality trade-offs.
    ai_provider: AIProviderName = "anthropic"
    ollama_model: str = "qwen2.5:7b-instruct"
    ollama_base_url: str = "http://localhost:11434"
    # Generic OpenAI-compatible provider settings (used when
    # AI_PROVIDER=openai_compatible). BASE_URL is the vendor's API root, e.g.
    # https://integrate.api.nvidia.com/v1 for NVIDIA NIM. BASE_URL and MODEL
    # have no universal default across vendors, so both are required when
    # this provider is selected — complete() raises ProviderError(PERMANENT)
    # if either is unset. API_KEY stays optional at runtime: local servers
    # (vLLM, LM Studio) accept unauthenticated requests, and auth-requiring
    # vendors answer 401 which maps to ProviderError(AUTH) like any other
    # rejected credential.
    openai_compat_base_url: str | None = None
    openai_compat_model: str | None = None
    openai_compat_api_key: str | None = None
    # Reasoning-capable OpenAI-compatible models (NVIDIA Nemotron, Qwen, ...)
    # spend ~1000 output tokens "thinking" before any content; the pipeline's
    # 50-800-token budgets then truncate mid-reasoning and a 200 response
    # arrives with EMPTY message.content — every caller parse-fails while the
    # circuit breaker counts a success. When true, OpenAICompatProvider
    # prepends the "/no_think" control token to the system message on the
    # wire; caller prompts and the Anthropic/Ollama paths are untouched.
    openai_compat_disable_reasoning: bool = False

    # --- Phase 6 Wave C: push delivery ---
    # Push provider selection, same shape as AI_PROVIDER above: "log_only"
    # (default — the Phase 2 stub logs instead of delivering) or "real"
    # (FCMProvider for Android devices, APNsProvider for iOS). Switch by
    # setting PUSH_PROVIDER=real in the environment or .env file.
    #
    # Real delivery needs credentials (documented requirement, not a default):
    #   FCM  — a Firebase service-account key JSON (Firebase console →
    #          Project settings → Service accounts → Generate new private
    #          key); point FCM_SERVICE_ACCOUNT_FILE at the file. Project id,
    #          client email and signing key are read from it.
    #   APNs — an Apple Push auth key (developer.apple.com → Keys → enable
    #          APNs): APNS_KEY_FILE (the .p8), APNS_KEY_ID, APNS_TEAM_ID.
    #          APNS_TOPIC is the app bundle id; APNS_USE_SANDBOX picks the
    #          sandbox host (development builds) vs production.
    push_provider: str = "log_only"
    fcm_service_account_file: str | None = None
    apns_key_file: str | None = None
    apns_key_id: str | None = None
    apns_team_id: str | None = None
    apns_topic: str = "com.oryx.app"
    apns_use_sandbox: bool = True

    # --- Alert email delivery (Phase 6 carry-over) ---
    # Email provider selection, same shape as AI_PROVIDER/PUSH_PROVIDER above:
    # "log_only" (default — the Phase 2 stub logs instead of delivering),
    # "sendgrid", or "smtp". Switch by setting EMAIL_PROVIDER in the
    # environment or .env file.
    #
    # Credentials are PLATFORM-level (alert email is ORYX mailing its own
    # user), deliberately separate from the per-workspace encrypted
    # publish-target credentials the newsletter channel uses:
    #   sendgrid — SENDGRID_API_KEY.
    #   smtp     — SMTP_HOST (+ optional SMTP_PORT/SMTP_USERNAME/SMTP_PASSWORD).
    # ALERT_EMAIL_FROM/_NAME give alerts their own sender identity so alert
    # mail is visually distinct from published-newsletter mail.
    email_provider: str = "log_only"
    sendgrid_api_key: str | None = None
    alert_email_from: str = "alerts@oryx.local"
    alert_email_from_name: str = "ORYX Alerts"
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None

    # --- Billing foundation wave: PaymentProvider (core/payment_provider.py) ---
    # Same shape as AI_PROVIDER/PUSH_PROVIDER/EMAIL_PROVIDER above: no live
    # credential is configured by default, so create_subscription/
    # cancel_subscription raise PaymentProviderError(PERMANENT) pre-flight
    # until real keys are wired (deliberately out of scope for this wave).
    # Currency routes the vendor (INR -> Razorpay, else Stripe); see
    # get_payment_provider()'s docstring for why.
    stripe_api_key: str | None = None
    stripe_webhook_secret: str | None = None
    razorpay_key_id: str | None = None
    razorpay_key_secret: str | None = None
    razorpay_webhook_secret: str | None = None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings accessor — call this everywhere instead of constructing Settings."""
    return Settings()
