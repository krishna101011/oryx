/**
 * Feature flag catalog and resolution shape.
 * Adding a new flag here also requires a row in the feature_flags table
 * via a migration. Keep this list in sync with §7.1 of the architecture.
 */
export type FlagKey =
  | 'ff_settings'
  | 'ff_dashboard'
  | 'ff_activity'
  | 'ff_mfa'
  | 'ff_research'
  | 'ff_intake_gmail'
  | 'ff_intake_rss'
  | 'ff_intake_webhook'
  | 'ff_intake_api_pull'
  | 'ff_intake_manual'
  | 'ff_verification'
  | 'ff_content_drafts'
  | 'ff_publishing_notion'
  | 'ff_automation'
  | 'ff_push_delivery'
  | 'ff_email_delivery'
  | 'ff_analytics'
  | 'ff_training'
  | 'ff_team_workspaces';

/** Resolved flag map for a single principal (account + active workspace). */
export type FlagSet = Record<FlagKey, boolean>;

export interface FeatureFlagOverride {
  flagKey: FlagKey;
  scope: 'account' | 'workspace';
  scopeId: string;
  enabled: boolean;
  expiresAt: string | null;
}
