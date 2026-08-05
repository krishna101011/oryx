"""SQLAlchemy ORM models.

These are the read/write entities services use. They match the schema created
by alembic/versions/0001_phase2_baseline.py.

Convention:
- All columns explicit; no auto-discovery.
- Domain dataclasses live in services/<domain>/models.py (frozen, no SA).
- Repository converts between ORM rows and domain dataclasses.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    LargeBinary,
    Numeric,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, CITEXT, INET, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from oryx.core.db import Base


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(CITEXT(), unique=True, nullable=False)
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    password_changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    status: Mapped[str] = mapped_column(
        Enum("pending", "active", "suspended", "deleted", name="account_status"),
        nullable=False,
        default="active",
    )
    mfa_secret: Mapped[str | None] = mapped_column(Text)
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    failed_login_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_platform_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    kind: Mapped[str] = mapped_column(
        Enum("personal", "team", name="workspace_kind"), nullable=False, default="personal"
    )
    owner_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False
    )
    # Billing foundation wave: widened from ('free','pro','enterprise') to the
    # real 4-tier model. Migration 0029 rebuilds workspace_plan as a fresh
    # Postgres type with exactly these 4 labels (type-swap, not ADD VALUE —
    # see that migration's docstring for why) and converts every existing
    # row, so — unlike activity_type's additive-widen precedent — the
    # retired free/pro/enterprise labels are dropped outright, not kept
    # dormant in the DB type.
    plan: Mapped[str] = mapped_column(
        Enum("glimpse", "focus", "clarity", "vision", name="workspace_plan"),
        nullable=False,
        default="glimpse",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class WorkspaceMember(Base):
    __tablename__ = "workspace_members"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), primary_key=True
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), primary_key=True
    )
    role: Mapped[str] = mapped_column(
        Enum("owner", "admin", "editor", "reader", name="workspace_role"), nullable=False
    )
    invited_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id")
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Profile(Base):
    __tablename__ = "profiles"

    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), primary_key=True
    )
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(Text)
    headline: Mapped[str | None] = mapped_column(Text)
    timezone: Mapped[str] = mapped_column(Text, nullable=False, default="UTC")
    locale: Mapped[str] = mapped_column(Text, nullable=False, default="en-US")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    # Team/Workspace Rev 2: the workspace this session's access tokens are
    # scoped to. Previously NOT stored anywhere — refresh() had no way to
    # know which workspace the prior access token was scoped to and had to
    # re-derive one from scratch via _primary_workspace_id's arbitrary
    # .limit(1), silently reverting an explicit workspace switch on the very
    # next token refresh. refresh() now inherits this column from the old
    # session; switch_workspace() is the only place that changes it.
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    refresh_token_hash: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    parent_session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.id")
    )
    device_id: Mapped[str] = mapped_column(Text, nullable=False)
    device_label: Mapped[str] = mapped_column(Text, nullable=False)
    device_platform: Mapped[str] = mapped_column(
        Enum("ios", "android", "web", name="device_platform"), nullable=False
    )
    ip_address: Mapped[str | None] = mapped_column(INET)
    user_agent: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_used_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_reason: Mapped[str | None] = mapped_column(Text)


class AuthAuditLog(Base):
    __tablename__ = "auth_audit_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id")
    )
    event: Mapped[str] = mapped_column(Text, nullable=False)
    ip_address: Mapped[str | None] = mapped_column(INET)
    user_agent: Mapped[str | None] = mapped_column(Text)
    data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Preferences(Base):
    __tablename__ = "preferences"

    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), primary_key=True
    )
    focus: Mapped[str] = mapped_column(
        Enum("markets", "crypto", "both", name="focus"), nullable=False, default="both"
    )
    content_style: Mapped[str] = mapped_column(
        Enum("concise", "balanced", "detailed", name="content_style"),
        nullable=False, default="balanced",
    )
    verification_strictness: Mapped[str] = mapped_column(
        Enum("loose", "balanced", "strict", name="verification_strictness"),
        nullable=False, default="balanced",
    )
    notification_frequency: Mapped[str] = mapped_column(
        Enum("off", "instant", "daily", "weekly", name="notification_frequency"),
        nullable=False, default="daily",
    )
    theme_mode: Mapped[str] = mapped_column(
        Enum("dark", "light", name="theme_mode"),
        nullable=False, default="dark", server_default="dark",
    )
    custom_topics: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class SourceCatalog(Base):
    __tablename__ = "source_catalog"

    key: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    focus: Mapped[str] = mapped_column(
        Enum("markets", "crypto", "both", name="focus", create_type=False), nullable=False
    )
    editorial_confidence: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class WorkspaceSource(Base):
    __tablename__ = "workspace_sources"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), primary_key=True
    )
    source_key: Mapped[str] = mapped_column(
        Text, ForeignKey("source_catalog.key"), primary_key=True
    )
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    confidence_override: Mapped[int | None] = mapped_column(Integer)
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class WorkspaceCustomSource(Base):
    __tablename__ = "workspace_custom_sources"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    url: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        Enum("pending_verification", "active", "rejected", name="custom_source_status"),
        nullable=False, default="pending_verification",
    )
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AlertPreference(Base):
    __tablename__ = "alert_preferences"

    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), primary_key=True
    )
    type: Mapped[str] = mapped_column(
        Enum(
            "security", "system", "instant_alert", "daily_digest", "weekly_digest",
            "verification", "publishing", "chat",
            name="activity_type",
        ),
        primary_key=True,
    )
    channel: Mapped[str] = mapped_column(
        Enum("in_app", "push", "email", name="alert_channel"), primary_key=True
    )
    frequency: Mapped[str] = mapped_column(
        Enum(
            "off", "instant", "daily", "weekly",
            name="notification_frequency", create_type=False,
        ),
        nullable=False, default="instant",
    )
    quiet_hours: Mapped[dict | None] = mapped_column(JSONB)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AlertDevice(Base):
    __tablename__ = "alert_devices"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    platform: Mapped[str] = mapped_column(
        Enum("ios", "android", "web", name="device_platform", create_type=False),
        nullable=False,
    )
    push_token: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    app_version: Mapped[str | None] = mapped_column(Text)
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    disabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ActivityInbox(Base):
    __tablename__ = "activity_inbox"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE")
    )
    type: Mapped[str] = mapped_column(
        Enum(
            "security", "system", "instant_alert", "daily_digest", "weekly_digest",
            "verification", "publishing", "chat",
            name="activity_type", create_type=False,
        ),
        nullable=False,
    )
    severity: Mapped[str] = mapped_column(
        Enum("info", "warning", "error", name="activity_severity", create_type=False),
        nullable=False,
        server_default="info",
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str | None] = mapped_column(Text)
    data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # Phase 6: traceability back to the outbox event that produced this row.
    source_event_type: Mapped[str | None] = mapped_column(Text)
    source_event_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AutomationLog(Base):
    """Phase 6 — one row per dispatcher decision (created OR suppressed).

    The transparency record behind the Automation Hub: it explains both why a
    notification appeared and why one didn't. UNIQUE(account_id,
    triggered_by_event_id, channel) is the dispatcher's idempotency key under
    the outbox's at-least-once redelivery contract — one decision per
    (account, event) per delivery channel (Wave C added the channel
    discriminator so a push decision can join the in_app one, migration 0017).
    """

    __tablename__ = "automation_log"
    __table_args__ = (
        UniqueConstraint(
            "account_id",
            "triggered_by_event_id",
            "channel",
            name="uq_automation_log_account_event_channel",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    activity_inbox_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("activity_inbox.id", ondelete="SET NULL")
    )
    triggered_by_event_type: Mapped[str] = mapped_column(Text, nullable=False)
    triggered_by_event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    action_taken: Mapped[str] = mapped_column(Text, nullable=False)
    # Which delivery channel this decision is about. No default on purpose —
    # every writer states its channel explicitly (migration 0017).
    channel: Mapped[str] = mapped_column(
        Enum("in_app", "push", "email", name="alert_channel", create_type=False),
        nullable=False,
    )
    # WHY the decision went the way it did — a real failure reason for
    # push_failed/email_failed ("no_registered_device", a provider error
    # string). NULL for successes/suppressions and for rows written before
    # migration 0024 introduced reason capture — the UI states that honestly.
    detail: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class DigestRun(Base):
    """Phase 6 Wave B — one row per SENT digest window.

    The DigestWorker's idempotency record, mirroring automation_log's approach:
    UNIQUE(account_id, activity_type, frequency, window_start) makes a second
    tick inside the same window a safe no-op. A window with zero source rows
    writes NO row here (silence, not an empty digest), so the next digest's
    window simply stretches back further — nothing is lost or duplicated.
    """

    __tablename__ = "digest_runs"
    __table_args__ = (
        UniqueConstraint(
            "account_id", "activity_type", "frequency", "window_start",
            name="uq_digest_runs_window",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    # The single content category this digest bundled (security/system/
    # verification/publishing) — NOT the daily_digest/weekly_digest bundle-row
    # marker, which lives on the activity_inbox row the run produced.
    activity_type: Mapped[str] = mapped_column(
        Enum(
            "security", "system", "instant_alert", "daily_digest", "weekly_digest",
            "verification", "publishing", "chat",
            name="activity_type", create_type=False,
        ),
        nullable=False,
    )
    frequency: Mapped[str] = mapped_column(
        Enum(
            "off", "instant", "daily", "weekly",
            name="notification_frequency", create_type=False,
        ),
        nullable=False,
    )
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AnalyticsEventRaw(Base):
    """Phase 7 Wave A — one lightweight fact per delivered bus event (Source A).

    NOT a re-store of the envelope (ADR-047): just "event X happened for
    workspace Y at time Z". `source_event_id` is the envelope's own id — which
    is the outbox row's id (queue/outbox.py) — so at-least-once redelivery
    hits the unique constraint and is a safe no-op.
    """

    __tablename__ = "analytics_events_raw"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    source_event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, unique=True
    )
    event_name: Mapped[str] = mapped_column(Text, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AnalyticsRollupDaily(Base):
    """Phase 7 Wave A — the single read model behind every Wave B chart.

    One row per (workspace, metric, UTC day). The unique constraint is what
    makes a rollup refresh an UPSERT of a freshly recomputed value, never an
    accumulate — re-running a refresh always converges (ADR-047). Sparse:
    zero-activity days write no row.
    """

    __tablename__ = "analytics_rollups_daily"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id", "metric_key", "date",
            name="uq_analytics_rollups_ws_metric_date",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    metric_key: Mapped[str] = mapped_column(Text, nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    value: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class FeatureFlag(Base):
    __tablename__ = "feature_flags"

    key: Mapped[str] = mapped_column(Text, primary_key=True)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    default_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class FeatureFlagOverride(Base):
    __tablename__ = "feature_flag_overrides"

    flag_key: Mapped[str] = mapped_column(Text, ForeignKey("feature_flags.key"), primary_key=True)
    scope: Mapped[str] = mapped_column(
        Enum("account", "workspace", name="flag_scope"), primary_key=True
    )
    scope_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class OnboardingState(Base):
    __tablename__ = "onboarding_state"

    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), primary_key=True
    )
    current_step: Mapped[str] = mapped_column(
        Enum(
            "welcome", "focus_sources", "notifications_permissions",
            "style_strictness", "complete",
            name="onboarding_step",
        ),
        nullable=False, default="welcome",
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


# ============================================================================
# Phase 3 — Intake (Batch 1)
# ============================================================================


class IntakeSource(Base):
    __tablename__ = "intake_sources"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(
        Enum("gmail", "rss", "webhook", "api_pull", "manual", name="intake_source_kind"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    origin_kind: Mapped[str] = mapped_column(
        Enum("catalog", "custom", name="intake_origin_kind"), nullable=False
    )
    origin_catalog_key: Mapped[str | None] = mapped_column(Text)
    origin_custom_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    cursor: Mapped[dict | None] = mapped_column(JSONB)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    consecutive_failures: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(
        Enum(
            "healthy", "degraded", "auth_required", "disabled",
            name="intake_source_status",
        ),
        nullable=False,
        default="healthy",
    )
    last_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class IntakeCredentials(Base):
    __tablename__ = "intake_credentials"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    intake_source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("intake_sources.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    encrypted_token: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    encrypted_refresh_token: Mapped[bytes | None] = mapped_column(LargeBinary)
    kms_key_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class IntakeItem(Base):
    __tablename__ = "intake_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    intake_source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("intake_sources.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider_name: Mapped[str] = mapped_column(Text, nullable=False)
    external_id: Mapped[str] = mapped_column(Text, nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    fingerprint: Mapped[str] = mapped_column(Text, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class IntakeItemNormalized(Base):
    __tablename__ = "intake_items_normalized"

    intake_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("intake_items.id", ondelete="CASCADE"),
        primary_key=True,
    )
    sender_domain: Mapped[str | None] = mapped_column(Text)
    sender_label: Mapped[str | None] = mapped_column(Text)
    subject: Mapped[str | None] = mapped_column(Text)
    body_text: Mapped[str | None] = mapped_column(Text)
    links: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    item_metadata: Mapped[dict] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )
    normalized_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    normalizer_version: Mapped[int] = mapped_column(Integer, nullable=False)


class IntakeItemDuplicate(Base):
    __tablename__ = "intake_items_duplicates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    fingerprint: Mapped[str] = mapped_column(Text, nullable=False)
    intake_source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("intake_sources.id", ondelete="CASCADE"),
        nullable=False,
    )
    external_id: Mapped[str] = mapped_column(Text, nullable=False)
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class IntakeDedupeIndex(Base):
    __tablename__ = "intake_dedupe_index"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), primary_key=True
    )
    fingerprint: Mapped[str] = mapped_column(Text, primary_key=True)
    first_intake_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("intake_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    duplicate_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class IntakeAuditLog(Base):
    __tablename__ = "intake_audit_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    intake_source_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("intake_sources.id", ondelete="CASCADE")
    )
    event: Mapped[str] = mapped_column(Text, nullable=False)
    data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class WebhookIdempotencyKey(Base):
    __tablename__ = "webhook_idempotency_keys"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), primary_key=True
    )
    intake_source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("intake_sources.id", ondelete="CASCADE"),
        primary_key=True,
    )
    idempotency_key: Mapped[str] = mapped_column(Text, primary_key=True)
    seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class OutboxEvent(Base):
    __tablename__ = "outbox_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_name: Mapped[str] = mapped_column(Text, nullable=False)
    event: Mapped[dict] = mapped_column(JSONB, nullable=False)
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(Text)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class OutboxDeadLetter(Base):
    __tablename__ = "outbox_dead_letter"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    original_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    event_name: Mapped[str] = mapped_column(Text, nullable=False)
    event: Mapped[dict] = mapped_column(JSONB, nullable=False)
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    moved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    final_error: Mapped[str] = mapped_column(Text, nullable=False)
    total_attempts: Mapped[int] = mapped_column(Integer, nullable=False)


class WorkspaceDeletionOrphanCredential(Base):
    """CR-6 holding pen: credentials whose upstream revoke failed during a
    workspace deletion. Forensic pointers (no FKs — the workspace is gone)."""

    __tablename__ = "workspace_deletion_orphan_credentials"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    intake_source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    provider_kind: Mapped[str] = mapped_column(Text, nullable=False)
    detail: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


# ============================================================================
# Phase 4 Wave A — claims + AI budget
# ============================================================================


class Claim(Base):
    __tablename__ = "claims"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    intake_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("intake_items.id", ondelete="CASCADE"), nullable=False
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    subject: Mapped[str] = mapped_column(Text, nullable=False)
    predicate: Mapped[str] = mapped_column(Text, nullable=False)
    object: Mapped[str | None] = mapped_column(Text)
    epistemic_type: Mapped[str] = mapped_column(
        Enum(
            "fact", "claim", "rumor", "speculation", "opinion", "unclassified",
            name="epistemic_type",
        ),
        nullable=False,
        default="unclassified",
    )
    extractor_version: Mapped[int] = mapped_column(Integer, nullable=False)
    classifier_version: Mapped[int | None] = mapped_column(Integer)
    requires_analyst_review: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    superseded_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("claims.id")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class WorkspaceAIBudget(Base):
    """Per-workspace daily AI token ledger. Checked before every AI call."""

    __tablename__ = "workspace_ai_budget"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), primary_key=True
    )
    budget_date: Mapped[date] = mapped_column(Date, primary_key=True)
    tokens_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    budget_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=100000)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


# ============================================================================
# Phase 4 Wave B — evidence + claim↔evidence links
# ============================================================================


class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    intake_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("intake_items.id", ondelete="CASCADE"), nullable=False
    )
    evidence_type: Mapped[str] = mapped_column(
        Enum(
            "corroboration", "contradiction", "context",
            "primary_source", "secondary_source", "inference",
            name="evidence_type",
        ),
        nullable=False,
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    source_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ClaimEvidenceLink(Base):
    __tablename__ = "claim_evidence_links"

    claim_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("claims.id", ondelete="CASCADE"), primary_key=True
    )
    evidence_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("evidence.id", ondelete="CASCADE"), primary_key=True
    )
    relationship: Mapped[str] = mapped_column(
        Enum("supports", "contradicts", "contextualizes", name="evidence_relationship"),
        nullable=False,
    )
    strength: Mapped[float] = mapped_column(Float, nullable=False)
    linker_version: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


# ============================================================================
# Phase 4 Wave C — verification runs, source credibility, audit log
# ============================================================================


class VerificationRun(Base):
    """One versioned, reproducible scoring pass on one claim. Append-only."""

    __tablename__ = "verification_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    claim_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("claims.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        Enum("pending", "running", "complete", "failed", name="verification_status"),
        nullable=False,
        default="pending",
    )
    outcome: Mapped[str | None] = mapped_column(
        Enum(
            "verified", "unverified", "contested", "unverifiable",
            name="verification_outcome",
        )
    )
    source_trust_score: Mapped[float | None] = mapped_column(Float)
    cross_reference_count: Mapped[int | None] = mapped_column(Integer)
    evidence_strength: Mapped[float | None] = mapped_column(Float)
    recency_score: Mapped[float | None] = mapped_column(Float)
    claim_specificity: Mapped[float | None] = mapped_column(Float)
    primary_source_flag: Mapped[bool | None] = mapped_column(Boolean)
    confidence_score: Mapped[float | None] = mapped_column(Float)
    factors: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    engine_version: Mapped[int] = mapped_column(Integer, nullable=False)
    scoring_version: Mapped[int] = mapped_column(Integer, nullable=False)
    tokens_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SourceCredibilityRecord(Base):
    """Per-(workspace, source) running accuracy. source_id == intake_sources.id."""

    __tablename__ = "source_credibility_records"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), primary_key=True
    )
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    accuracy_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    verified_claim_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    contested_claim_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_claim_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    bias_indicators: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    topic_reliability: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    last_evaluated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class VerificationAuditLog(Base):
    """Append-only Phase 4 pipeline decision log (separate from auth_audit_log)."""

    __tablename__ = "verification_audit_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    account_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    event: Mapped[str] = mapped_column(Text, nullable=False)
    entity_type: Mapped[str] = mapped_column(Text, nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


# ============================================================================
# Phase 4 Wave D — conflict detection, resolution, analyst review
# ============================================================================


class ConflictRecord(Base):
    """A detected conflict between two claims on the same subject.

    Stored with canonical ordering: claim_a_id is always the smaller UUID
    (enforced in the service), so the UNIQUE (workspace, a, b) dedupes a pair
    from either detection direction.
    """

    __tablename__ = "conflict_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    claim_a_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("claims.id"), nullable=False
    )
    claim_b_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("claims.id"), nullable=False
    )
    conflict_type: Mapped[str] = mapped_column(
        Enum(
            "direct_contradiction", "factual_disagreement",
            "temporal_inconsistency", "scope_difference",
            name="conflict_type_enum",
        ),
        nullable=False,
    )
    severity: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(
        Enum(
            "open", "resolved_a_wins", "resolved_b_wins",
            "resolved_inconclusive", "resolved_system", "analyst_reviewed",
            name="conflict_status_enum",
        ),
        nullable=False,
        default="open",
    )
    resolution_note: Mapped[str | None] = mapped_column(Text)
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id")
    )
    resolved_by_kind: Mapped[str | None] = mapped_column(
        Enum("system", "analyst", name="conflict_resolver_enum")
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    # UNIQUE (workspace_id, claim_a_id, claim_b_id) lives in migration 0007
    # (uq_conflict_records_pair); the repository upserts via index_elements.


class AnalystReview(Base):
    """Append-only record of one analyst decision. Overrides write HERE —
    they never mutate the original claim / verification_run rows."""

    __tablename__ = "analyst_reviews"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    entity_type: Mapped[str] = mapped_column(
        Enum("claim", "intelligence_object", "conflict", name="analyst_entity_enum"),
        nullable=False,
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    outcome: Mapped[str] = mapped_column(
        Enum(
            "approved", "rejected", "flagged",
            "override_verified", "override_unverified",
            "conflict_resolved_a", "conflict_resolved_b", "conflict_inconclusive",
            name="analyst_outcome_enum",
        ),
        nullable=False,
    )
    note: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


# ============================================================================
# Phase 4 Wave E — intelligence objects + research workspaces/packets
# ============================================================================


class IntelligenceObject(Base):
    """The fan-in: N non-superseded claims for one intake item → one scored
    object. UNIQUE (workspace_id, intake_item_id) — one per item."""

    __tablename__ = "intelligence_objects"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    intake_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("intake_items.id"), nullable=False
    )
    epistemic_type: Mapped[str] = mapped_column(
        Enum(
            "fact", "claim", "rumor", "speculation", "opinion", "unclassified",
            name="epistemic_type",
        ),
        nullable=False,
    )
    confidence_score: Mapped[float | None] = mapped_column(Float)
    verification_status: Mapped[str] = mapped_column(
        Enum(
            "unverified", "verified", "contested",
            "analyst_approved", "analyst_rejected",
            name="intel_status_enum",
        ),
        nullable=False,
        default="unverified",
    )
    claim_ids: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=False, default=list
    )
    conflict_ids: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=False, default=list
    )
    key_facts: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    headline: Mapped[str] = mapped_column(Text, nullable=False)
    scoring_version: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    # UNIQUE (workspace_id, intake_item_id) lives in migration 0008.


class ResearchWorkspace(Base):
    __tablename__ = "research_workspaces"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        Enum("active", "archived", name="rws_status_enum"),
        nullable=False,
        default="active",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ResearchWorkspaceItem(Base):
    __tablename__ = "research_workspace_items"

    research_workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("research_workspaces.id", ondelete="CASCADE"),
        primary_key=True,
    )
    intelligence_object_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("intelligence_objects.id"), primary_key=True
    )
    added_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False
    )
    note: Mapped[str | None] = mapped_column(Text)  # CHECK len<=500 in migration
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ResearchPacket(Base):
    __tablename__ = "research_packets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    research_workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("research_workspaces.id"), nullable=False
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        Enum("assembling", "ready", "consumed", name="packet_status_enum"),
        nullable=False,
        default="assembling",
    )
    intelligence_object_ids: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=False, default=list
    )
    conflict_acknowledged_ids: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=False, default=list
    )
    ready_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # consumed_at is written by Phase 5 ONLY — never by Phase 4 code.
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


# ============================================================================
# Phase 5 Wave A — content drafts + versions + citations
# ============================================================================


class ContentDraft(Base):
    """One AI-generated draft per research packet. UNIQUE (workspace_id,
    packet_id) — exactly one draft per packet (generate is idempotent on it)."""

    __tablename__ = "content_drafts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False
    )
    packet_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("research_packets.id"), nullable=False
    )
    # FK to content_templates lands in migration 0010 (Wave B). Nullable UUID now.
    template_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    format: Mapped[str] = mapped_column(
        Enum(
            "tweet_thread", "linkedin_post", "newsletter_section",
            "article", "report_summary", "custom",
            name="content_format_enum",
        ),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        Enum(
            "draft", "in_review", "changes_requested", "approved",
            "scheduled", "published", "rejected", "archived",
            name="draft_status_enum",
        ),
        nullable=False,
        default="draft",
    )
    current_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    generation_model: Mapped[str] = mapped_column(Text, nullable=False)
    generation_version: Mapped[int] = mapped_column(Integer, nullable=False)
    word_count: Mapped[int | None] = mapped_column(Integer)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    # UNIQUE (workspace_id, packet_id) lives in migration 0009.


class DraftVersion(Base):
    """Append-only edit history. Every save and every regeneration inserts a
    new row; nothing is ever overwritten. UNIQUE (draft_id, version_number)."""

    __tablename__ = "draft_versions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    draft_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("content_drafts.id", ondelete="CASCADE"), nullable=False
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_html: Mapped[str | None] = mapped_column(Text)
    edited_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False
    )
    edit_note: Mapped[str | None] = mapped_column(Text)
    word_count: Mapped[int | None] = mapped_column(Integer)
    token_count: Mapped[int | None] = mapped_column(Integer)
    is_ai_generated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    # UNIQUE (draft_id, version_number) lives in migration 0009.


class DraftCitation(Base):
    """Provenance edge: a draft drew from an intelligence object. The chain back
    to verified claims and intake items runs through intelligence_objects."""

    __tablename__ = "draft_citations"

    draft_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("content_drafts.id", ondelete="CASCADE"), primary_key=True
    )
    intelligence_object_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("intelligence_objects.id"), primary_key=True
    )
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


# ============================================================================
# Phase 5 Wave B — content templates
# ============================================================================


class ContentTemplate(Base):
    """Reusable format definition. One default per (workspace, format) enforced
    by the partial UNIQUE index uq_templates_one_default_per_format."""

    __tablename__ = "content_templates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    format: Mapped[str] = mapped_column(
        Enum(
            "tweet_thread", "linkedin_post", "newsletter_section",
            "article", "report_summary", "custom",
            name="content_format_enum",
            create_type=False,
        ),
        nullable=False,
    )
    tone: Mapped[str] = mapped_column(
        Enum(
            "formal", "analytical", "conversational", "authoritative", "concise",
            name="content_tone_enum",
        ),
        nullable=False,
        default="analytical",
    )
    max_words: Mapped[int | None] = mapped_column(Integer)
    min_words: Mapped[int | None] = mapped_column(Integer)
    structure_hint: Mapped[str | None] = mapped_column(Text)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


# ============================================================================
# Phase 5 Wave C — review workflow + approval
# ============================================================================


class DraftReview(Base):
    """Append-only audit row, one per review action (submit→approve/reject/
    changes_requested). `note` is nullable at the DB layer (frozen schema); the
    non-empty requirement for rejected/changes_requested is a service-layer
    guard (Wave C Refinement 1), mirroring analyst_reviews."""

    __tablename__ = "draft_reviews"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    draft_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("content_drafts.id", ondelete="CASCADE"), nullable=False
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False
    )
    outcome: Mapped[str] = mapped_column(
        Enum(
            "approved", "rejected", "changes_requested",
            name="review_outcome_enum",
        ),
        nullable=False,
    )
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    # idx_draft_reviews_draft (draft_id, created_at DESC) lives in migration 0011.


# ============================================================================
# Phase 5 Wave D — publish targets + publications (channel delivery)
# ============================================================================


class PublishTarget(Base):
    """A configured per-workspace delivery channel. `credentials` +
    `credentials_iv` hold AES-256-GCM ciphertext/IV and are NEVER serialized to
    an API response (write-only — see services/targets/schemas.py)."""

    __tablename__ = "publish_targets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    channel: Mapped[str] = mapped_column(
        Enum(
            "twitter_x", "linkedin", "email_newsletter", "notion",
            "webhook", "export",
            name="publish_channel_enum",
            create_type=False,
        ),
        nullable=False,
    )
    credentials: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    credentials_iv: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_health_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_health_ok: Mapped[bool | None] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Publication(Base):
    """One delivery attempt for (draft, version, target). The UNIQUE constraint
    uq_publications_draft_version_target (draft_id, version_number, target_id) is
    the idempotency guarantee — the engine inserts ON CONFLICT DO NOTHING and
    re-reads the winner (§16.2)."""

    __tablename__ = "publications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    draft_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("content_drafts.id"), nullable=False
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    target_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("publish_targets.id"), nullable=False
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        Enum(
            "pending", "delivering", "delivered", "failed", "cancelled",
            name="publication_status_enum",
            create_type=False,
        ),
        nullable=False,
        default="pending",
    )
    external_id: Mapped[str | None] = mapped_column(Text)
    external_url: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # WHEN the last engine-level attempt happened (HOW MANY = attempt_count). The
    # transient-failure path stamps it so the Wave E retry re-drive can compute
    # backoff (§16.3). Added in migration 0013.
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    # uq_publications_draft_version_target + idx_publications_* live in migration 0012.


class PublicationCitation(Base):
    """Transparency snapshot: the cited intelligence objects' values AS OF the
    moment the publication row was created. Written in the SAME transaction as
    the pending publication insert (engine._publish_one) so a publication can
    never exist without its provenance record. Read-only afterwards — the
    provenance endpoint serves THESE rows, never a live join back to
    intelligence_objects, so a later re-score cannot rewrite the history of
    what was published. Intelligence-object level only by design (same public
    boundary as publishing/citations.py): no claim or evidence data here."""

    __tablename__ = "publication_citations"

    publication_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("publications.id", ondelete="CASCADE"), primary_key=True
    )
    intelligence_object_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("intelligence_objects.id"), primary_key=True
    )
    headline: Mapped[str] = mapped_column(Text, nullable=False)
    epistemic_type: Mapped[str] = mapped_column(
        Enum(
            "fact", "claim", "rumor", "speculation", "opinion", "unclassified",
            name="epistemic_type",
            create_type=False,
        ),
        nullable=False,
    )
    confidence_score: Mapped[float | None] = mapped_column(Float)
    scoring_version: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshotted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


# ============================================================================
# Public Reader Rev 1 (docs/PUBLIC_READER_ARCHITECTURE.md §6) — backend
# foundation only; no frontend rendering yet.
# ============================================================================


class PublicPage(Base):
    """One row per ContentDraft that has ever reached 'published' — never per
    Publication (a draft may fan out to several external channels but gets
    exactly one public page). Created automatically by the publishing engine
    in the SAME transaction as the draft's status transition to 'published'
    (services/publishing/engine.py, PublishingEngine.publish_draft step 4),
    never by a direct API write.

    `content_snapshot` is DraftVersion.content AS OF the moment of first
    successful publish — matching the frozen-snapshot philosophy
    PublicationCitation already uses for provenance data (§6 "Content is a
    frozen snapshot, never a live read"). A later edit to the internal draft
    never changes what is already public; republishing is out of scope for
    Rev 1.

    `slug` is an opaque, random, non-enumerable public identifier (nanoid) —
    deliberately NOT the invite-token bearer-credential pattern and NOT a
    raw UUID (§6 "URLs are opaque, not sequential, not bearer secrets").

    UNIQUE(content_draft_id) enforces "exactly one public page per draft" at
    the schema level, not just by the engine's own status guard.
    """

    __tablename__ = "public_pages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_draft_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("content_drafts.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    slug: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    content_snapshot: Mapped[str] = mapped_column(Text, nullable=False)
    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class PublicPageCitation(Base):
    """Provenance snapshot for one PublicPage's cited intelligence objects —
    headline, epistemic_type, confidence_score, scoring_version,
    snapshotted_at — frozen in the SAME transaction as the PublicPage row
    (mirrors publication_citations exactly, including its ON CONFLICT DO
    NOTHING composite-PK idempotency).

    Deliberately a SEPARATE table from publication_citations, not a join
    target of it: §6's exposure allow-list is enforced structurally by
    giving the public repository method (services/reader/repository.py)
    only its OWN two tables — public_pages and this one — to SELECT from,
    with no join clause reaching intelligence_objects, claims, or any other
    workspace-internal table."""

    __tablename__ = "public_page_citations"

    public_page_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("public_pages.id", ondelete="CASCADE"), primary_key=True
    )
    intelligence_object_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("intelligence_objects.id"), primary_key=True
    )
    headline: Mapped[str] = mapped_column(Text, nullable=False)
    epistemic_type: Mapped[str] = mapped_column(
        Enum(
            "fact", "claim", "rumor", "speculation", "opinion", "unclassified",
            name="epistemic_type",
            create_type=False,
        ),
        nullable=False,
    )
    confidence_score: Mapped[float | None] = mapped_column(Float)
    scoring_version: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshotted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class CalendarEntry(Base):
    """One explicit schedule of (draft, target) for a future time (Phase 5
    Wave E). UNIQUE (draft_id, target_id) — a draft can schedule each target at
    most once. The CalendarScheduler fires 'scheduled' rows whose scheduled_at
    has arrived through the existing publishing engine."""

    __tablename__ = "calendar_entries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    draft_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("content_drafts.id"), nullable=False
    )
    target_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("publish_targets.id"), nullable=False
    )
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(
        Enum(
            "scheduled", "published", "cancelled", "failed",
            name="calendar_status_enum",
            create_type=False,
        ),
        nullable=False,
        default="scheduled",
    )
    publication_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("publications.id")
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    # uq_calendar_entries_draft_target + idx_calendar_* live in migration 0013.


# ============================================================================
# Billing foundation wave — Stripe/Razorpay subscription state ledger
# ============================================================================


class WorkspaceSubscription(Base):
    """One row per vendor subscription. UNIQUE (provider, provider_subscription_id)
    is the durable cross-reference the webhook handler resolves an inbound
    event against — see services/billing/repository.py.

    `plan` is nullable: until the (not-yet-built) checkout flow stashes the
    target tier in the vendor's own metadata/notes field at creation time, a
    freshly-seen subscription has no known tier. BillingService only ever
    promotes Workspace.plan when this column is populated AND the resolved
    SubscriptionStatus is ACTIVE — never on creation/pending states, and
    never when the tier is still unknown."""

    __tablename__ = "workspace_subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[str] = mapped_column(
        Enum("stripe", "razorpay", name="payment_provider"), nullable=False
    )
    provider_subscription_id: Mapped[str] = mapped_column(Text, nullable=False)
    plan: Mapped[str | None] = mapped_column(
        Enum("glimpse", "focus", "clarity", "vision", name="workspace_plan", create_type=False)
    )
    currency: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        Enum("pending", "active", "past_due", "canceled", name="subscription_status"),
        nullable=False,
        default="pending",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    # uq_workspace_subscriptions_provider_ref + ix_workspace_subscriptions_workspace
    # live in migration 0029.


class PlanPrice(Base):
    """The real, decided price catalog: tier x cadence x currency -> amount.
    plan_id is a stable internal identifier (e.g. "focus_monthly_usd") —
    PaymentProvider.create_subscription takes this, not a raw vendor price
    id or an ad-hoc amount (services/billing/models.py's PlanPriceRef is the
    DB-agnostic snapshot providers resolve it against).

    stripe_price_id/razorpay_plan_id are nullable and NULL for every row as
    of migration 0030 — populating them requires a real vendor API call
    (creating a Stripe Price / Razorpay Plan object), which is out of scope
    until checkout actually goes live. Until then, create_subscription
    resolves the real amount/currency correctly but raises PERMANENT for any
    plan_id whose vendor reference isn't provisioned yet.

    Glimpse has no row here — it's the free tier."""

    __tablename__ = "plan_prices"

    plan_id: Mapped[str] = mapped_column(Text, primary_key=True)
    tier: Mapped[str] = mapped_column(
        Enum("glimpse", "focus", "clarity", "vision", name="workspace_plan", create_type=False),
        nullable=False,
    )
    cadence: Mapped[str] = mapped_column(
        Enum("monthly", "quarterly", "yearly", name="billing_cadence"), nullable=False
    )
    currency: Mapped[str] = mapped_column(
        Enum("USD", "INR", name="billing_currency"), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    stripe_price_id: Mapped[str | None] = mapped_column(Text)
    razorpay_plan_id: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "tier", "cadence", "currency", name="uq_plan_prices_tier_cadence_currency"
        ),
    )


