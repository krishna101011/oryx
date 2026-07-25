# THIS FILE IS GENERATED — DO NOT EDIT.
# Source: packages/shared-types/src/
# Regenerate via: pnpm gen:pydantic
from __future__ import annotations

from datetime import datetime
from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")

# ============================================================================
# Common
# ============================================================================

ErrorCode = Literal[
    "INTERNAL_ERROR", "NOT_FOUND", "VALIDATION_FAILED", "RATE_LIMITED",
    "NOT_IMPLEMENTED", "PROVIDER_ERROR",
    "AUTH_REQUIRED", "AUTH_INVALID_CREDENTIALS", "AUTH_TOKEN_EXPIRED",
    "AUTH_REFRESH_INVALID", "AUTH_REFRESH_REUSE_DETECTED", "AUTH_EMAIL_TAKEN",
    "AUTH_PASSWORD_WEAK", "AUTH_RATE_LIMITED", "AUTH_ACCOUNT_LOCKED",
    "AUTH_MFA_REQUIRED", "AUTH_MFA_INVALID",
    "PERMISSION_DENIED", "FEATURE_DISABLED", "WORKSPACE_NOT_FOUND",
    "ONBOARDING_REQUIRED",
    "PAYMENT_PROVIDER_UNAVAILABLE",
    "INVITE_NOT_FOUND", "INVITE_INVALID", "INVITE_EMAIL_MISMATCH",
]


class _Base(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True, from_attributes=True, extra="ignore",
    )


class Pagination(_Base):
    next_cursor: str | None = Field(default=None, alias="nextCursor")
    prev_cursor: str | None = Field(default=None, alias="prevCursor")


class ResponseMeta(_Base):
    request_id: str = Field(alias="requestId")
    server_time: datetime = Field(alias="serverTime")
    pagination: Pagination | None = None


class ApiResponse(_Base, Generic[T]):
    data: T
    meta: ResponseMeta | None = None


class ApiErrorBody(_Base):
    code: ErrorCode
    message: str
    details: dict[str, Any] | None = None
    request_id: str = Field(alias="requestId")


class ApiError(_Base):
    error: ApiErrorBody


class HealthStatus(_Base):
    status: Literal["ok", "degraded", "down"]
    service: str
    environment: Literal["dev", "staging", "prod"]
    server_time: datetime = Field(alias="serverTime")


class BuildInfo(_Base):
    version: str
    commit: str
    built_at: datetime = Field(alias="builtAt")


# ============================================================================
# Accounts
# ============================================================================

AccountStatus = Literal["pending", "active", "suspended", "deleted"]


class Account(_Base):
    id: str
    email: str
    status: AccountStatus
    email_verified: bool = Field(alias="emailVerified")
    is_platform_admin: bool = Field(default=False, alias="isPlatformAdmin")
    created_at: datetime = Field(alias="createdAt")


User = Account
UserStatus = AccountStatus


# ============================================================================
# Profiles
# ============================================================================


class Profile(_Base):
    account_id: str = Field(alias="accountId")
    display_name: str = Field(alias="displayName")
    avatar_url: str | None = Field(default=None, alias="avatarUrl")
    headline: str | None = None
    timezone: str
    locale: str
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")


class UpdateProfileRequest(_Base):
    display_name: str | None = Field(default=None, alias="displayName")
    avatar_url: str | None = Field(default=None, alias="avatarUrl")
    headline: str | None = None
    timezone: str | None = None
    locale: str | None = None


# ============================================================================
# Workspaces
# ============================================================================

WorkspaceKind = Literal["personal", "team"]
# Billing foundation wave: widened from ("free","pro","enterprise") to the
# real 4-tier model. See migration 0029_billing_foundation.py for the
# free/pro/enterprise -> glimpse/focus/vision data mapping and why the
# retired names are dropped here rather than kept alongside the new ones.
WorkspacePlan = Literal["glimpse", "focus", "clarity", "vision"]
Role = Literal["owner", "admin", "editor", "reader"]


class Workspace(_Base):
    id: str
    name: str
    kind: WorkspaceKind
    plan: WorkspacePlan
    created_at: datetime = Field(alias="createdAt")


class WorkspaceMember(_Base):
    workspace_id: str = Field(alias="workspaceId")
    account_id: str = Field(alias="accountId")
    role: Role
    joined_at: datetime = Field(alias="joinedAt")


class ActiveWorkspace(_Base):
    id: str
    name: str
    kind: WorkspaceKind
    role: Role


# ============================================================================
# Team/Workspace Rev 2 (docs/TEAM_WORKSPACE_ARCHITECTURE.md) — invites,
# switching, member listing. Backend foundation only — no screen consumes
# these yet.
# ============================================================================

InviteRole = Literal["admin", "editor", "reader"]


class WorkspacesListResponse(_Base):
    workspaces: list[ActiveWorkspace]


class WorkspaceMemberSummary(_Base):
    account_id: str = Field(alias="accountId")
    role: Role
    joined_at: datetime = Field(alias="joinedAt")


class CreateInviteRequest(_Base):
    email: str
    role: InviteRole


