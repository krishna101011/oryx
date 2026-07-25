import React, { useRef, useState } from 'react';
import { ScrollView, TextInput, View } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import {
  Button,
  Card,
  CardHeader,
  HairlineRowList,
  Screen,
  SkeletonRow,
  Spacer,
  Text,
  useTheme,
} from '@oryx/design-system';
import { useCreateWorkspace, useResearchWorkspaces } from '../hooks/useResearch';
import { WorkspaceCard } from '../components/WorkspaceCard';
import { workspaceCountSub } from '../list';
import { EmptyState } from '../../../components/EmptyState';

/**
 * Research Workspace list (design-foundation wave, 2026-07-13). Rows render
 * through CardHeader + HairlineRowList with the RW-1 anatomy (WorkspaceCard).
 * RW-2's selected treatment is DEFERRED: no "currently open workspace"
 * concept exists anywhere in state (status 'active'|'archived' is lifecycle,
 * not selection), and inventing one here would be a fake state with no
 * backing logic. RW-4's inner-card outline sections are NOT applicable: this
 * list is a flat, ungrouped collection — the card header's real count sub is
 * the honest extent of that pattern here.
 */
export const ResearchWorkspaceListScreen: React.FC = () => {
  const navigation = useNavigation();
  const theme = useTheme();
  const workspaces = useResearchWorkspaces();
  const create = useCreateWorkspace();
  const [name, setName] = useState('');
  const nameInput = useRef<TextInput>(null);

  const onCreate = () => {
    if (!name.trim()) return;
    create.mutate({ name: name.trim() }, { onSuccess: () => setName('') });
  };

  return (
    <Screen background="primary">
      <ScrollView showsVerticalScrollIndicator={false}>
        <Spacer size={6} />
        <Text variant="pageTitle">Research</Text>
        <Spacer size={4} />

        <Card variant="elevated">
          <Text variant="bodySm" color="secondary">
            New workspace
          </Text>
          <Spacer size={2} />
          <TextInput
            ref={nameInput}
            value={name}
            onChangeText={setName}
            placeholder="Workspace name"
            placeholderTextColor={theme.colors.text.tertiary}
            // Reference input surface (--elev bg, --border, 5px corners — the
            // .card-head input radius, radius.md): tokens only, the RW-3 fix.
            style={{
              backgroundColor: theme.colors.bg.elevated,
              borderColor: theme.colors.border.default,
              borderRadius: theme.radius.md,
              borderWidth: 1,
              padding: theme.spacing[3],
              color: theme.colors.text.primary,
            }}
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
          <Card header={<CardHeader title="Workspaces" />}>
            <HairlineRowList>
              {/* WorkspaceCard anatomy: RWS-XXXXXXXX mono-id (~72px) + status
                  chip on the head line, title, meta line, chevron gap. */}
              <SkeletonRow leadingWidth={72} hasTrailingChip />
              <SkeletonRow leadingWidth={72} hasTrailingChip />
              <SkeletonRow leadingWidth={72} hasTrailingChip />
            </HairlineRowList>
          </Card>
        ) : (workspaces.data ?? []).length === 0 ? (
          <EmptyState
            icon="horn"
            title="Create a workspace"
            description="Organize verified intelligence here before assembling it into a packet."
            ctaLabel="New workspace"
            onPress={() => nameInput.current?.focus()}
          />
        ) : (
          <Card
            header={
              <CardHeader title="Workspaces" sub={workspaceCountSub(workspaces.data)} />
            }
          >
            <HairlineRowList>
              {(workspaces.data ?? []).map((w) => (
                <View key={w.id}>
                  <WorkspaceCard
                    workspace={w}
                    onPress={() =>
                      // @ts-expect-error param-carrying navigate
                      navigation.navigate('ResearchWorkspaceDetail', { rwsId: w.id })
                    }
                  />
                </View>
              ))}
            </HairlineRowList>
          </Card>
        )}
        <Spacer size={8} />
      </ScrollView>
    </Screen>
  );
};