# ============================================================================
# Team/Workspace Rev 2 — invite mechanism (docs/TEAM_WORKSPACE_ARCHITECTURE.md §3)
# ============================================================================


class WorkspaceInvite(Base):
    """A pending (or resolved) invitation to join a workspace. token_hash is
    the SHA-256 hex of a display-once random token — same shape as the
    intake webhook secret convention (services/intake/providers/webhook/
    secrets.py): the raw token is only ever in the invite email, never
    persisted or logged.

    Exactly one of accepted_at/revoked_at is ever set for a resolved invite;
    both NULL means still pending. accept_invite's atomic UPDATE ... WHERE
    accepted_at IS NULL is what makes a concurrent double-accept race safe —
    see services/workspaces/repository.py."""

    __tablename__ = "workspace_invites"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    invited_email: Mapped[str] = mapped_column(CITEXT(), nullable=False)
    role: Mapped[str] = mapped_column(
        Enum("owner", "admin", "editor", "reader", name="workspace_role", create_type=False),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    invited_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class WorkspaceAuditLog(Base):
    """Real, workspace-scoped membership audit trail — the Team nav section's
    Activity view. Same write-only shape as AuthAuditLog (core/audit.py): a
    plain Text `event` column (not a Postgres enum, deliberately — sidesteps
    the ADD VALUE single-transaction trap documented for activity_type) so a
    future event kind is just a new string, no migration required. Rows are
    inserted inside the same transaction as the membership change itself
    (services/workspaces/repository.py's record_activity), never a separate
    commit. `event` values in use: member_invited, member_joined,
    member_removed, role_changed. `subject_email` carries the invited address
    for member_invited (the invitee has no account yet); `subject_account_id`
    carries the real account for member_joined/member_removed/role_changed.
    `role` always carries the role meaningfully associated with the subject
    AFTER the event (invited-as, joined-as, removed-from, changed-to);
    `previous_role` (migration 0033) is set ONLY for role_changed — the role
    the subject held immediately before this change."""

    __tablename__ = "workspace_audit_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    event: Mapped[str] = mapped_column(Text, nullable=False)
    actor_account_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id")
    )
    subject_account_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id")
    )
    subject_email: Mapped[str | None] = mapped_column(Text)
    role: Mapped[str | None] = mapped_column(Text)
    previous_role: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ChatMessage(Base):
    """Team Chat foundation wave — a single workspace-wide channel (no
    conversation/thread concept yet). Deliberately NOT modeled on
    WorkspaceAuditLog: that table is an unpaginated "latest 50" append-only
    log with no edit/delete semantics, which doesn't fit real message
    history (recon: docs/design-reference has no chat mockup, and
    WorkspaceAuditLog's own read path has zero pagination). `body` is
    redacted to null at the API layer (never in this column) once
    `deleted_at` is set — the row and its real content stay in the DB, only
    clients stop seeing it. `edited_at` is set on a real edit and left null
    otherwise. See services/workspaces/repository.py for the cursor-paginated
    read path (ORDER BY created_at, id — a stable compound order so a cursor
    of (created_at, id) never skips or duplicates a row on a timestamp tie)."""

    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    sender_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class WorkspaceChatRead(Base):
    """One row per (workspace, account) — the minimal last-read marker an
    unread indicator needs. Upserted on every real POST
    /workspaces/messages/read; both fields stay null until an account marks
    anything read at least once."""

    __tablename__ = "workspace_chat_reads"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), primary_key=True
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), primary_key=True
    )
    last_read_message_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chat_messages.id", ondelete="SET NULL")
    )
    last_read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Course(Base):
    """Phase 8 Wave A (docs/PHASE_8_TRAINING_ARCHITECTURE.md §2/§4) — a
    Course is platform-wide, NOT per-workspace: the Academy catalog is
    shared across every workspace, so this table deliberately carries no
    workspace_id column at all — there is no "which workspace's course"
    question to answer. Authoring is gated by Account.is_platform_admin at
    the router layer (core/dependencies.py's require_platform_admin), never
    by a workspace-role capability check — §4's corrected reasoning."""

    __tablename__ = "courses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Module(Base):
    """One ordered unit inside a Course. `order` positions modules within
    their course for display — same convention as Lesson.order below."""

    __tablename__ = "modules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Lesson(Base):
    """Belongs to a Module. `video_asset_id` stores the VideoProvider's own
    asset reference (core/video_provider.py) — a Cloudflare Stream video
    uid, never a raw file path (§3). Null until a real upload exists; no
    live upload/playback flow is wired this wave — §3's honest "not
    configured" default (CloudflareStreamProvider) is the real state until
    live credentials exist."""

    __tablename__ = "lessons"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    module_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("modules.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    video_asset_id: Mapped[str | None] = mapped_column(Text)
    transcript_text: Mapped[str | None] = mapped_column(Text)
    order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Enrollment(Base):
    """One row per (account, course) — composite PK, same shape as
    WorkspaceMember's (workspace_id, account_id) convention. No enrollment
    endpoints exist yet (authoring-only wave); schema only, exercised
    directly by CertificateRepository's own tests."""

    __tablename__ = "enrollments"

    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), primary_key=True
    )
    course_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), primary_key=True
    )
    enrolled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class LessonProgress(Base):
    """One row per (account, lesson) marking real completion. Composite PK
    — a lesson is either completed or not for a given account, never
    re-inserted."""

    __tablename__ = "lesson_progress"

    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), primary_key=True
    )
    lesson_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lessons.id", ondelete="CASCADE"), primary_key=True
    )
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Certificate(Base):
    """Issued when every lesson in a course has a LessonProgress row for
    the same account (services/training/repository.py's
    CertificateRepository.issue_if_eligible) — never issued directly by an
    API write. Composite PK: at most one certificate per (account, course)."""

    __tablename__ = "certificates"

    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), primary_key=True
    )
    course_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), primary_key=True
    )
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Symbol(Base):
    """Phase 9 Wave A (docs/PHASE_9_MARKET_TERMINAL_ARCHITECTURE.md §3) — a
    tradable instrument. Platform-wide, same shape as Course (§2 of the
    Phase 8 doc): the symbol catalog is shared across every workspace, so
    this table deliberately carries no workspace_id column. asset_class
    covers only the two classes evidenced in the real design-reference
    mockups (terminal.jsx's heatmap sectors, technical.jsx's BTC/USD
    chart) — widen additively when a real screen needs a third, don't
    pre-guess the set."""

    __tablename__ = "symbols"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticker: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    asset_class: Mapped[str] = mapped_column(
        Enum("equity", "crypto", name="symbol_asset_class"), nullable=False
    )
    exchange: Mapped[str] = mapped_column(Text, nullable=False)
    currency: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (UniqueConstraint("ticker", "exchange", name="uq_symbols_ticker_exchange"),)


