import React from 'react';
import { View, type ViewStyle } from 'react-native';
import { useTheme } from '../theme/ThemeProvider';

export interface HairlineRowListProps {
  children: React.ReactNode;
  /**
   * Vertical padding per row. The reference runs 6–10px depending on row
   * weight (alerts 6, workflow/opportunities 8, packets 10); default 8.
   */
  rowVerticalPadding?: number;
  style?: ViewStyle;
  testID?: string;
}

/**
 * The reference in-card list pattern (command-center.jsx:78, :95, :174;
 * verification.jsx:126): each child renders as a compact row separated by the
 * 4%-white hairline (--hairline / border.subtle), with no border after the
 * last row. This is how the reference packs 4–9 items into one card without
 * the dividers turning into visual noise — never use border.default between
 * rows; that weight belongs to card edges and header strips.
 */
export const HairlineRowList: React.FC<HairlineRowListProps> = ({
  children,
  rowVerticalPadding = 8,
  style,
  testID,
}) => {
  const t = useTheme();
  const rows = React.Children.toArray(children);
  return (
    <View style={style} testID={testID}>
      {rows.map((row, i) => (
        <View
          key={React.isValidElement(row) && row.key != null ? row.key : i}
          style={[
            { paddingVertical: rowVerticalPadding },
            i < rows.length - 1 && {
              borderBottomWidth: 1,
              borderBottomColor: t.colors.border.subtle,
            },
          ]}
        >
          {row}
        </View>
      ))}
    </View>
  );
};
