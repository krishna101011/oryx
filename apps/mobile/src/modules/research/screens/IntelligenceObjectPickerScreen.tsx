import React, { useState } from 'react';
import { ScrollView, StyleSheet, TextInput, View } from 'react-native';
import { type RouteProp, useNavigation, useRoute } from '@react-navigation/native';
import {
  Pressable,
  Screen,
  Skeleton,
  Spacer,
  Text,
  useTheme,
} from '@oryx/design-system';
import type { ResearchStackParamList } from '../../../navigation/types';
import { IntelligenceObjectCard } from '../../verification/components/IntelligenceObjectCard';
import { useIntelligenceObjects } from '../../verification/hooks/useIntelligence';
import { useAddItem } from '../hooks/useResearch';

const STATUS_FILTERS = ['verified', 'contested', 'unverified'] as const;

export const IntelligenceObjectPickerScreen: React.FC = () => {
  const route =
    useRoute<RouteProp<ResearchStackParamList, 'IntelligenceObjectPicker'>>();
  const navigation = useNavigation();
  const theme = useTheme();
  const { rwsId, workspaceName } = route.params;

  const [search, setSearch] = useState('');
  const [status, setStatus] = useState<string | undefined>(undefined);
  const objects = useIntelligenceObjects({ search: search || undefined, status });
  const addItem = useAddItem(rwsId);

  const onPick = (objectId: string) => {
    addItem.mutate(
      { intelligence_object_id: objectId },
      { onSuccess: () => navigation.goBack() },
    );
  };

  return (
    <Screen background="primary">
      <ScrollView showsVerticalScrollIndicator={false}>
        <Spacer size={6} />
        <Text variant="display">Add objects</Text>
        <Spacer size={1} />
        <Text variant="bodySm" color="secondary">
          to {workspaceName}
        </Text>

        <Spacer size={4} />
        <TextInput
          value={search}
          onChangeText={setSearch}
          placeholder="Search headlines"
          placeholderTextColor={theme.colors.text.tertiary}
          style={[
            styles.input,
            {
              borderColor: theme.colors.border.default,
              color: theme.colors.text.primary,
            },
          ]}
        />
        <Spacer size={3} />
        <View style={styles.filterRow}>
          <Pressable onPress={() => setStatus(undefined)}>
            <Text variant="caption" color={status ? 'tertiary' : 'brand'}>
              All
            </Text>
          </Pressable>
          {STATUS_FILTERS.map((s) => (
            <Pressable key={s} onPress={() => setStatus(s)}>
              <Text variant="caption" color={status === s ? 'brand' : 'tertiary'}>
                {s}
              </Text>
            </Pressable>
          ))}
        </View>

        <Spacer size={5} />
        {objects.isLoading ? (
          <Skeleton height={100} />
        ) : (objects.data ?? []).length === 0 ? (
          <Text variant="bodySm" color="secondary">
            No matching objects.
          </Text>
        ) : (
          (objects.data ?? []).map((o) => (
            <View key={o.id}>
              <IntelligenceObjectCard
                headline={o.headline}
                epistemicType={o.epistemicType}
                confidenceScore={o.confidenceScore}
                verificationStatus={o.verificationStatus}
                onPress={() => onPick(o.id)}
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
    borderRadius: 10,
    borderWidth: 1,
    padding: 12,
  },
  filterRow: {
    flexDirection: 'row',
    gap: 16,
  },
});
