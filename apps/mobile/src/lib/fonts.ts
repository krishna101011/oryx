import {
  useFonts,
  Inter_400Regular,
  Inter_500Medium,
  Inter_600SemiBold,
  Inter_700Bold,
} from '@expo-google-fonts/inter';
import {
  JetBrainsMono_400Regular,
  JetBrainsMono_500Medium,
  JetBrainsMono_600SemiBold,
} from '@expo-google-fonts/jetbrains-mono';

/**
 * Loads the Genspark type system fonts: Inter (400/500/600/700) for UI text and
 * JetBrains Mono (400/500/600) for numerics/tickers. The keys here are the exact
 * family names referenced by the typography tokens (design-system).
 *
 * Returns [loaded, error] from expo-font's useFonts. App.tsx holds the splash
 * until `loaded` (or `error`) so no text renders in the system fallback first.
 */
export function useAppFonts(): [boolean, Error | null] {
  const [loaded, error] = useFonts({
    Inter_400Regular,
    Inter_500Medium,
    Inter_600SemiBold,
    Inter_700Bold,
    JetBrainsMono_400Regular,
    JetBrainsMono_500Medium,
    JetBrainsMono_600SemiBold,
  });
  return [loaded, error];
}
