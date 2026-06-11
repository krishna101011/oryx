"""Phase 3 — intake baseline schema.

Creates the Phase 3 table set per the frozen Revision 2 spec:
  intake_sources, intake_items, intake_items_normalized,
  intake_items_duplicates, intake_dedupe_index, intake_credentials,
  intake_audit_log, webhook_idempotency_keys,
  outbox_events, outbox_dead_letter

Plus Phase 2 ALTERs:
  source_catalog.provider_kind, source_catalog.provider_config_schema
  workspace_custom_sources.provider_kind, verified_at, rejected_reason

Plus new feature flag rows for intake providers + manual ingest.

Revision ID: 0002_phase3_baseline
Revises: 0001_phase2_baseline
Create Date: 2026-06-07
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0002_phase3_baseline"
down_revision = "0001_phase2_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---------------- Phase 2 ALTERs ----------------
    op.add_column("source_catalog", sa.Column("provider_kind", sa.Text()))
    op.add_column("source_catalog", sa.Column("provider_config_schema", postgresql.JSONB()))
    op.add_column(
        "workspace_custom_sources",
        sa.Column("provider_kind", sa.Text(), nullable=False, server_default="rss"),
    )
    op.add_column("workspace_custom_sources", sa.Column("verified_at", sa.DateTime(timezone=True)))
    op.add_column("workspace_custom_sources", sa.Column("rejected_reason", sa.Text()))

    # ---------------- intake_sources ----------------
    op.create_table(
        "intake_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "kind",
            sa.Enum("gmail", "rss", "webhook", "api_pull", "manual", name="intake_source_kind"),
            nullable=False,
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("config", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column(
            "origin_kind",
            sa.Enum("catalog", "custom", name="intake_origin_kind"),
            nullable=False,
        ),
        sa.Column("origin_catalog_key", sa.Text()),
        sa.Column("origin_custom_id", postgresql.UUID(as_uuid=True)),
        sa.Column("cursor", postgresql.JSONB()),
        sa.Column("last_synced_at", sa.DateTime(timezone=True)),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True)),
        sa.Column("consecutive_failures", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "status",
            sa.Enum(
                "healthy", "degraded", "auth_required", "disabled",
                name="intake_source_status",
            ),
            nullable=False,
            server_default="healthy",
        ),
        sa.Column("last_error", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_intake_sources_workspace", "intake_sources", ["workspace_id"])
    op.create_index(
        "ix_intake_sources_scheduler",
        "intake_sources",
        ["status", "last_synced_at"],
    )
    op.create_index(
        "ix_intake_sources_active",
        "intake_sources",
        ["workspace_id"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    # ---------------- intake_credentials ----------------
    op.create_table(
        "intake_credentials",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "intake_source_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("intake_sources.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("encrypted_token", sa.LargeBinary(), nullable=False),
        sa.Column("encrypted_refresh_token", sa.LargeBinary()),
        sa.Column("kms_key_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("token_expires_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # ---------------- intake_items (immutable raw) ----------------
    op.create_table(
        "intake_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "intake_source_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("intake_sources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("provider_name", sa.Text(), nullable=False),
        sa.Column("external_id", sa.Text(), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("fingerprint", sa.Text(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint(
            "workspace_id", "intake_source_id", "external_id",
            name="uq_intake_items_provider_key",
        ),
    )
    op.create_index(
        "ix_intake_items_workspace_time",
        "intake_items",
        ["workspace_id", sa.text("received_at DESC")],
    )
    op.create_index(
        "ix_intake_items_fingerprint",
        "intake_items",
        ["workspace_id", "fingerprint"],
    )
    op.create_index(
        "ix_intake_items_active",
        "intake_items",
        ["workspace_id"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    # ---------------- intake_items_normalized ----------------
    op.create_table(
        "intake_items_normalized",
        sa.Column(
            "intake_item_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("intake_items.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("sender_domain", sa.Text()),
        sa.Column("sender_label", sa.Text()),
        sa.Column("subject", sa.Text()),
        sa.Column("body_text", sa.Text()),
        sa.Column("links", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("normalized_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("normalizer_version", sa.Integer(), nullable=False),
    )
    op.create_index("ix_normalized_sender_domain", "intake_items_normalized", ["sender_domain"])

    # ---------------- intake_items_duplicates ----------------
    op.create_table(
        "intake_items_duplicates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("fingerprint", sa.Text(), nullable=False),
        sa.Column(
            "intake_source_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("intake_sources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("external_id", sa.Text(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "ix_duplicates_workspace_fingerprint",
        "intake_items_duplicates",
        ["workspace_id", "fingerprint"],
    )

    # ---------------- intake_dedupe_index ----------------
    op.create_table(
        "intake_dedupe_index",
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("fingerprint", sa.Text(), primary_key=True),
        sa.Column(
            "first_intake_item_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("intake_items.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("duplicate_count", sa.Integer(), nullable=False, server_default="0"),
    )

    # ---------------- intake_audit_log ----------------
    op.create_table(
        "intake_audit_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "intake_source_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("intake_sources.id", ondelete="CASCADE"),
        ),
        sa.Column("event", sa.Text(), nullable=False),
        sa.Column("data", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "ix_intake_audit_workspace_time",
        "intake_audit_log",
        ["workspace_id", sa.text("created_at DESC")],
    )

    # ---------------- webhook_idempotency_keys (CR-4) ----------------
    op.create_table(
        "webhook_idempotency_keys",
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "intake_source_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("intake_sources.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("idempotency_key", sa.Text(), primary_key=True),
        sa.Column("seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_webhook_idempotency_seen_at", "webhook_idempotency_keys", ["seen_at"])

    # ---------------- outbox_events ----------------
    op.create_table(
        "outbox_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("event_name", sa.Text(), nullable=False),
        sa.Column("event", postgresql.JSONB(), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("delivered_at", sa.DateTime(timezone=True)),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text()),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True)),
    )
    op.create_index(
        "ix_outbox_undelivered",
        "outbox_events",
        ["created_at"],
        postgresql_where=sa.text("delivered_at IS NULL"),
    )
    op.create_index(
        "ix_outbox_delivered_cleanup",
        "outbox_events",
        ["delivered_at"],
        postgresql_where=sa.text("delivered_at IS NOT NULL"),
    )

    # ---------------- outbox_dead_letter (CR-3) ----------------
    op.create_table(
        "outbox_dead_letter",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("original_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_name", sa.Text(), nullable=False),
        sa.Column("event", postgresql.JSONB(), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True)),
        sa.Column("moved_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("final_error", sa.Text(), nullable=False),
        sa.Column("total_attempts", sa.Integer(), nullable=False),
    )
    op.create_index("ix_outbox_dl_workspace", "outbox_dead_letter", ["workspace_id"])

    # ---------------- feature flag seeds ----------------
    flags_table = sa.table(
        "feature_flags",
        sa.column("key", sa.Text()),
        sa.column("description", sa.Text()),
        sa.column("default_enabled", sa.Boolean()),
    )
    op.bulk_insert(
        flags_table,
        [
            {"key": "ff_intake_api_pull", "description": "API pull intake", "default_enabled": False},
            {"key": "ff_intake_manual", "description": "Manual URL ingest (platform admin only)", "default_enabled": False},
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_outbox_dl_workspace", table_name="outbox_dead_letter")
    op.drop_table("outbox_dead_letter")
    op.drop_index("ix_outbox_delivered_cleanup", table_name="outbox_events")
    op.drop_index("ix_outbox_undelivered", table_name="outbox_events")
    op.drop_table("outbox_events")
    op.drop_index("ix_webhook_idempotency_seen_at", table_name="webhook_idempotency_keys")
    op.drop_table("webhook_idempotency_keys")
    op.drop_index("ix_intake_audit_workspace_time", table_name="intake_audit_log")
    op.drop_table("intake_audit_log")
    op.drop_table("intake_dedupe_index")
    op.drop_index(
        "ix_duplicates_workspace_fingerprint",
        table_name="intake_items_duplicates",
    )
    op.drop_table("intake_items_duplicates")
    op.drop_index("ix_normalized_sender_domain", table_name="intake_items_normalized")
    op.drop_table("intake_items_normalized")
    op.drop_index("ix_intake_items_active", table_name="intake_items")
    op.drop_index("ix_intake_items_fingerprint", table_name="intake_items")
    op.drop_index("ix_intake_items_workspace_time", table_name="intake_items")
    op.drop_table("intake_items")
    op.drop_table("intake_credentials")
    op.drop_index("ix_intake_sources_active", table_name="intake_sources")
    op.drop_index("ix_intake_sources_scheduler", table_name="intake_sources")
    op.drop_index("ix_intake_sources_workspace", table_name="intake_sources")
    op.drop_table("intake_sources")
    op.drop_column("workspace_custom_sources", "rejected_reason")
    op.drop_column("workspace_custom_sources", "verified_at")
    op.drop_column("workspace_custom_sources", "provider_kind")
    op.drop_column("source_catalog", "provider_config_schema")
    op.drop_column("source_catalog", "provider_kind")
    for enum_name in [
        "intake_source_status", "intake_source_kind", "intake_origin_kind",
    ]:
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")
