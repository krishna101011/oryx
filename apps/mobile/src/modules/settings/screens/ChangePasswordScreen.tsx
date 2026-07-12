import React, { useState } from 'react';
import { useNavigation } from '@react-navigation/native';
import { Button, Screen, Spacer, Text } from '@oryx/design-system';
import type { ChangePasswordRequest } from '@oryx/shared-types';
import { AuthFormField } from '../../auth/components/AuthFormField';
import { apiClient } from '../../../lib/api/client';
import { isApiError } from '../../../lib/errors';

export const ChangePasswordScreen: React.FC = () => {
  const navigation = useNavigation();
  const [currentPassword, setCurrent] = useState('');
  const [newPassword, setNew] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const onSubmit = async () => {
    setError(null);
    setLoading(true);
    try {
      const body: ChangePasswordRequest = {
        currentPassword,
        newPassword,
      };
      await apiClient().post('/auth/password/change', body);
      navigation.goBack();
    } catch (e) {
      if (isApiError(e)) setError(e.message);
      else setError('Could not change password.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Screen background="primary">
      <Spacer size={6} />
      <Text variant="pageTitle">Change password</Text>
      <Spacer size={6} />
      <AuthFormField
        label="Current password"
        secureTextEntry
        value={currentPassword}
        onChangeText={setCurrent}
      />
      <Spacer size={4} />
      <AuthFormField
        label="New password"
        secureTextEntry
        value={newPassword}
        onChangeText={setNew}
        placeholder="At least 10 characters"
        errorText={error}
      />
      <Spacer size={6} />
      <Button label="Update password" fullWidth onPress={onSubmit} loading={loading} />
    </Screen>
  );
};
