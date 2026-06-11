/** Border radius tokens. */
export const radius = {
  none: 0,
  sm: 6,
  md: 10,
  lg: 14,
  xl: 20,
  full: 9999,
} as const;

export type Radius = typeof radius;
export type RadiusKey = keyof Radius;