class WorkspaceInvite(_Base):
    id: str
    workspace_id: str = Field(alias="workspaceId")
    invited_email: str = Field(alias="invitedEmail")
    role: InviteRole
    invited_by: str = Field(alias="invitedBy")
    expires_at: datetime = Field(alias="expiresAt")
    accepted_at: datetime | None = Field(default=None, alias="acceptedAt")
    revoked_at: datetime | None = Field(default=None, alias="revokedAt")
    created_at: datetime = Field(alias="createdAt")


class AcceptInviteResult(_Base):
    workspace_id: str = Field(alias="workspaceId")
    role: InviteRole
    joined_at: datetime = Field(alias="joinedAt")


# ============================================================================
# Preferences
# ============================================================================

Focus = Literal["markets", "crypto", "both"]
ContentStyle = Literal["concise", "balanced", "detailed"]
VerificationStrictness = Literal["loose", "balanced", "strict"]
NotificationFrequency = Literal["off", "instant", "daily", "weekly"]
# Theming Phase A (2026-07-16): account-synced light/dark mode.
ThemeMode = Literal["dark", "light"]


class Preferences(_Base):
    account_id: str = Field(alias="accountId")
    focus: Focus
    content_style: ContentStyle = Field(alias="contentStyle")
    verification_strictness: VerificationStrictness = Field(alias="verificationStrictness")
    notification_frequency: NotificationFrequency = Field(alias="notificationFrequency")
    theme_mode: ThemeMode = Field(default="dark", alias="themeMode")
    custom_topics: list[str] = Field(default_factory=list, alias="customTopics")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")


class UpdatePreferencesRequest(_Base):
    focus: Focus | None = None
    content_style: ContentStyle | None = Field(default=None, alias="contentStyle")
    verification_strictness: VerificationStrictness | None = Field(
        default=None, alias="verificationStrictness"
    )
    notification_frequency: NotificationFrequency | None = Field(
        default=None, alias="notificationFrequency"
    )
    theme_mode: ThemeMode | None = Field(default=None, alias="themeMode")
    custom_topics: list[str] | None = Field(default=None, alias="customTopics")


# ============================================================================
# Sources
# ============================================================================


class SourceCatalogEntry(_Base):
    key: str
    name: str
    url: str
    focus: Focus
    editorial_confidence: int = Field(alias="editorialConfidence")


class WorkspaceSource(_Base):
    workspace_id: str = Field(alias="workspaceId")
    source_key: str = Field(alias="sourceKey")
    enabled: bool
    confidence_override: int | None = Field(default=None, alias="confidenceOverride")
    added_at: datetime = Field(alias="addedAt")


class WorkspaceCustomSource(_Base):
    id: str
    workspace_id: str = Field(alias="workspaceId")
    url: str
    status: Literal["pending_verification", "active", "rejected"]
    added_at: datetime = Field(alias="addedAt")


class UpdateWorkspaceSourceRequest(_Base):
    enabled: bool | None = None
    confidence_override: int | None = Field(default=None, alias="confidenceOverride")


# ============================================================================
# Sessions
# ============================================================================

DevicePlatform = Literal["ios", "android", "web"]


class Session(_Base):
    id: str
    device_label: str = Field(alias="deviceLabel")
    device_platform: DevicePlatform = Field(alias="devicePlatform")
    created_at: datetime = Field(alias="createdAt")
    last_used_at: datetime = Field(alias="lastUsedAt")
    expires_at: datetime = Field(alias="expiresAt")
    current: bool


# ============================================================================
# Auth
# ============================================================================


class SignupRequest(_Base):
    email: str
    password: str
    display_name: str = Field(alias="displayName")
    device_id: str = Field(alias="deviceId")
    device_label: str = Field(alias="deviceLabel")
    device_platform: DevicePlatform = Field(alias="devicePlatform")


class SigninRequest(_Base):
    email: str
    password: str
    device_id: str = Field(alias="deviceId")
    device_label: str = Field(alias="deviceLabel")
    device_platform: DevicePlatform = Field(alias="devicePlatform")


class RefreshRequest(_Base):
    refresh_token: str = Field(alias="refreshToken")
    device_id: str = Field(alias="deviceId")


class SwitchWorkspaceRequest(_Base):
    refresh_token: str = Field(alias="refreshToken")
    device_id: str = Field(alias="deviceId")
    workspace_id: str = Field(alias="workspaceId")


class ChangePasswordRequest(_Base):
    current_password: str = Field(alias="currentPassword")
    new_password: str = Field(alias="newPassword")


class ForgotPasswordRequest(_Base):
    email: str


class ResetPasswordRequest(_Base):
    token: str
    new_password: str = Field(alias="newPassword")


class TokenPair(_Base):
    access_token: str = Field(alias="accessToken")
    refresh_token: str = Field(alias="refreshToken")
    access_token_expires_at: datetime = Field(alias="accessTokenExpiresAt")
    refresh_token_expires_at: datetime = Field(alias="refreshTokenExpiresAt")
    session_id: str = Field(alias="sessionId")
    account_id: str = Field(alias="accountId")


class SignupResponse(_Base):
    tokens: TokenPair
    account: Account


class SigninResponse(_Base):
    tokens: TokenPair
    account: Account


