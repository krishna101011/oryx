import React, { useEffect, useState } from 'react';
import { useNavigation } from '@react-navigation/native';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Button, Screen, Spacer, Text } from '@oryx/design-system';
import type { Profile, UpdateProfileRequest } from '@oryx/shared-types';
import { useMe } from '../../../hooks/useMe';
import { AuthFormField } from '../../auth/components/AuthFormField';
import { apiClient } from '../../../lib/api/client';

export const ProfileEditScreen: React.FC = () => {
  const navigation = useNavigation();
  const me = useMe();
  const queryClient = useQueryClient();
  const [displayName, setDisplayName] = useState('');
  const [headline, setHeadline] = useState('');

  useEffect(() => {
    if (me.data?.profile) {
      setDisplayName(me.data.profile.displayName ?? '');
      setHeadline(me.data.profile.headline ?? '');
    }
  }, [me.data?.profile]);

  const mutation = useMutation({
    mutationFn: (body: UpdateProfileRequest) =>
      apiClient().patch<Profile, UpdateProfileRequest>('/profiles/me', body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['me'] }),
  });

  const onSave = async () => {
    await mutation.mutateAsync({
      displayName: displayName.trim(),
      headline: headline.trim() || null,
    });
    navigation.goBack();
  };

  return (
    <Screen background="primary">
      <Spacer size={6} />
      <Text variant="display">Profile</Text>
      <Spacer size={6} />
      <AuthFormField
        label="Display name"
        value={displayName}
        onChangeText={setDisplayName}
      />
      <Spacer size={4} />
      <AuthFormField
        label="Headline"
        value={headline}
        onChangeText={setHeadline}
        placeholder="What do you focus on?"
      />
      <Spacer size={6} />
      <Button label="Save" fullWidth onPress={onSave} loading={mutation.isPending} />
    </Screen>
  );
};
