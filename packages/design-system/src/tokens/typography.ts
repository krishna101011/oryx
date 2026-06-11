/**
 * Typography tokens.
 * Six text sizes total. No ad-hoc font sizes at call sites.
 *
 * Font choice: Inter for UI text, JetBrains Mono for numbers / tickers.
 */
export const typography = {
  display: {
    fontFamily: 'Inter-Bold',
    fontSize: 32,
    fontWeight: '700' as const,
    lineHeight: 38,
    letterSpacing: -0.5,
  },
  h1: {
    fontFamily: 'Inter-Bold',
    fontSize: 24,
    fontWeight: '700' as const,
    lineHeight: 30,
    letterSpacing: -0.25,
  },
  h2: {
    fontFamily: 'Inter-SemiBold',
    fontSize: 20,
    fontWeight: '600' as const,
    lineHeight: 26,
    letterSpacing: 0,
  },
  body: {
    fontFamily: 'Inter-Regular',
    fontSize: 16,
    fontWeight: '400' as const,
    lineHeight: 24,
    letterSpacing: 0,
  },
  bodySm: {
    fontFamily: 'Inter-Regular',
    fontSize: 14,
    fontWeight: '400' as const,
    lineHeight: 20,
    letterSpacing: 0,
  },
  caption: {
    fontFamily: 'Inter-Medium',
    fontSize: 12,
    fontWeight: '500' as const,
    lineHeight: 16,
    letterSpacing: 0.4,
  },
  mono: {
    fontFamily: 'JetBrainsMono-Medium',
    fontSize: 13,
    fontWeight: '500' as const,
    lineHeight: 18,
    letterSpacing: 0,
  },
} as const;

export type Typography = typeof typography;
export type TextVariant = keyof Typography;
