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

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    LargeBinary,
    Text,
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
    plan: Mapped[str] = mapped_column(
        Enum("free", "pro", "enterprise", name="workspace_plan"),
        nullable=False,
        default="free",
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
            name="activity_type", create_type=False,
        ),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str | None] = mapped_column(Text)
    data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
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
