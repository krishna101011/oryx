/**
 * 8pt grid spacing tokens.
 * Every layout dimension must be a multiple of 4 via these tokens.
 */
export const spacing = {
  0: 0,
  1: 4,
  2: 8,
  3: 12,
  4: 16,
  5: 20,
  6: 24,
  8: 32,
  10: 40,
  12: 48,
  16: 64,
} as const;

export type Spacing = typeof spacing;
export type SpacingKey = keyof Spacing;
