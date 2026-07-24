import React from 'react';
import { ScrollView, StyleSheet, View } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import {
  Card,
  CardHeader,
  HairlineRowList,
  Pressable,
  Screen,
  Skeleton,
  Spacer,
  Text,
  useGx,
} from '@oryx/design-system';
import { useDraftList } from '../hooks/useDrafts';
import { DraftCard } from '../components/DraftCard';
import { EmptyState } from '../../../components/EmptyState';
import { CONTENT_ACTIONS, draftCountSub } from '../home';

/**
 * Content Studio home (design-foundation wave, CS-1/CS-2, 2026-07-15). The
 * five stacked full-width Buttons are replaced by the compact gx.btn toolbar
 * (reference button scale: 5/11px padding, 11.5px text) living in a Card's
 * card-head area — the reference's own 3-pane editor toolbar is out of scope
 * for this list screen. Every action from the old stack is preserved 1:1 via
 * CONTENT_ACTIONS (see ../home.ts); action parity is tested against that list.
 */
export const ContentHomeScreen: React.FC = () => {
  const gx = useGx();
  const navigation = useNavigation();
  const drafts = useDraftList();

  const navigateTo = (screen: string) =>
    // @ts-expect-error param-less navigate within the content stack
    navigation.navigate(screen);

  return (
    <Screen background="primary">
      <ScrollView showsVerticalScrollIndicator={false}>
        <Spacer size={6} />
        <Text variant="pageTitle">Content</Text>
        <Spacer size={2} />
        <Text variant="bodySm" color="secondary">
          Turn verified research packets into publishable content.
        </Text>
        <Spacer size={4} />

        <Card header={<CardHeader title="Actions" />}>
          <View style={styles.toolbar}>
            {CONTENT_ACTIONS.map((action) => (
              <Pressable
                key={action.id}
                onPress={() => navigateTo(action.screen)}
                accessibilityRole="button"
                accessibilityLabel={action.label}
                style={[gx.btn, action.primary && gx.btnPrimary]}
              >
                <Text
                  variant="bodySm"
                  style={action.primary ? gx.btnPrimaryText : gx.btnText}
                >
                  {action.primary ? `+ ${action.label}` : action.label}
                </Text>
              </Pressable>
            ))}
          </View>
        </Card>

        <Spacer size={6} />
        {drafts.isLoading ? (
          <Skeleton height={100} />
        ) : (drafts.data ?? []).length === 0 ? (
          <EmptyState
            icon="horn"
            title="Start your first draft"
            description="Drafts generate from verified research packets, so everything here traces back to a source."
            ctaLabel="Generate draft"
            onPress={() => navigateTo('GenerateDraft')}
          />
        ) : (
          <Card
            header={<CardHeader title="Drafts" sub={draftCountSub(drafts.data)} />}
          >
            <HairlineRowList>
              {(drafts.data ?? []).map((d) => (
                <View key={d.id}>
                  <DraftCard
                    draft={d}
                    onPress={() =>
                      // @ts-expect-error param-carrying navigate
                      navigation.navigate('DraftEditor', { draftId: d.id })
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

const styles = StyleSheet.create({
  toolbar: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
});
