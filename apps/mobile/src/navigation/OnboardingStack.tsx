import React from 'react';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import type { OnboardingStackParamList } from './types';
import { WelcomeScreen } from '../modules/onboarding/screens/WelcomeScreen';
import { FocusAndSourcesScreen } from '../modules/onboarding/screens/FocusAndSourcesScreen';
import { NotificationsAndPermissionsScreen } from '../modules/onboarding/screens/NotificationsAndPermissionsScreen';
import { StyleAndStrictnessScreen } from '../modules/onboarding/screens/StyleAndStrictnessScreen';

const Stack = createNativeStackNavigator<OnboardingStackParamList>();

export const OnboardingStack: React.FC = () => (
  <Stack.Navigator
    screenOptions={{ headerShown: false, gestureEnabled: false }}
  >
    <Stack.Screen name="Welcome" component={WelcomeScreen} />
    <Stack.Screen name="FocusAndSources" component={FocusAndSourcesScreen} />
    <Stack.Screen
      name="NotificationsAndPermissions"
      component={NotificationsAndPermissionsScreen}
    />
    <Stack.Screen name="StyleAndStrictness" component={StyleAndStrictnessScreen} />
  </Stack.Navigator>
);
