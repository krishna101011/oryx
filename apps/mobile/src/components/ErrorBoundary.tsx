import React from 'react';
import { View, StyleSheet } from 'react-native';
import { logger } from '../lib/logger';

interface State {
  error: Error | null;
}

export class ErrorBoundary extends React.Component<
  { children: React.ReactNode },
  State
> {
  override state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  override componentDidCatch(error: Error, info: React.ErrorInfo): void {
    logger.error('react.error_boundary', {
      message: error.message,
      stack: info.componentStack ?? null,
    });
  }

  override render(): React.ReactNode {
    if (this.state.error) {
      return (
        <View style={styles.container}>
          {/* Intentionally minimal — design-system theme may not be available if the error is inside ThemeProvider */}
        </View>
      );
    }
    return this.props.children;
  }
}

const styles = StyleSheet.create({
  // The boundary may render when ThemeProvider itself crashed, so the
  // token hook is unavailable here by construction.
  // eslint-disable-next-line no-restricted-syntax
  container: { flex: 1, backgroundColor: '#0A0A0A' },
});