class MfaSetupResponse(_Base):
    secret: str
    otpauth_url: str = Field(alias="otpauthUrl")


class MfaVerifyRequest(_Base):
    code: str


# ============================================================================
# Feature flags
# ============================================================================

FlagKey = Literal[
    "ff_settings", "ff_dashboard", "ff_activity", "ff_mfa", "ff_research",
    "ff_intake_gmail", "ff_intake_rss", "ff_intake_webhook",
    "ff_intake_api_pull", "ff_intake_manual", "ff_verification",
    "ff_content_drafts", "ff_publishing_notion", "ff_automation",
    "ff_push_delivery", "ff_email_delivery", "ff_analytics", "ff_training",
    "ff_team_workspaces",
]


class FeatureFlagOverride(_Base):
    flag_key: FlagKey = Field(alias="flagKey")
    scope: Literal["account", "workspace"]
    scope_id: str = Field(alias="scopeId")
    enabled: bool
    expires_at: datetime | None = Field(default=None, alias="expiresAt")


# ============================================================================
# Activity
# ============================================================================

ActivityType = Literal[
    "security", "system", "instant_alert", "daily_digest", "weekly_digest",
    "verification", "publishing",
]


class ActivityItem(_Base):
    id: str
    type: ActivityType
    title: str
    body: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    read_at: datetime | None = Field(default=None, alias="readAt")
    created_at: datetime = Field(alias="createdAt")


class ActivityInboxResponse(_Base):
    items: list[ActivityItem]
    unread_count: int = Field(alias="unreadCount")


# ============================================================================
# Alerts
# ============================================================================

Channel = Literal["in_app", "push", "email"]


class QuietHours(_Base):
    start: str
    end: str
    tz: str


class AlertPreference(_Base):
    type: ActivityType
    channel: Channel
    frequency: NotificationFrequency
    quiet_hours: QuietHours | None = Field(default=None, alias="quietHours")


class UpdateAlertPreferenceRequest(_Base):
    frequency: NotificationFrequency | None = None
    quiet_hours: QuietHours | None = Field(default=None, alias="quietHours")


class AlertDevice(_Base):
    id: str
    platform: DevicePlatform
    app_version: str | None = Field(default=None, alias="appVersion")
    last_seen_at: datetime = Field(alias="lastSeenAt")


class RegisterAlertDeviceRequest(_Base):
    platform: DevicePlatform
    push_token: str = Field(alias="pushToken")
    app_version: str | None = Field(default=None, alias="appVersion")


# ============================================================================
# Automation (Phase 6 Wave B) — mirrors shared-types/src/automation.ts
# ============================================================================

AutomationEntryKind = Literal["dispatch", "digest"]

AutomationAction = Literal[
    "notification_created",
    "suppressed_by_preference",
    "push_sent",
    "push_failed",
    "push_suppressed_quiet_hours",
    "email_sent",
    "email_failed",
    "email_suppressed_quiet_hours",
    "digest_sent",
]


class AutomationLogEntry(_Base):
    id: str
    kind: AutomationEntryKind
    action: AutomationAction
    event_type: str | None = Field(default=None, alias="eventType")
    category: str | None = None
    frequency: NotificationFrequency | None = None
    window_start: datetime | None = Field(default=None, alias="windowStart")
    window_end: datetime | None = Field(default=None, alias="windowEnd")
    activity_inbox_id: str | None = Field(default=None, alias="activityInboxId")
    # dispatch: which delivery channel this decision is about. digest: null.
    channel: Channel | None = None
    # dispatch: WHY a *_failed action failed (e.g. "no_registered_device",
    # a provider error string). Null for successes/suppressions, digests, and
    # rows recorded before reason capture (migration 0024).
    detail: str | None = None
    created_at: datetime = Field(alias="createdAt")


class AutomationLogResponse(_Base):
    entries: list[AutomationLogEntry]


# ============================================================================
# Analytics (Phase 7 Wave B) — mirrors shared-types/src/analytics.ts
# ============================================================================


class RollupPoint(_Base):
    """One day's value for one metric. `date` is the UTC day, YYYY-MM-DD."""

    date: str
    value: int


class AnalyticsRollupsResponse(_Base):
    """metric_key -> ascending daily points; sparse on both axes."""

    series: dict[str, list[RollupPoint]]
    from_: str = Field(alias="from")
    to: str


class PublishingSuccess(_Base):
    published: int
    failed: int
    success_rate: float | None = Field(default=None, alias="successRate")


class TimeToPublish(_Base):
    """Draft-creation -> publication gap; computed on request, not persisted."""

    average_seconds: float | None = Field(default=None, alias="averageSeconds")
    median_seconds: float | None = Field(default=None, alias="medianSeconds")
    sample_size: int = Field(alias="sampleSize")


class AnalyticsPublishingResponse(_Base):
    """§3.4: success rate + time-to-publish ONLY — no engagement field exists
    because no real engagement signal exists anywhere in the platform."""

    success: PublishingSuccess
    time_to_publish: TimeToPublish = Field(alias="timeToPublish")


# ============================================================================
# Onboarding
# ============================================================================

OnboardingStep = Literal[
    "welcome", "focus_sources", "notifications_permissions", "style_strictness",
]
OnboardingState = Literal["incomplete", "complete"]


