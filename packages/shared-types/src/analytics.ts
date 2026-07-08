/**
 * Analytics domain types — Phase 7 Wave B.
 *
 * The dashboard reads exactly two contracts (docs/PHASE_7_ARCHITECTURE.md §6
 * Wave B): GET /v1/analytics/rollups — daily series straight out of
 * analytics_rollups_daily, workspace-scoped, sparse (zero-activity days have
 * no point and absent metrics have no key) — and GET /v1/analytics/publishing,
 * the delivery-performance view. The publishing shape is DELIBERATELY limited
 * to success rate + time-to-publish (§3.4): no engagement/view field exists
 * because no real engagement signal exists anywhere in the platform.
 */

/** One day's value for one metric. `date` is the UTC day, YYYY-MM-DD. */
export interface RollupPoint {
  date: string;
  value: number;
}

/**
 * metric_key (§3.3 vocabulary, e.g. 'claims_verified') → daily points,
 * ascending by date. Sparse on both axes: metrics with no rows in range are
 * absent, and days with no activity are skipped — clients pad zeros.
 */
export interface AnalyticsRollupsResponse {
  series: Record<string, RollupPoint[]>;
  /** Inclusive UTC day bounds actually used (defaults applied server-side). */
  from: string;
  to: string;
}

/** drafts_published vs publish_failures over the window, from the rollups. */
export interface PublishingSuccess {
  published: number;
  failed: number;
  /** published / (published + failed); null when there were no attempts. */
  successRate: number | null;
}

/**
 * Draft-creation → publication gap over recently delivered publications —
 * computed on request from content_drafts/publications, never persisted.
 */
export interface TimeToPublish {
  averageSeconds: number | null;
  medianSeconds: number | null;
  /** How many delivered publications the stats were computed over. */
  sampleSize: number;
}

export interface AnalyticsPublishingResponse {
  success: PublishingSuccess;
  timeToPublish: TimeToPublish;
}
