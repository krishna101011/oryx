import React from 'react';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { useTheme } from '@anant/design-system';
import type { ResearchStackParamList } from './types';
import { ResearchWorkspaceListScreen } from '../modules/research/screens/ResearchWorkspaceListScreen';
import { ResearchWorkspaceDetailScreen } from '../modules/research/screens/ResearchWorkspaceDetailScreen';
import { IntelligenceObjectPickerScreen } from '../modules/research/screens/IntelligenceObjectPickerScreen';
import { ResearchPacketScreen } from '../modules/research/screens/ResearchPacketScreen';
import { IntelligenceObjectDetailScreen } from '../modules/verification/screens/IntelligenceObjectDetailScreen';
import { ClaimDetailScreen } from '../modules/verification/screens/ClaimDetailScreen';

const Stack = createNativeStackNavigator<ResearchStackParamList>();

export const ResearchStack: React.FC = () => {
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
        name="ResearchWorkspaceList"
        component={ResearchWorkspaceListScreen}
        options={{ headerShown: false }}
      />
      <Stack.Screen
        name="ResearchWorkspaceDetail"
        component={ResearchWorkspaceDetailScreen}
        options={{ title: 'Workspace' }}
      />
      <Stack.Screen
        name="IntelligenceObjectPicker"
        component={IntelligenceObjectPickerScreen}
        options={{ title: 'Add objects' }}
      />
      <Stack.Screen
        name="ResearchPacket"
        component={ResearchPacketScreen}
        options={{ title: 'Packet' }}
      />
      <Stack.Screen
        name="IntelligenceObjectDetail"
        component={IntelligenceObjectDetailScreen}
        options={{ title: 'Object' }}
      />
      <Stack.Screen
        name="ClaimDetail"
        component={ClaimDetailScreen}
        options={{ title: 'Claim' }}
      />
    </Stack.Navigator>
  );
};
