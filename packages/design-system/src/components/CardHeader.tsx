import React from 'react';
import { StyleSheet, View } from 'react-native';
import { useTheme } from '../theme/ThemeProvider';
import { Text } from './Text';

export interface CardHeaderProps {
  title: string;
  /** Mono meta after the title (the reference .card-head .sub, e.g. "6 SOURCES"). */
  sub?: string;
  /** Right-aligned meta: chips, counts, a ghost action. */
  right?: React.ReactNode;
  testID?: string;
}

/**
 * The reference card-header strip — .card-head (styles.css:310-318): uppercase
 * 11.5/600 title (cardTitle variant, --text-2) + mono sub (--text-4; rendered
 * tertiary, the darkest themed text color) + right-aligned meta, over a full-
 * width bottom border. Padding ports the source values verbatim (9px 12px),
 * following the gx precedent for exact Genspark dimensions.
 *
 * Pass it through Card's `header` slot so the border runs edge-to-edge:
 *   <Card header={<CardHeader title="Claim queue" sub="9 ACTIVE" />}>…</Card>
 */
export const CardHeader: React.FC<CardHeaderProps> = ({
  title,
  sub,
  right,
  testID,
}) => {
  const t = useTheme();
  return (
    <View
      style={[styles.root, { borderBottomColor: t.colors.border.default }]}
      testID={testID}
    >
      <Text variant="cardTitle" color="secondary">
        {title}
      </Text>
      {sub ? (
        <Text variant="caption" color="tertiary">
          {sub}
        </Text>
      ) : null}
      {right ? <View style={styles.right}>{right}</View> : null}
    </View>
  );
};

const styles = StyleSheet.create({
  // .card-head { padding: 9px 12px; border-bottom: 1px --border; gap: 8 }
  root: {
    flexDirection: 'row',
    alignItems: 'center',
    columnGap: 8,
    paddingVertical: 9,
    paddingHorizontal: 12,
    borderBottomWidth: 1,
  },
  // .card-head .right { margin-left: auto; gap: 6 }
  right: {
    marginLeft: 'auto',
    flexDirection: 'row',
    alignItems: 'center',
    columnGap: 6,
  },
});
