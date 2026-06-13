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
WorkspacePlan = Literal["free", "pro", "enterprise"]
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
# Preferences
# ============================================================================

Focus = Literal["markets", "crypto", "both"]
ContentStyle = Literal["concise", "balanced", "detailed"]
VerificationStrictness = Literal["loose", "balanced", "strict"]
NotificationFrequency = Literal["off", "instant", "daily", "weekly"]


class Preferences(_Base):
    account_id: str = Field(alias="accountId")
    focus: Focus
    content_style: ContentStyle = Field(alias="contentStyle")
    verification_strictness: VerificationStrictness = Field(alias="verificationStrictness")
    notification_frequency: NotificationFrequency = Field(alias="notificationFrequency")
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


class MeResponse(_Base):
    account: Account
    profile: Profile
    workspace: ActiveWorkspace
    preferences: Preferences
    activity: _MeActivity
    flags: dict[str, bool]
    onboarding: _MeOnboarding
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
