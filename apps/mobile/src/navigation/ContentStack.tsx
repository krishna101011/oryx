import React from 'react';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { useTheme } from '@oryx/design-system';
import type { ContentStackParamList } from './types';
import { ContentHomeScreen } from '../modules/content/screens/ContentHomeScreen';
import { GenerateDraftScreen } from '../modules/content/screens/GenerateDraftScreen';
import { DraftEditorScreen } from '../modules/content/screens/DraftEditorScreen';

const Stack = createNativeStackNavigator<ContentStackParamList>();

export const ContentStack: React.FC = () => {
  const t = useTheme();
  return (
    <Stack.Navigator
      screenOptions={{
        headerStyle: { backgroundColor: t.colors.bg.primary },
        headerTintColor: t.colors.text.primary,
        headerTitleStyle: { fontWeight: '600' },
      }}
    >
      <Stack.Screen
        name="ContentHome"
        component={ContentHomeScreen}
        options={{ headerShown: false }}
      />
      <Stack.Screen
        name="GenerateDraft"
        component={GenerateDraftScreen}
        options={{ title: 'Generate' }}
      />
      <Stack.Screen
        name="DraftEditor"
        component={DraftEditorScreen}
        options={{ title: 'Draft' }}
      />
    </Stack.Navigator>
  );
};