class OnboardingStepRequest(_Base):
    step: OnboardingStep
    focus: Focus | None = None
    custom_topics: list[str] | None = Field(default=None, alias="customTopics")
    enabled_source_keys: list[str] | None = Field(default=None, alias="enabledSourceKeys")
    notification_frequency: NotificationFrequency | None = Field(
        default=None, alias="notificationFrequency"
    )
    push_permission_granted: bool | None = Field(
        default=None, alias="pushPermissionGranted"
    )
    content_style: ContentStyle | None = Field(default=None, alias="contentStyle")
    verification_strictness: VerificationStrictness | None = Field(
        default=None, alias="verificationStrictness"
    )


class OnboardingStepResponse(_Base):
    state: OnboardingState
    next_step: OnboardingStep | None = Field(default=None, alias="nextStep")


# ============================================================================
# Me (bootstrap envelope)
# ============================================================================


class _MeActivity(_Base):
    unread_count: int = Field(alias="unreadCount")


class _MeOnboarding(_Base):
    state: OnboardingState
    next_step: OnboardingStep | None = Field(default=None, alias="nextStep")


class _MeBuild(_Base):
    version: str
    commit: str


class _MeVerification(_Base):
    pending_review_count: int = Field(alias="pendingReviewCount")
    open_conflict_count: int = Field(alias="openConflictCount")
    # Command Center VERIFIED stat (2026-07-11): intelligence objects whose
    # verification_status is 'verified' OR 'analyst_approved'. Approval flips
    # an object AWAY from 'verified', so counting only 'verified' would make
    # the stat DROP when an analyst approves — both statuses mean verified.
    verified_count: int = Field(alias="verifiedCount")


class _MeResearch(_Base):
    active_workspace_count: int = Field(alias="activeWorkspaceCount")
    ready_packet_count: int = Field(alias="readyPacketCount")


class _MeContent(_Base):
    draft_count: int = Field(alias="draftCount")
    pending_review_count: int = Field(alias="pendingReviewCount")
    scheduled_count: int = Field(alias="scheduledCount")
    published_this_week: int = Field(alias="publishedThisWeek")


class MeResponse(_Base):
    account: Account
    profile: Profile
    workspace: ActiveWorkspace
    preferences: Preferences
    activity: _MeActivity
    flags: dict[str, bool]
    onboarding: _MeOnboarding
    verification: _MeVerification
    research: _MeResearch
    content: _MeContent
    server_time: datetime = Field(alias="serverTime")
    build: _MeBuild


# ============================================================================
# Phase 3 — Intake (Batch 1)
# ============================================================================

IntakeSourceKind = Literal["gmail", "rss", "webhook", "api_pull", "manual"]
SourceHealth = Literal["healthy", "degraded", "auth_required", "disabled"]
OriginKind = Literal["catalog", "custom"]
IntakeProviderName = Literal["gmail", "rss", "webhook", "api_pull", "manual"]


class IntakeSource(_Base):
    id: str
    workspace_id: str = Field(alias="workspaceId")
    kind: IntakeSourceKind
    name: str
    enabled: bool
    config: dict[str, Any] = Field(default_factory=dict)
    health: SourceHealth
    last_synced_at: datetime | None = Field(default=None, alias="lastSyncedAt")
    consecutive_failures: int = Field(default=0, alias="consecutiveFailures")
    origin_kind: OriginKind = Field(alias="originKind")
    origin_catalog_key: str | None = Field(default=None, alias="originCatalogKey")
    origin_custom_id: str | None = Field(default=None, alias="originCustomId")


class IntakeSourceAuditEntry(_Base):
    id: str
    intake_source_id: str = Field(alias="intakeSourceId")
    event: str
    data: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(alias="createdAt")


class IntakeStatusSummary(_Base):
    total: int
    by_health: dict[str, int] = Field(alias="byHealth")


class RecentIntakeItem(_Base):
    """One row of the Command Center "Today" feed — the real ingested content
    (headline + source), not the generic activity_inbox notification row."""

    id: str
    subject: str | None = None
    source_name: str = Field(alias="sourceName")
    provider_name: str = Field(alias="providerName")
    received_at: datetime = Field(alias="receivedAt")


class IntakeItemLink(_Base):
    """One extracted link on a normalized item (intake_items_normalized.links)."""

    url: str
    anchor: str = ""


class IntakeItemDetail(_Base):
    """GET /intake/items/{id} — one ingested item with its real content.

    What an Activity "New item ingested" row and a search result open onto.
    The normalized fields are None/empty when the normalizer hasn't reached
    the item yet (same outer-join contract as /items/recent)."""

    id: str
    subject: str | None = None
    body_text: str | None = Field(default=None, alias="bodyText")
    sender_label: str | None = Field(default=None, alias="senderLabel")
    sender_domain: str | None = Field(default=None, alias="senderDomain")
    links: list[IntakeItemLink] = Field(default_factory=list)
    source_name: str = Field(alias="sourceName")
    provider_name: str = Field(alias="providerName")
    received_at: datetime = Field(alias="receivedAt")


