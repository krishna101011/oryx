import React, { useState } from 'react';
import { ScrollView, StyleSheet, TextInput, View } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import {
  Button,
  Card,
  Screen,
  Skeleton,
  Spacer,
  Text,
  useTheme,
} from '@oryx/design-system';
import { useCreateWorkspace, useResearchWorkspaces } from '../hooks/useResearch';
import { WorkspaceCard } from '../components/WorkspaceCard';

export const ResearchWorkspaceListScreen: React.FC = () => {
  const navigation = useNavigation();
  const theme = useTheme();
  const workspaces = useResearchWorkspaces();
  const create = useCreateWorkspace();
  const [name, setName] = useState('');

  const onCreate = () => {
    if (!name.trim()) return;
    create.mutate({ name: name.trim() }, { onSuccess: () => setName('') });
  };

  return (
    <Screen background="primary">
      <ScrollView showsVerticalScrollIndicator={false}>
        <Spacer size={6} />
        <Text variant="display">Research</Text>
        <Spacer size={4} />

        <Card variant="elevated">
          <Text variant="bodySm" color="secondary">
            New workspace
          </Text>
          <Spacer size={2} />
          <TextInput
            value={name}
            onChangeText={setName}
            placeholder="Workspace name"
            placeholderTextColor={theme.colors.text.tertiary}
            style={[styles.input, { color: theme.colors.text.primary }]}
          />
          <Spacer size={2} />
          <Button
            label="+ New Workspace"
            variant="primary"
            fullWidth
            disabled={!name.trim() || create.isPending}
            onPress={onCreate}
          />
        </Card>

        <Spacer size={6} />
        {workspaces.isLoading ? (
          <Skeleton height={100} />
        ) : (workspaces.data ?? []).length === 0 ? (
          <Text variant="bodySm" color="secondary">
            No workspaces yet. Create one to start curating intelligence.
          </Text>
        ) : (
          (workspaces.data ?? []).map((w) => (
            <View key={w.id}>
              <WorkspaceCard
                workspace={w}
                onPress={() =>
                  // @ts-expect-error param-carrying navigate
                  navigation.navigate('ResearchWorkspaceDetail', { rwsId: w.id })
                }
              />
              <Spacer size={2} />
            </View>
          ))
        )}
        <Spacer size={8} />
      </ScrollView>
    </Screen>
  );
};

const styles = StyleSheet.create({
  input: {
    borderColor: 'rgba(127,127,127,0.35)',
    borderRadius: 10,
    borderWidth: 1,
    padding: 12,
  },
});
