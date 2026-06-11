import React from 'react';
import { Screen, Spacer, Text } from '@anant/design-system';

/**
 * Deep-link target. Phase 2: stub screen — the backend returns 501 for
 * password reset until Phase 6 wires email delivery.
 */
export const ResetPasswordScreen: React.FC = () => (
  <Screen background="primary">
    <Spacer size={12} />
    <Text variant="display">Reset password</Text>
    <Spacer size={3} />
    <Text variant="body" color="secondary">
      Password reset will be available once email delivery ships in Phase 6.
    </Text>
  </Screen>
);
