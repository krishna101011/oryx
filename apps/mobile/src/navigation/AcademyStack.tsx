import React from 'react';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { useTheme } from '@oryx/design-system';
import type { AcademyStackParamList } from './types';
import { AcademyHomeScreen } from '../modules/training/screens/AcademyHomeScreen';
import { LessonViewerScreen } from '../modules/training/screens/LessonViewerScreen';

const Stack = createNativeStackNavigator<AcademyStackParamList>();

export const AcademyStack: React.FC = () => {
  const t = useTheme();
  return (
    <Stack.Navigator
      screenOptions={{
        headerStyle: { backgroundColor: t.colors.bg.primary },
        headerTintColor: t.colors.text.primary,
        headerTitleStyle: { fontWeight: '600' },
      }}
    >
      <Stack.Screen name="AcademyHome" component={AcademyHomeScreen} options={{ headerShown: false }} />
      <Stack.Screen name="LessonViewer" component={LessonViewerScreen} options={{ title: 'Lesson' }} />
    </Stack.Navigator>
  );
};
