import React, { createContext, useContext, useMemo } from 'react';
import type { Theme } from '../tokens';
import { theme as defaultTheme } from '../tokens';

const ThemeContext = createContext<Theme>(defaultTheme);

export interface ThemeProviderProps {
  theme?: Theme;
  children: React.ReactNode;
}

/**
 * Wraps the app and provides the design system theme tokens via context.
 * Pass `theme={themes[mode]}` to switch modes (theming Phase A, 2026-07-16);
 * with no prop it provides the dark default.
 */
export const ThemeProvider: React.FC<ThemeProviderProps> = ({
  theme = defaultTheme,
  children,
}) => {
  const value = useMemo(() => theme, [theme]);
  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
};

/** Read the current theme. Components consume tokens through this hook. */
export const useTheme = (): Theme => useContext(ThemeContext);
