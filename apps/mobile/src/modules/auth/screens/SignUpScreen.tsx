import React, { useState } from 'react';
import { Button, Screen, Spacer, Text, Pressable } from '@anant/design-system';
import { useNavigation } from '@react-navigation/native';
import { AuthFormField } from '../components/AuthFormField';
import { useAppDispatch } from '../../../store';
import { signup } from '../../../store/thunks/auth';
import { isApiError } from '../../../lib/errors';

export const SignUpScreen: React.FC = () => {
  const dispatch = useAppDispatch();
  const navigation = useNavigation();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const onSubmit = async () => {
    setError(null);
    if (!displayName.trim()) {
      setError('Display name is required');
      return;
    }
    setLoading(true);
    try {
      await dispatch(signup(email.trim(), password, displayName.trim()));
    } catch (e) {
      if (isApiError(e)) setError(e.message);
      else setError('Unable to sign up. Try again.');
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
      <Text variant="display">Create account</Text>
      <Spacer size={8} />

      <AuthFormField
        label="Display name"
        value={displayName}
        onChangeText={setDisplayName}
        placeholder="Your name"
      />
      <Spacer size={4} />
      <AuthFormField
        label="Email"
        keyboardType="email-address"
        textContentType="emailAddress"
        value={email}
        onChangeText={setEmail}
        placeholder="you@example.com"
      />
      <Spacer size={4} />
      <AuthFormField
        label="Password"
        secureTextEntry
        textContentType="newPassword"
        value={password}
        onChangeText={setPassword}
        placeholder="At least 10 characters"
        errorText={error}
      />
      <Spacer size={6} />
      <Button label="Create account" fullWidth onPress={onSubmit} loading={loading} />
      <Spacer size={4} />
      <Pressable
        onPress={() => navigation.goBack()}
        style={{ alignSelf: 'center' }}
      >
        <Text variant="bodySm" color="secondary">
          Have an account?{' '}
          <Text variant="bodySm" color="gold">
            Sign in
          </Text>
        </Text>
      </Pressable>
    </Screen>
  );
};
