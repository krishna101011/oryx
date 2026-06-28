import React from 'react';
import * as Lucide from 'lucide-react-native';
import { useTheme } from '../theme/ThemeProvider';

export type IconName = keyof typeof Lucide;
export type IconSize = 'sm' | 'md' | 'lg';

/** Decorative/category accent keys exposed to icon glyphs ("Midnight Citrus"). */
type IconAccent = 'amber' | 'coral' | 'teal' | 'slateBlue' | 'plum' | 'cream';

export interface IconProps {
  name: IconName;
  size?: IconSize | number;
  color?: 'primary' | 'secondary' | 'tertiary' | 'brand' | 'danger' | IconAccent;
}

const SIZE_MAP: Record<IconSize, number> = { sm: 16, md: 20, lg: 24 };

const ACCENT_KEYS: readonly IconAccent[] = [
  'amber',
  'coral',
  'teal',
  'slateBlue',
  'plum',
  'cream',
];

export const Icon: React.FC<IconProps> = ({
  name,
  size = 'md',
  color = 'primary',
}) => {
  const t = useTheme();
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const LucideIcon = Lucide[name] as any;
  if (!LucideIcon) return null;

  const px = typeof size === 'number' ? size : SIZE_MAP[size];
  // 'brand' resolves to the new primary accent (amber).
  const resolvedColor =
    color === 'brand'
      ? t.colors.accent.amber
      : color === 'danger'
        ? t.colors.semantic.danger
        : (ACCENT_KEYS as readonly string[]).includes(color)
          ? t.colors.accent[color as IconAccent]
          : t.colors.text[color as 'primary' | 'secondary' | 'tertiary'];

  return <LucideIcon size={px} color={resolvedColor} strokeWidth={1.75} />;
};