class IntakeItem(_Base):
    id: str
    workspace_id: str = Field(alias="workspaceId")
    intake_source_id: str = Field(alias="intakeSourceId")
    provider_name: str = Field(alias="providerName")
    external_id: str = Field(alias="externalId")
    received_at: datetime = Field(alias="receivedAt")
    fingerprint: str


class NormalizedItemView(_Base):
    intake_item_id: str = Field(alias="intakeItemId")
    sender_domain: str | None = Field(default=None, alias="senderDomain")
    sender_label: str | None = Field(default=None, alias="senderLabel")
    subject: str | None = None
    link_count: int = Field(alias="linkCount")
    normalized_at: datetime = Field(alias="normalizedAt")
    normalizer_version: int = Field(alias="normalizerVersion")


class IntakeItemReceived(_Base):
    """Domain event payload emitted via the outbox after successful ingest."""

    intake_item_id: str = Field(alias="intakeItemId")
    workspace_id: str = Field(alias="workspaceId")
    intake_source_id: str = Field(alias="intakeSourceId")
    provider_name: IntakeProviderName = Field(alias="providerName")
    received_at: datetime = Field(alias="receivedAt")
    fingerprint: str
    external_id: str = Field(alias="externalId")


class ManualIngestRequest(_Base):
    """CR-8 — body for POST /admin/intake/manual_ingest (snake_case body
    convention of the intake routers)."""

    workspace_id: str
    title: str
    url: str | None = None
    body_text: str | None = None
    sender: str | None = None


class ManualIngestResponse(_Base):
    outcome: Literal["inserted", "skipped_provider_key", "skipped_fingerprint"]
    intake_item_id: str | None = Field(default=None, alias="intakeItemId")
    fingerprint: str


# ============================================================================
# Claims (Phase 4 Wave A)
# ============================================================================

EpistemicType = Literal[
    "fact", "claim", "rumor", "speculation", "opinion", "unclassified"
]


class Claim(_Base):
    id: str
    workspace_id: str = Field(alias="workspaceId")
    intake_item_id: str = Field(alias="intakeItemId")
    text: str
    subject: str
    predicate: str
    object: str | None = None
    epistemic_type: EpistemicType = Field(alias="epistemicType")
    extractor_version: int = Field(alias="extractorVersion")
    classifier_version: int | None = Field(default=None, alias="classifierVersion")
    requires_analyst_review: bool = Field(alias="requiresAnalystReview")
    superseded_by: str | None = Field(default=None, alias="supersededBy")
    created_at: datetime = Field(alias="createdAt")


class _ClaimListMeta(_Base):
    pagination: Pagination


class ClaimListResponse(_Base):
    claims: list[Claim]
    meta: _ClaimListMeta


# ============================================================================
# Evidence (Phase 4 Wave B)
# ============================================================================

EvidenceType = Literal[
    "corroboration", "contradiction", "context",
    "primary_source", "secondary_source", "inference",
]

EvidenceRelationship = Literal["supports", "contradicts", "contextualizes"]


class Evidence(_Base):
    id: str
    workspace_id: str = Field(alias="workspaceId")
    intake_item_id: str = Field(alias="intakeItemId")
    evidence_type: EvidenceType = Field(alias="evidenceType")
    text: str
    source_deleted: bool = Field(default=False, alias="sourceDeleted")
    created_at: datetime = Field(alias="createdAt")


class ClaimEvidenceLink(_Base):
    claim_id: str = Field(alias="claimId")
    evidence_id: str = Field(alias="evidenceId")
    relationship: EvidenceRelationship
    strength: float
    linker_version: int = Field(alias="linkerVersion")


class EvidenceWithLink(Evidence):
    link: ClaimEvidenceLink


class WebhookEnvelope(_Base):
    workspace_id: str = Field(alias="workspaceId")
    intake_source_id: str = Field(alias="intakeSourceId")
    signature: str
    timestamp: int
    idempotency_key: str = Field(alias="idempotencyKey")
    body: Any


# ============================================================================
# Verification (Phase 4 Wave C)
# ============================================================================

VerificationOutcome = Literal["verified", "unverified", "contested", "unverifiable"]
VerificationStatus = Literal["pending", "running", "complete", "failed"]


class ScoringFactors(_Base):
    source_trust_score: float | None = Field(default=None, alias="sourceTrustScore")
    cross_reference_count_score: float | None = Field(
        default=None, alias="crossReferenceCountScore"
    )
    evidence_strength_score: float | None = Field(
        default=None, alias="evidenceStrengthScore"
    )
    recency_score: float | None = Field(default=None, alias="recencyScore")
    claim_specificity_score: float | None = Field(
        default=None, alias="claimSpecificityScore"
    )
    primary_source_available: float | None = Field(
        default=None, alias="primarySourceAvailable"
    )


class VerificationRun(_Base):
    id: str
    claim_id: str = Field(alias="claimId")
    status: VerificationStatus
    outcome: VerificationOutcome | None = None
    confidence_score: float | None = Field(default=None, alias="confidenceScore")
    cross_reference_count: int | None = Field(
        default=None, alias="crossReferenceCount"
    )
    primary_source_flag: bool | None = Field(default=None, alias="primarySourceFlag")
    factors: ScoringFactors
    engine_version: int = Field(alias="engineVersion")
    scoring_version: int = Field(alias="scoringVersion")
    tokens_used: int = Field(alias="tokensUsed")
    started_at: datetime = Field(alias="startedAt")
    completed_at: datetime | None = Field(default=None, alias="completedAt")


