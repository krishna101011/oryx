import React from 'react';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { StatusBar } from 'expo-status-bar';
import { AppProviders } from './src/providers/AppProviders';
import { RootNavigator } from './src/navigation/RootNavigator';
import { WebShell } from './src/components/web/WebShell';
import { useAppFonts } from './src/lib/fonts';

export default function App(): React.JSX.Element {
  const [fontsLoaded, fontError] = useAppFonts();

  // Hold render until the Genspark fonts (Inter + JetBrains Mono) are ready so
  // text never flashes in the system fallback. On a font error we proceed
  // anyway (fallback families) rather than blocking the app indefinitely.
  if (!fontsLoaded && !fontError) return <></>;

  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <AppProviders>
        <StatusBar style="light" />
        <WebShell>
          <RootNavigator />
        </WebShell>
      </AppProviders>
    </GestureHandlerRootView>
  );
}
