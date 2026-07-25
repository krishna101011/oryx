import React from 'react';
import type { ViewStyle } from 'react-native';
import { Card } from './Card';
import { Skeleton } from './Skeleton';
import { Spacer } from './Spacer';

export interface SkeletonTileProps {
  /**
   * An extra descriptive line under the value bar — Analytics Publishing's
   * "delivered · failed" / "median · average · sample" caption. Omit (the
   * default) for the plain 2-line label+value tile (Command Center,
   * Automation Hub's KPI rows).
   */
  detailWidth?: `${number}%` | false;
  /**
   * Reserves a "last 7 days" caption line plus a full-width bar matching
   * Spark's real height (28px) — Analytics Overview's KPI tiles, the one
   * shape in the family with a trend + sparkline row.
   */
  hasSparkline?: boolean;
  style?: ViewStyle;
}

/**
 * Shaped loading placeholder for the plain KPI tile — label + big value,
 * shared by Command Center, Automation Hub, and (via `hasSparkline`/
 * `detailWidth`) Analytics' richer variant. Bar heights are derived from the
 * real Text variants each tile uses: `label` (9.5px) for the caption,
 * `kpiVal` (22px) for the value, `caption`/`bodySm` for the optional detail
 * line — packages/design-system/src/tokens/typography.ts.
 */
export const SkeletonTile: React.FC<SkeletonTileProps> = ({
  detailWidth = false,
  hasSparkline = false,
  style,
}) => (
  <Card style={style}>
    <Skeleton width="50%" height={8} radius={2} />
    <Spacer size={1} />
    <Skeleton width="65%" height={18} radius={2} />
    {detailWidth ? (
      <>
        <Spacer size={1} />
        <Skeleton width={detailWidth} height={9} radius={2} />
      </>
    ) : null}
    {hasSparkline ? (
      <>
        <Spacer size={1} />
        <Skeleton width="40%" height={8} radius={2} />
        <Spacer size={2} />
        {/* Spark fullWidth height={28} — AnalyticsHomeScreen.tsx OverviewTab */}
        <Skeleton width="100%" height={28} radius={4} />
      </>
    ) : null}
  </Card>
);
