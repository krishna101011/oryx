import React from 'react';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import type { AuthStackParamList } from './types';
import { SignInScreen } from '../modules/auth/screens/SignInScreen';
import { SignUpScreen } from '../modules/auth/screens/SignUpScreen';
import { ForgotPasswordScreen } from '../modules/auth/screens/ForgotPasswordScreen';
import { ResetPasswordScreen } from '../modules/auth/screens/ResetPasswordScreen';

const Stack = createNativeStackNavigator<AuthStackParamList>();

export const AuthStack: React.FC = () => (
  <Stack.Navigator screenOptions={{ headerShown: false }}>
    <Stack.Screen name="SignIn" component={SignInScreen} />
    <Stack.Screen name="SignUp" component={SignUpScreen} />
    <Stack.Screen name="ForgotPassword" component={ForgotPasswordScreen} />
    <Stack.Screen name="ResetPassword" component={ResetPasswordScreen} />
  </Stack.Navigator>
);
