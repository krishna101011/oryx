import React from 'react';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { useTheme } from '@oryx/design-system';
import type { TeamStackParamList } from './types';
import { TeamHomeScreen } from '../modules/team/screens/TeamHomeScreen';
import { TeamActivityScreen } from '../modules/team/screens/TeamActivityScreen';

const Stack = createNativeStackNavigator<TeamStackParamList>();

export const TeamStack: React.FC = () => {
  const t = useTheme();
  return (
    <Stack.Navigator
      screenOptions={{
        headerStyle: { backgroundColor: t.colors.bg.primary },
        headerTintColor: t.colors.text.primary,
        headerTitleStyle: { fontWeight: '600' },
      }}
    >
      <Stack.Screen name="TeamHome" component={TeamHomeScreen} options={{ headerShown: false }} />
      <Stack.Screen name="TeamActivity" component={TeamActivityScreen} options={{ title: 'Activity' }} />
    </Stack.Navigator>
  );
};
