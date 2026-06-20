import React, { useState } from 'react';
import { Button, Screen, Spacer, Text, Pressable } from '@oryx/design-system';
import { useNavigation } from '@react-navigation/native';
import { AuthFormField } from '../components/AuthFormField';
import { useAppDispatch } from '../../../store';
import { signin } from '../../../store/thunks/auth';
import { isApiError } from '../../../lib/errors';

export const SignInScreen: React.FC = () => {
  const dispatch = useAppDispatch();
  const navigation = useNavigation();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const onSubmit = async () => {
    setError(null);
    setLoading(true);
    try {
      await dispatch(signin(email.trim(), password));
    } catch (e) {
      if (isApiError(e)) setError(e.message);
      else setError('Could not reach the server. Check that the backend is running and try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Screen background="primary">
      <Spacer size={12} />
      <Text variant="caption" color="brand">
        ORYX
      </Text>
      <Spacer size={2} />
      <Text variant="display">Sign in</Text>
      <Spacer size={8} />

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
        textContentType="password"
        value={password}
        onChangeText={setPassword}
        placeholder="••••••••"
        errorText={error}
      />
      <Spacer size={6} />
      <Button label="Continue" fullWidth onPress={onSubmit} loading={loading} />
      <Spacer size={4} />
      <Pressable
        onPress={() => navigation.navigate('SignUp' as never)}
        style={{ alignSelf: 'center' }}
      >
        <Text variant="bodySm" color="secondary">
          Don't have an account?{' '}
          <Text variant="bodySm" color="brand">
            Sign up
          </Text>
        </Text>
      </Pressable>
      <Spacer size={2} />
      <Pressable
        onPress={() => navigation.navigate('ForgotPassword' as never)}
        style={{ alignSelf: 'center' }}
      >
        <Text variant="bodySm" color="tertiary">
          Forgot password?
        </Text>
      </Pressable>
    </Screen>
  );
};