class SourceCredibility(_Base):
    workspace_id: str = Field(alias="workspaceId")
    source_id: str = Field(alias="sourceId")
    accuracy_rate: float = Field(alias="accuracyRate")
    verified_claim_count: int = Field(alias="verifiedClaimCount")
    contested_claim_count: int = Field(alias="contestedClaimCount")
    total_claim_count: int = Field(alias="totalClaimCount")
    last_evaluated_at: datetime | None = Field(default=None, alias="lastEvaluatedAt")
    updated_at: datetime = Field(alias="updatedAt")


# ============================================================================
# Scoring contract (Phase 4 Wave C) — shared constants, not response models
# ============================================================================

CURRENT_SCORING_VERSION = 1

EPISTEMIC_CEILINGS: dict[str, float | None] = {
    "fact": 1.0,
    "claim": 0.85,
    "speculation": 0.6,
    "rumor": 0.4,
    "opinion": 0.3,
    "unclassified": None,
}

ConfidenceBand = Literal["high", "moderate", "low", "minimal", "unscored"]

CONFIDENCE_BAND_THRESHOLDS: list[tuple[str, float]] = [
    ("high", 0.75),
    ("moderate", 0.5),
    ("low", 0.25),
    ("minimal", 0.0),
]


# ============================================================================
# Conflicts (Phase 4 Wave D)
# ============================================================================

ConflictType = Literal[
    "direct_contradiction",
    "factual_disagreement",
    "temporal_inconsistency",
    "scope_difference",
]
ConflictStatus = Literal[
    "open",
    "resolved_a_wins",
    "resolved_b_wins",
    "resolved_inconclusive",
    "resolved_system",
    "analyst_reviewed",
]
ConflictResolver = Literal["system", "analyst"]
AnalystEntityType = Literal["claim", "intelligence_object", "conflict"]


class ConflictRecord(_Base):
    id: str
    workspace_id: str = Field(alias="workspaceId")
    claim_a_id: str = Field(alias="claimAId")
    claim_b_id: str = Field(alias="claimBId")
    conflict_type: ConflictType = Field(alias="conflictType")
    severity: float
    status: ConflictStatus
    resolution_note: str | None = Field(default=None, alias="resolutionNote")
    resolved_by_kind: ConflictResolver | None = Field(
        default=None, alias="resolvedByKind"
    )
    resolved_at: datetime | None = Field(default=None, alias="resolvedAt")
    created_at: datetime = Field(alias="createdAt")


class AnalystReview(_Base):
    id: str
    account_id: str = Field(alias="accountId")
    workspace_id: str = Field(alias="workspaceId")
    entity_type: AnalystEntityType = Field(alias="entityType")
    entity_id: str = Field(alias="entityId")
    outcome: str
    note: str
    created_at: datetime = Field(alias="createdAt")


class ConflictDetail(ConflictRecord):
    claim_a: Claim = Field(alias="claimA")
    claim_b: Claim = Field(alias="claimB")
    claim_a_score: float | None = Field(default=None, alias="claimAScore")
    claim_b_score: float | None = Field(default=None, alias="claimBScore")
    claim_a_evidence_counts: dict[str, int] = Field(alias="claimAEvidenceCounts")
    claim_b_evidence_counts: dict[str, int] = Field(alias="claimBEvidenceCounts")


class ReviewQueue(_Base):
    pending_claims: list[Claim] = Field(alias="pendingClaims")
    open_conflicts: list[ConflictRecord] = Field(alias="openConflicts")


class ResolveConflictRequest(_Base):
    outcome: Literal["a_wins", "b_wins", "inconclusive"]
    note: str


# ============================================================================
# Intelligence objects (Phase 4 Wave E)
# ============================================================================

IntelligenceStatus = Literal[
    "unverified", "verified", "contested", "analyst_approved", "analyst_rejected"
]


class IntelligenceObject(_Base):
    id: str
    workspace_id: str = Field(alias="workspaceId")
    intake_item_id: str = Field(alias="intakeItemId")
    epistemic_type: EpistemicType = Field(alias="epistemicType")
    confidence_score: float | None = Field(default=None, alias="confidenceScore")
    verification_status: IntelligenceStatus = Field(alias="verificationStatus")
    claim_ids: list[str] = Field(alias="claimIds")
    conflict_ids: list[str] = Field(alias="conflictIds")
    key_facts: dict[str, Any] = Field(alias="keyFacts")
    headline: str
    scoring_version: int = Field(alias="scoringVersion")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")


class StaleCheck(_Base):
    is_stale: bool = Field(alias="isStale")
    current_version: int = Field(alias="currentVersion")
    object_version: int = Field(alias="objectVersion")


# ============================================================================
# Research workspaces + packets (Phase 4 Wave E)
# ============================================================================

ResearchPacketStatus = Literal["assembling", "ready", "consumed"]


