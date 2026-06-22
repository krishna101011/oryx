import React from 'react';
import { ScrollView, View } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { Button, Screen, Skeleton, Spacer, Text } from '@oryx/design-system';
import { useDraftList } from '../hooks/useDrafts';
import { DraftCard } from '../components/DraftCard';

export const ContentHomeScreen: React.FC = () => {
  const navigation = useNavigation();
  const drafts = useDraftList();

  return (
    <Screen background="primary">
      <ScrollView showsVerticalScrollIndicator={false}>
        <Spacer size={6} />
        <Text variant="display">Content</Text>
        <Spacer size={2} />
        <Text variant="bodySm" color="secondary">
          Turn verified research packets into publishable content.
        </Text>
        <Spacer size={4} />
        <Button
          label="+ Generate from packet"
          variant="primary"
          fullWidth
          onPress={() =>
            // @ts-expect-error param-less navigate within the content stack
            navigation.navigate('GenerateDraft')
          }
        />
        <Spacer size={2} />
        <Button
          label="Review queue"
          variant="secondary"
          fullWidth
          onPress={() =>
            // @ts-expect-error param-less navigate within the content stack
            navigation.navigate('ReviewQueue')
          }
        />

        <Spacer size={6} />
        {drafts.isLoading ? (
          <Skeleton height={100} />
        ) : (drafts.data ?? []).length === 0 ? (
          <Text variant="bodySm" color="secondary">
            No drafts yet. Generate one from a ready research packet.
          </Text>
        ) : (
          (drafts.data ?? []).map((d) => (
            <View key={d.id}>
              <DraftCard
                draft={d}
                onPress={() =>
                  // @ts-expect-error param-carrying navigate
                  navigation.navigate('DraftEditor', { draftId: d.id })
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
