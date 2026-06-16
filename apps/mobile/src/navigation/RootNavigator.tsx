import React from 'react';
import { ActivityIndicator, View, StyleSheet } from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { useTheme } from '@oryx/design-system';
import { useAppSelector } from '../store';
import { useMe } from '../hooks/useMe';
import type { RootStackParamList } from './types';
import { AuthStack } from './AuthStack';
import { OnboardingStack } from './OnboardingStack';
import { RootTabNavigator } from './RootTabNavigator';
import { linking } from './linking';

const Stack = createNativeStackNavigator<RootStackParamList>();

/**
 * Root decision logic.
 *
 *   status === 'unknown'                        → splash
 *   status === 'unauthenticated'                → AuthStack
 *   authenticated + /me loading (no data yet)   → splash (avoid wrong branch)
 *   authenticated + onboarding incomplete       → OnboardingStack
 *   authenticated + onboarding complete         → RootTabNavigator
 *
 * Terminal auth errors on /me are handled inside useMe by dispatching
 * signedOut(), which causes this component to re-render in 'unauthenticated'.
 */
const Splash: React.FC = () => {
  const t = useTheme();
  return (
    <View style={[styles.splash, { backgroundColor: t.colors.bg.primary }]}>
      <ActivityIndicator color={t.colors.accent.teal} />
    </View>
  );
};

export const RootNavigator: React.FC = () => {
  const status = useAppSelector((s) => s.auth.status);
  const me = useMe();

  if (status === 'unknown') {
    return <Splash />;
  }

  // Authenticated but /me hasn't resolved yet — show splash rather than
  // routing to OnboardingStack against undefined data.
  const meReady =
    status !== 'authenticated' || me.data !== undefined || me.isError;
  if (!meReady) {
    return <Splash />;
  }

  const onboardingIncomplete =
    status === 'authenticated' &&
    me.data?.onboarding?.state !== 'complete';

  return (
    <NavigationContainer linking={linking}>
      <Stack.Navigator screenOptions={{ headerShown: false }}>
        {status !== 'authenticated' ? (
          <Stack.Screen name="Auth" component={AuthStack} />
        ) : onboardingIncomplete ? (
          <Stack.Screen name="Onboarding" component={OnboardingStack} />
        ) : (
          <Stack.Screen name="Tabs" component={RootTabNavigator} />
        )}
      </Stack.Navigator>
    </NavigationContainer>
  );
};

const styles = StyleSheet.create({
  splash: { flex: 1, alignItems: 'center', justifyContent: 'center' },
});
