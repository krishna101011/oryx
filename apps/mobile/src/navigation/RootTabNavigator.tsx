import React from 'react';
import { Platform } from 'react-native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { Icon, useTheme } from '@oryx/design-system';
import type { RootTabParamList } from './types';
import { DashboardScreen } from '../modules/dashboard/screens/DashboardScreen';
import { ResearchStack } from './ResearchStack';
import { ContentStack } from './ContentStack';
import { TeamStack } from './TeamStack';
import { AcademyStack } from './AcademyStack';
import { ActivityHomeScreen } from '../modules/activity/screens/ActivityHomeScreen';
import { SettingsStack } from './SettingsStack';
import { FeatureGate } from '../components/FeatureGate';

const Tab = createBottomTabNavigator<RootTabParamList>();

// Research / Content are flag-gated. Activity + Settings always on in Phase 2.
const GatedResearch: React.FC = () => (
  <FeatureGate flag="ff_research" name="Research">
    <ResearchStack />
  </FeatureGate>
);
const GatedContent: React.FC = () => (
  <FeatureGate flag="ff_content_drafts" name="Content">
    <ContentStack />
  </FeatureGate>
);

export const RootTabNavigator: React.FC = () => {
  const t = useTheme();
  return (
    <Tab.Navigator
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: t.colors.accent.amber,
        tabBarInactiveTintColor: t.colors.text.tertiary,
        // On web the ported Genspark sidebar (WebShell) is the primary nav, so
        // the bottom tab bar is hidden there; native keeps it.
        tabBarStyle:
          Platform.OS === 'web'
            ? { display: 'none' }
            : {
                backgroundColor: t.colors.bg.secondary,
                borderTopColor: t.colors.border.subtle,
                borderTopWidth: 1,
              },
        tabBarLabelStyle: { fontSize: 11, fontWeight: '500' },
      }}
    >
      <Tab.Screen
        name="Home"
        component={DashboardScreen}
        options={{
          tabBarIcon: ({ focused }) => (
            <Icon name="LayoutDashboard" color={focused ? 'brand' : 'tertiary'} />
          ),
        }}
      />
      <Tab.Screen
        name="Research"
        component={GatedResearch}
        options={{
          tabBarIcon: ({ focused }) => (
            <Icon name="BookOpen" color={focused ? 'brand' : 'tertiary'} />
          ),
        }}
      />
      <Tab.Screen
        name="Content"
        component={GatedContent}
        options={{
          tabBarIcon: ({ focused }) => (
            <Icon name="FileText" color={focused ? 'brand' : 'tertiary'} />
          ),
        }}
      />
      <Tab.Screen
        name="Team"
        component={TeamStack}
        options={{
          tabBarIcon: ({ focused }) => (
            <Icon name="Users" color={focused ? 'brand' : 'tertiary'} />
          ),
        }}
      />
      <Tab.Screen
        name="Academy"
        component={AcademyStack}
        options={{
          tabBarIcon: ({ focused }) => (
            <Icon name="GraduationCap" color={focused ? 'brand' : 'tertiary'} />
          ),
        }}
      />
      <Tab.Screen
        name="Activity"
        component={ActivityHomeScreen}
        options={{
          tabBarIcon: ({ focused }) => (
            <Icon name="Bell" color={focused ? 'brand' : 'tertiary'} />
          ),
        }}
      />
      <Tab.Screen
        name="Settings"
        component={SettingsStack}
        options={{
          tabBarIcon: ({ focused }) => (
            <Icon name="Settings" color={focused ? 'brand' : 'tertiary'} />
          ),
        }}
      />
    </Tab.Navigator>
  );
};
