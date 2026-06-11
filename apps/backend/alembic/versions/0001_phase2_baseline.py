"""Phase 2 baseline schema.

Creates every Phase 2 table:
  accounts, profiles, workspaces, workspace_members,
  sessions, auth_audit_log,
  preferences, source_catalog, workspace_sources, workspace_custom_sources,
  alert_preferences, alert_devices, activity_inbox,
  feature_flags, feature_flag_overrides,
  onboarding_state

Seeds source_catalog and feature_flags defaults.

Revision ID: 0001_phase2_baseline
Revises:
Create Date: 2026-06-06
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001_phase2_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # citext for case-insensitive email
    op.execute("CREATE EXTENSION IF NOT EXISTS citext")

    # ---------------- accounts ----------------
    op.create_table(
        "accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", postgresql.CITEXT(), nullable=False, unique=True),
        sa.Column("email_verified_at", sa.DateTime(timezone=True)),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "status",
            sa.Enum("pending", "active", "suspended", "deleted", name="account_status"),
            nullable=False,
            server_default="active",
        ),
        sa.Column("mfa_secret", sa.Text()),
        sa.Column("mfa_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("failed_login_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("locked_until", sa.DateTime(timezone=True)),
        sa.Column("last_login_at", sa.DateTime(timezone=True)),
        sa.Column("is_platform_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
    )

    # ---------------- workspaces ----------------
    op.create_table(
        "workspaces",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum("personal", "team", name="workspace_kind"),
            nullable=False,
            server_default="personal",
        ),
        sa.Column(
            "owner_account_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("accounts.id"),
            nullable=False,
        ),
        sa.Column(
            "plan",
            sa.Enum("free", "pro", "enterprise", name="workspace_plan"),
            nullable=False,
            server_default="free",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
    )

    # ---------------- workspace_members ----------------
    op.create_table(
        "workspace_members",
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "account_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("accounts.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "role",
            sa.Enum("owner", "admin", "editor", "reader", name="workspace_role"),
            nullable=False,
        ),
        sa.Column("invited_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("accounts.id")),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("removed_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_workspace_members_account", "workspace_members", ["account_id"])

    # ---------------- profiles ----------------
    op.create_table(
        "profiles",
        sa.Column(
            "account_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("accounts.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("avatar_url", sa.Text()),
        sa.Column("headline", sa.Text()),
        sa.Column("timezone", sa.Text(), nullable=False, server_default="UTC"),
        sa.Column("locale", sa.Text(), nullable=False, server_default="en-US"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # ---------------- sessions ----------------
    op.create_table(
        "sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "account_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("refresh_token_hash", sa.Text(), nullable=False, unique=True),
        sa.Column("parent_session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sessions.id")),
        sa.Column("device_id", sa.Text(), nullable=False),
        sa.Column("device_label", sa.Text(), nullable=False),
        sa.Column(
            "device_platform",
            sa.Enum("ios", "android", "web", name="device_platform"),
            nullable=False,
        ),
        sa.Column("ip_address", postgresql.INET()),
        sa.Column("user_agent", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("revoked_reason", sa.Text()),
    )
    op.create_index(
        "ix_sessions_active",
        "sessions",
        ["account_id"],
        postgresql_where=sa.text("revoked_at IS NULL"),
    )
    op.create_index("ix_sessions_expires", "sessions", ["expires_at"])

    # ---------------- auth_audit_log ----------------
    op.create_table(
        "auth_audit_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("accounts.id")),
        sa.Column("event", sa.Text(), nullable=False),
        sa.Column("ip_address", postgresql.INET()),
        sa.Column("user_agent", sa.Text()),
        sa.Column("data", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "ix_auth_audit_account_time", "auth_audit_log", ["account_id", "created_at"]
    )

    # ---------------- preferences ----------------
    op.create_table(
        "preferences",
        sa.Column(
            "account_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("accounts.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "focus",
            sa.Enum("markets", "crypto", "both", name="focus"),
            nullable=False,
            server_default="both",
        ),
        sa.Column(
            "content_style",
            sa.Enum("concise", "balanced", "detailed", name="content_style"),
            nullable=False,
            server_default="balanced",
        ),
        sa.Column(
            "verification_strictness",
            sa.Enum("loose", "balanced", "strict", name="verification_strictness"),
            nullable=False,
            server_default="balanced",
        ),
        sa.Column(
            "notification_frequency",
            sa.Enum("off", "instant", "daily", "weekly", name="notification_frequency"),
            nullable=False,
            server_default="daily",
        ),
        sa.Column("custom_topics", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # ---------------- source_catalog ----------------
    op.create_table(
        "source_catalog",
        sa.Column("key", sa.Text(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column(
            "focus",
            sa.Enum("markets", "crypto", "both", name="focus", create_type=False),
            nullable=False,
        ),
        sa.Column("editorial_confidence", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # ---------------- workspace_sources ----------------
    op.create_table(
        "workspace_sources",
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "source_key", sa.Text(), sa.ForeignKey("source_catalog.key"), primary_key=True
        ),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("confidence_override", sa.Integer()),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # ---------------- workspace_custom_sources ----------------
    op.create_table(
        "workspace_custom_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("pending_verification", "active", "rejected", name="custom_source_status"),
            nullable=False,
            server_default="pending_verification",
        ),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # ---------------- alert_preferences ----------------
    op.create_table(
        "alert_preferences",
        sa.Column(
            "account_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("accounts.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "type",
            sa.Enum(
                "security", "system", "instant_alert", "daily_digest", "weekly_digest",
                name="activity_type",
            ),
            primary_key=True,
        ),
        sa.Column(
            "channel",
            sa.Enum("in_app", "push", "email", name="alert_channel"),
            primary_key=True,
        ),
        sa.Column(
            "frequency",
            sa.Enum(
                "off", "instant", "daily", "weekly",
                name="notification_frequency", create_type=False,
            ),
            nullable=False,
            server_default="instant",
        ),
        sa.Column("quiet_hours", postgresql.JSONB()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # ---------------- alert_devices ----------------
    op.create_table(
        "alert_devices",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "account_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "platform",
            sa.Enum("ios", "android", "web", name="device_platform", create_type=False),
            nullable=False,
        ),
        sa.Column("push_token", sa.Text(), nullable=False, unique=True),
        sa.Column("app_version", sa.Text()),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("disabled_at", sa.DateTime(timezone=True)),
    )

    # ---------------- activity_inbox ----------------
    op.create_table(
        "activity_inbox",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "account_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
        ),
        sa.Column(
            "type",
            sa.Enum(
                "security", "system", "instant_alert", "daily_digest", "weekly_digest",
                name="activity_type", create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("body", sa.Text()),
        sa.Column("data", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("read_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_activity_account_time", "activity_inbox", ["account_id", "created_at"])

    # ---------------- feature_flags ----------------
    op.create_table(
        "feature_flags",
        sa.Column("key", sa.Text(), primary_key=True),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("default_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # ---------------- feature_flag_overrides ----------------
    op.create_table(
        "feature_flag_overrides",
        sa.Column("flag_key", sa.Text(), sa.ForeignKey("feature_flags.key"), primary_key=True),
        sa.Column(
            "scope",
            sa.Enum("account", "workspace", name="flag_scope"),
            primary_key=True,
        ),
        sa.Column("scope_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # ---------------- onboarding_state ----------------
    op.create_table(
        "onboarding_state",
        sa.Column(
            "account_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("accounts.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "current_step",
            sa.Enum(
                "welcome", "focus_sources", "notifications_permissions",
                "style_strictness", "complete",
                name="onboarding_step",
            ),
            nullable=False,
            server_default="welcome",
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # ---------------- seeds: feature_flags ----------------
    flags_table = sa.table(
        "feature_flags",
        sa.column("key", sa.Text()),
        sa.column("description", sa.Text()),
        sa.column("default_enabled", sa.Boolean()),
    )
    op.bulk_insert(
        flags_table,
        [
            {"key": "ff_settings", "description": "Settings module", "default_enabled": True},
            {"key": "ff_dashboard", "description": "Dashboard module", "default_enabled": True},
            {"key": "ff_activity", "description": "Activity inbox", "default_enabled": True},
            {"key": "ff_mfa", "description": "MFA UI (interface only in Phase 2)", "default_enabled": False},
            {"key": "ff_research", "description": "Research module", "default_enabled": False},
            {"key": "ff_intake_gmail", "description": "Gmail intake", "default_enabled": False},
            {"key": "ff_intake_rss", "description": "RSS intake", "default_enabled": False},
            {"key": "ff_intake_webhook", "description": "Webhook intake", "default_enabled": False},
            {"key": "ff_verification", "description": "Verification engine", "default_enabled": False},
            {"key": "ff_content_drafts", "description": "Content drafts", "default_enabled": False},
            {"key": "ff_publishing_notion", "description": "Notion publishing", "default_enabled": False},
            {"key": "ff_automation", "description": "Automation engine", "default_enabled": False},
            {"key": "ff_push_delivery", "description": "Push notification delivery", "default_enabled": False},
            {"key": "ff_email_delivery", "description": "Email delivery", "default_enabled": False},
            {"key": "ff_analytics", "description": "Analytics module", "default_enabled": False},
            {"key": "ff_training", "description": "Training module", "default_enabled": False},
            {"key": "ff_team_workspaces", "description": "Team workspaces (future)", "default_enabled": False},
        ],
    )

    # ---------------- seeds: source_catalog (representative starter set) ----------------
    sources_table = sa.table(
        "source_catalog",
        sa.column("key", sa.Text()),
        sa.column("name", sa.Text()),
        sa.column("url", sa.Text()),
        # Must be typed as the enum, not Text — asyncpg binds Text params as
        # VARCHAR, which Postgres refuses to implicitly cast to the enum.
        sa.column("focus", sa.Enum("markets", "crypto", "both", name="focus", create_type=False)),
        sa.column("editorial_confidence", sa.Integer()),
    )
    op.bulk_insert(
        sources_table,
        [
            {"key": "ft", "name": "Financial Times", "url": "https://www.ft.com",
             "focus": "markets", "editorial_confidence": 90},
            {"key": "wsj", "name": "Wall Street Journal", "url": "https://www.wsj.com",
             "focus": "markets", "editorial_confidence": 88},
            {"key": "bloomberg", "name": "Bloomberg", "url": "https://www.bloomberg.com",
             "focus": "markets", "editorial_confidence": 92},
            {"key": "reuters", "name": "Reuters", "url": "https://www.reuters.com",
             "focus": "markets", "editorial_confidence": 90},
            {"key": "coindesk", "name": "CoinDesk", "url": "https://www.coindesk.com",
             "focus": "crypto", "editorial_confidence": 78},
            {"key": "the_block", "name": "The Block", "url": "https://www.theblock.co",
             "focus": "crypto", "editorial_confidence": 82},
            {"key": "decrypt", "name": "Decrypt", "url": "https://decrypt.co",
             "focus": "crypto", "editorial_confidence": 75},
        ],
    )


def downgrade() -> None:
    # Drop in reverse dependency order
    op.drop_table("onboarding_state")
    op.drop_table("feature_flag_overrides")
    op.drop_table("feature_flags")
    op.drop_index("ix_activity_account_time", table_name="activity_inbox")
    op.drop_table("activity_inbox")
    op.drop_table("alert_devices")
    op.drop_table("alert_preferences")
    op.drop_table("workspace_custom_sources")
    op.drop_table("workspace_sources")
    op.drop_table("source_catalog")
    op.drop_table("preferences")
    op.drop_index("ix_auth_audit_account_time", table_name="auth_audit_log")
    op.drop_table("auth_audit_log")
    op.drop_index("ix_sessions_expires", table_name="sessions")
    op.drop_index("ix_sessions_active", table_name="sessions")
    op.drop_table("sessions")
    op.drop_table("profiles")
    op.drop_index("ix_workspace_members_account", table_name="workspace_members")
    op.drop_table("workspace_members")
    op.drop_table("workspaces")
    op.drop_table("accounts")
    for enum_name in [
        "onboarding_step", "flag_scope", "activity_type", "alert_channel",
        "custom_source_status", "notification_frequency", "verification_strictness",
        "content_style", "focus", "device_platform", "workspace_role",
        "workspace_plan", "workspace_kind", "account_status",
    ]:
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")
