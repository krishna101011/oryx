import React from 'react';
import * as Lucide from 'lucide-react-native';
import { useTheme } from '../theme/ThemeProvider';

export type IconName = keyof typeof Lucide;
export type IconSize = 'sm' | 'md' | 'lg';

export interface IconProps {
  name: IconName;
  size?: IconSize | number;
  color?: 'primary' | 'secondary' | 'tertiary' | 'brand' | 'danger';
}

const SIZE_MAP: Record<IconSize, number> = { sm: 16, md: 20, lg: 24 };

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
  const resolvedColor =
    color === 'brand'
      ? t.colors.accent.teal
      : color === 'danger'
        ? t.colors.semantic.danger
        : t.colors.text[color];

  return <LucideIcon size={px} color={resolvedColor} strokeWidth={1.75} />;
};
