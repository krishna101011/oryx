import React from 'react';
import { StyleSheet, View } from 'react-native';
import { Skeleton } from './Skeleton';
import { Spacer } from './Spacer';

export interface SkeletonRowProps {
  /**
   * Width of the leading mono/chip bar — a row's mono-id (WorkspaceCard),
   * fixed date column (DraftCard), category chip (Automation Rules row), or
   * timestamp column (Automation Log row). Omit to start straight into the
   * title bar.
   */
  leadingWidth?: number;
  /**
   * Render the leading bar as two stacked lines instead of one — Automation
   * Hub's Log row mono time + caption date column.
   */
  stackedLeading?: boolean;
  /**
   * 'head' (default): the leading bar sits on its own line ABOVE the title,
   * with the trailing element reserved as a chevron-width gap on the row's
   * right edge — WorkspaceCard / DraftCard / Command Center's Today row.
   * 'flank': the leading bar sits BESIDE the title/meta block as a row-level
   * sibling, with any trailing chip on the opposite side — Automation Hub's
   * Rules and Log rows.
   */
  leadingPlacement?: 'head' | 'flank';
  /**
   * A second, smaller chip-shaped bar: in 'head' mode it sits on the head
   * line next to the leading bar (WorkspaceCard's status chip); in 'flank'
   * mode it's a trailing sibling on the row's right edge (Rules' cadence
   * chip, Log's outcome chip).
   */
  hasTrailingChip?: boolean;
  /**
   * Reserves the chevron-width gap on the row's right edge (Icon size="sm"
   * footprint, 16px). Only meaningful in 'head' mode — flank rows don't
   * navigate via a trailing chevron. Default true.
   */
  hasChevron?: boolean;
  /** Title bar width. Default '70%'. */
  titleWidth?: `${number}%`;
  /** Meta/description bar width, or false to omit that line entirely. Default '45%'. */
  metaWidth?: `${number}%` | false;
}

/**
 * Shaped loading placeholder for the row anatomy shared by WorkspaceCard,
 * DraftCard, Command Center's Today row, and (via 'flank') Automation Hub's
 * Rules/Log rows — see the loading-skeleton recon's real card-shape catalog.
 * Composed entirely from the existing `Skeleton` primitive; bar heights are
 * derived from the real Text variants each row uses (caption lineHeight 14,
 * mono lineHeight 16, body lineHeight 18 — packages/design-system/src/
 * tokens/typography.ts), not arbitrary numbers.
 *
 * Callers render N of these inside the SAME real `HairlineRowList` /
 * `Card` wrapper the real rows use, so dividers and padding match exactly —
 * this component only ever renders one row's content.
 */
export const SkeletonRow: React.FC<SkeletonRowProps> = ({
  leadingWidth,
  stackedLeading = false,
  leadingPlacement = 'head',
  hasTrailingChip = false,
  hasChevron = true,
  titleWidth = '70%',
  metaWidth = '45%',
}) => {
  const leading = leadingWidth ? (
    stackedLeading ? (
      <View style={{ width: leadingWidth }}>
        <Skeleton width={leadingWidth} height={10} radius={2} />
        <Spacer size={1} />
        <Skeleton width={Math.round(leadingWidth * 0.6)} height={8} radius={2} />
      </View>
    ) : (
      <Skeleton width={leadingWidth} height={10} radius={2} />
    )
  ) : null;

  const chip = hasTrailingChip ? <Skeleton width={40} height={14} radius={3} /> : null;

  const textBlock = (
    <View style={{ flex: 1 }}>
      {leadingPlacement === 'head' && (leading || chip) ? (
        <>
          <View style={styles.headLine}>
            {leading}
            {chip}
          </View>
          <Spacer size={1} />
        </>
      ) : null}
      <Skeleton width={titleWidth} height={11} radius={2} />
      {metaWidth ? (
        <>
          <Spacer size={1} />
          <Skeleton width={metaWidth} height={9} radius={2} />
        </>
      ) : null}
    </View>
  );

  if (leadingPlacement === 'flank') {
    return (
      <View style={styles.row}>
        {leading}
        {textBlock}
        {chip}
      </View>
    );
  }

  return (
    <View style={styles.row}>
      {textBlock}
      {hasChevron ? <View style={styles.chevronGap} /> : null}
    </View>
  );
};

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'flex-start', columnGap: 10 },
  headLine: { flexDirection: 'row', alignItems: 'center', columnGap: 8 },
  // Icon size="sm" footprint (16px) + its real 8px marginLeft (WorkspaceCard/
  // DraftCard's .chevron style) — reserves the exact space the real chevron
  // icon occupies so content doesn't shift when the skeleton resolves.
  chevronGap: { width: 16, height: 14, marginLeft: 8 },
});
