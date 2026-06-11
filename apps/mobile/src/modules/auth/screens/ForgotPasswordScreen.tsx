import React, { useState } from 'react';
import { Button, Screen, Spacer, Text, Pressable } from '@anant/design-system';
import { useNavigation } from '@react-navigation/native';
import { AuthFormField } from '../components/AuthFormField';
import { apiClient } from '../../../lib/api/client';

export const ForgotPasswordScreen: React.FC = () => {
  const navigation = useNavigation();
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);

  const onSubmit = async () => {
    setLoading(true);
    try {
      await apiClient().post('/auth/password/forgot', { email: email.trim() });
      setSent(true);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Screen background="primary">
      <Spacer size={12} />
      <Text variant="caption" color="gold">
        ANANT CAPITAL
      </Text>
      <Spacer size={2} />
      <Text variant="display">Reset password</Text>
      <Spacer size={3} />
      <Text variant="body" color="secondary">
        {sent
          ? 'If that email is registered, you will receive instructions shortly.'
          : 'Enter the email associated with your account.'}
      </Text>
      <Spacer size={8} />
      {!sent && (
        <>
          <AuthFormField
            label="Email"
            keyboardType="email-address"
            textContentType="emailAddress"
            value={email}
            onChangeText={setEmail}
            placeholder="you@example.com"
          />
          <Spacer size={6} />
          <Button label="Send reset link" fullWidth onPress={onSubmit} loading={loading} />
        </>
      )}
      <Spacer size={4} />
      <Pressable
        onPress={() => navigation.goBack()}
        style={{ alignSelf: 'center' }}
      >
        <Text variant="bodySm" color="gold">
          Back to sign in
        </Text>
      </Pressable>
    </Screen>
  );
};
