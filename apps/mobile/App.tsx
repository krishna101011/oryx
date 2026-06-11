import React from 'react';
import { StatusBar } from 'expo-status-bar';
import { AppProviders } from './src/providers/AppProviders';
import { RootNavigator } from './src/navigation/RootNavigator';

export default function App(): React.JSX.Element {
  return (
    <AppProviders>
      <StatusBar style="light" />
      <RootNavigator />
    </AppProviders>
  );
}