class PriceBar(Base):
    """The OHLCV cache (§3) — explicitly a CACHE, not a source of truth;
    populated by whichever real vendor MarketDataProvider eventually wires
    up (§3 of the architecture doc — none is chosen yet). Composite PK
    (symbol_id, timeframe, bar_time): one bar per symbol/timeframe/
    timestamp is the natural dedup key for a re-fetchable cache row, no
    synthetic id needed. `timeframe` enum values match technical.jsx's
    real timeframe tabs exactly (§1) — 1m/5m/15m/1H/4H/1D/1W, nothing
    invented beyond the confirmed mockup."""

    __tablename__ = "price_bars"

    symbol_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("symbols.id", ondelete="CASCADE"), primary_key=True
    )
    timeframe: Mapped[str] = mapped_column(
        Enum("1m", "5m", "15m", "1H", "4H", "1D", "1W", name="bar_timeframe"),
        primary_key=True,
    )
    bar_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    open: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    volume: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Watchlist(Base):
    """§3 — a personal, per-account tracked-symbol list, NOT a shared
    workspace resource. Scoped to account_id only, no workspace_id —
    mirrors AlertPreference's real precedent above (account_id-only,
    despite living inside a workspace-scoped app) for a setting that's
    personal to the user: different teammates in the same workspace want
    different symbols tracked, same reasoning as why notification
    preferences aren't shared across a workspace. `name` defaults to
    'Default', matching technical.jsx's real "Watchlist · DEFAULT" mockup
    label — which implies (not built this wave) room for more than one
    named list per account, so the schema allows it now rather than
    needing a later migration."""

    __tablename__ = "watchlists"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False, server_default="Default")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (UniqueConstraint("account_id", "name", name="uq_watchlists_account_name"),)


class WatchlistItem(Base):
    """One row per (watchlist, symbol) — composite PK, same shape as
    Enrollment's (account_id, course_id) convention (Phase 8 §2). `order`
    positions symbols within their watchlist for display, same convention
    as Module.order/Lesson.order above."""

    __tablename__ = "watchlist_items"

    watchlist_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("watchlists.id", ondelete="CASCADE"), primary_key=True
    )
    symbol_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("symbols.id", ondelete="CASCADE"), primary_key=True
    )
    order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