class ResearchWorkspace(_Base):
    id: str
    account_id: str = Field(alias="accountId")
    workspace_id: str = Field(alias="workspaceId")
    name: str
    description: str | None = None
    status: Literal["active", "archived"]
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")


class ResearchWorkspaceItem(_Base):
    research_workspace_id: str = Field(alias="researchWorkspaceId")
    intelligence_object_id: str = Field(alias="intelligenceObjectId")
    added_by: str = Field(alias="addedBy")
    note: str | None = None
    added_at: datetime = Field(alias="addedAt")


class ResearchPacket(_Base):
    id: str
    research_workspace_id: str = Field(alias="researchWorkspaceId")
    workspace_id: str = Field(alias="workspaceId")
    name: str
    status: ResearchPacketStatus
    intelligence_object_ids: list[str] = Field(alias="intelligenceObjectIds")
    conflict_acknowledged_ids: list[str] = Field(alias="conflictAcknowledgedIds")
    ready_at: datetime | None = Field(default=None, alias="readyAt")
    consumed_at: datetime | None = Field(default=None, alias="consumedAt")
    created_at: datetime = Field(alias="createdAt")


class ReadinessResult(_Base):
    is_ready: bool = Field(alias="isReady")
    blockers: list[str]


# ============================================================================
# Phase 5 Wave A — content drafts
# ============================================================================

ContentFormat = Literal[
    "tweet_thread",
    "linkedin_post",
    "newsletter_section",
    "article",
    "report_summary",
    "custom",
]
DraftStatus = Literal[
    "draft",
    "in_review",
    "changes_requested",
    "approved",
    "scheduled",
    "published",
    "rejected",
    "archived",
]


class ContentDraft(_Base):
    id: str
    workspace_id: str = Field(alias="workspaceId")
    account_id: str = Field(alias="accountId")
    packet_id: str = Field(alias="packetId")
    template_id: str | None = Field(default=None, alias="templateId")
    format: ContentFormat
    title: str
    status: DraftStatus
    current_version: int = Field(alias="currentVersion")
    generation_model: str = Field(alias="generationModel")
    word_count: int | None = Field(default=None, alias="wordCount")
    published_at: datetime | None = Field(default=None, alias="publishedAt")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")


class ContentDraftDetail(ContentDraft):
    current_content: str | None = Field(default=None, alias="currentContent")
    current_content_html: str | None = Field(default=None, alias="currentContentHtml")
    citation_object_ids: list[str] = Field(alias="citationObjectIds")


class DraftVersion(_Base):
    id: str
    draft_id: str = Field(alias="draftId")
    version_number: int = Field(alias="versionNumber")
    content: str
    content_html: str | None = Field(default=None, alias="contentHtml")
    edited_by: str = Field(alias="editedBy")
    edit_note: str | None = Field(default=None, alias="editNote")
    word_count: int | None = Field(default=None, alias="wordCount")
    token_count: int | None = Field(default=None, alias="tokenCount")
    is_ai_generated: bool = Field(alias="isAiGenerated")
    created_at: datetime = Field(alias="createdAt")


class DraftCitation(_Base):
    draft_id: str = Field(alias="draftId")
    intelligence_object_id: str = Field(alias="intelligenceObjectId")
    added_at: datetime = Field(alias="addedAt")


class ContentCounts(_Base):
    draft_count: int = Field(alias="draftCount")
    pending_review_count: int = Field(alias="pendingReviewCount")
    scheduled_count: int = Field(alias="scheduledCount")
    published_this_week: int = Field(alias="publishedThisWeek")


class GenerateRequest(_Base):
    packet_id: str = Field(alias="packetId")
    format: ContentFormat
    template_id: str | None = Field(default=None, alias="templateId")
    instructions: str | None = Field(default=None)


class SwitchFormatRequest(_Base):
    format: ContentFormat
    template_id: str | None = Field(default=None, alias="templateId")


# ============================================================================
# Phase 5 Wave B — content templates
# ============================================================================

ContentTone = Literal[
    "formal",
    "analytical",
    "conversational",
    "authoritative",
    "concise",
]


class ContentTemplate(_Base):
    id: str
    workspace_id: str = Field(alias="workspaceId")
    name: str
    format: ContentFormat
    tone: ContentTone
    max_words: int | None = Field(default=None, alias="maxWords")
    min_words: int | None = Field(default=None, alias="minWords")
    structure_hint: str | None = Field(default=None, alias="structureHint")
    is_default: bool = Field(alias="isDefault")


class CreateTemplateRequest(_Base):
    name: str
    format: ContentFormat
    tone: ContentTone = "analytical"
    max_words: int | None = Field(default=None, alias="maxWords")
    min_words: int | None = Field(default=None, alias="minWords")
    structure_hint: str | None = Field(default=None, alias="structureHint")


class UpdateTemplateRequest(_Base):
    name: str | None = None
    tone: ContentTone | None = None
    max_words: int | None = Field(default=None, alias="maxWords")
    min_words: int | None = Field(default=None, alias="minWords")
    structure_hint: str | None = Field(default=None, alias="structureHint")


# ============================================================================
# Phase 5 Wave C — review workflow
# ============================================================================

ReviewOutcome = Literal["approved", "rejected", "changes_requested"]


class DraftReview(_Base):
    id: str
    draft_id: str = Field(alias="draftId")
    version_number: int = Field(alias="versionNumber")
    account_id: str = Field(alias="accountId")
    outcome: ReviewOutcome
    note: str | None = None
    created_at: datetime = Field(alias="createdAt")


class ApproveDraftRequest(_Base):
    note: str | None = None


class RejectDraftRequest(_Base):
    note: str


class RequestChangesRequest(_Base):
    note: str


# ============================================================================
# Phase 5 Wave D — publish targets + publications
# ============================================================================

PublishChannel = Literal[
    "twitter_x",
    "linkedin",
    "email_newsletter",
    "notion",
    "webhook",
    "export",
]

PublicationStatus = Literal[
    "pending",
    "delivering",
    "delivered",
    "failed",
    "cancelled",
]


class PublishTarget(_Base):
    # No credentials field — write-only, never serialized (§13.2).
    id: str
    workspace_id: str = Field(alias="workspaceId")
    name: str
    channel: PublishChannel
    config: dict[str, object]
    is_active: bool = Field(alias="isActive")
    last_health_at: str | None = Field(default=None, alias="lastHealthAt")
    last_health_ok: bool | None = Field(default=None, alias="lastHealthOk")
    created_at: str = Field(alias="createdAt")


class Publication(_Base):
    id: str
    draft_id: str = Field(alias="draftId")
    version_number: int = Field(alias="versionNumber")
    target_id: str = Field(alias="targetId")
    workspace_id: str = Field(alias="workspaceId")
    status: PublicationStatus
    external_id: str | None = Field(default=None, alias="externalId")
    external_url: str | None = Field(default=None, alias="externalUrl")
    error_message: str | None = Field(default=None, alias="errorMessage")
    published_at: str | None = Field(default=None, alias="publishedAt")
    created_at: str = Field(alias="createdAt")


class PublishRequest(_Base):
    target_ids: list[str] = Field(alias="targetIds")


class PublishTargetResult(_Base):
    target_id: str = Field(alias="targetId")
    publication_id: str | None = Field(default=None, alias="publicationId")
    status: Literal["delivered", "failed", "pending", "skipped"]
    external_id: str | None = Field(default=None, alias="externalId")
    external_url: str | None = Field(default=None, alias="externalUrl")
    error_message: str | None = Field(default=None, alias="errorMessage")


class PublicationCitationSnapshot(_Base):
    # Snapshotted at publication-row creation, never live-read afterwards.
    # Intelligence-object level ONLY — no claim/evidence fields at any depth.
    intelligence_object_id: str = Field(alias="intelligenceObjectId")
    headline: str
    epistemic_type: EpistemicType = Field(alias="epistemicType")
    confidence_tier: ConfidenceBand = Field(alias="confidenceTier")
    confidence_score: float | None = Field(default=None, alias="confidenceScore")
    scoring_version: int = Field(alias="scoringVersion")
    snapshotted_at: str = Field(alias="snapshottedAt")


class PublicationProvenance(_Base):
    publication_id: str = Field(alias="publicationId")
    entries: list[PublicationCitationSnapshot]


# ============================================================================
# Phase 5 Wave E — content calendar + scheduling
# ============================================================================

CalendarStatus = Literal[
    "scheduled",
    "published",
    "cancelled",
    "failed",
]


class CalendarEntry(_Base):
    id: str
    workspace_id: str = Field(alias="workspaceId")
    draft_id: str = Field(alias="draftId")
    target_id: str = Field(alias="targetId")
    scheduled_at: str = Field(alias="scheduledAt")
    status: CalendarStatus
    publication_id: str | None = Field(default=None, alias="publicationId")
    created_by: str = Field(alias="createdBy")
    created_at: str = Field(alias="createdAt")


class ScheduleDraftRequest(_Base):
    draft_id: str = Field(alias="draftId")
    target_id: str = Field(alias="targetId")
    scheduled_at: str = Field(alias="scheduledAt")


# ============================================================================
# Billing — first frontend-facing surface over the billing foundation
# ============================================================================

BillingCadence = Literal["monthly", "quarterly", "yearly"]
BillingCurrency = Literal["USD", "INR"]
PaymentProviderName = Literal["stripe", "razorpay"]
SubscriptionStatus = Literal["pending", "active", "past_due", "canceled"]


class PlanPrice(_Base):
    plan_id: str = Field(alias="planId")
    tier: WorkspacePlan
    cadence: BillingCadence
    currency: BillingCurrency
    amount: float


class PlansResponse(_Base):
    plans: list[PlanPrice]


class ActiveSubscription(_Base):
    provider: PaymentProviderName
    plan: WorkspacePlan | None
    status: SubscriptionStatus
    currency: BillingCurrency


class SubscriptionSummary(_Base):
    current_plan: WorkspacePlan = Field(alias="currentPlan")
    subscription: ActiveSubscription | None


class SubscribeRequest(_Base):
    plan_id: str = Field(alias="planId")
    currency: BillingCurrency


class SubscribeResult(_Base):
    provider_subscription_id: str = Field(alias="providerSubscriptionId")
    status: SubscriptionStatus
