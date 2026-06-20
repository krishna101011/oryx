import React from 'react';
import { View, Text, ScrollView, StyleSheet } from 'react-native';
import { logger } from '../lib/logger';

interface State {
  error: Error | null;
  stack: string | null;
}

export class ErrorBoundary extends React.Component<
  { children: React.ReactNode },
  State
> {
  override state: State = { error: null, stack: null };

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { error };
  }

  override componentDidCatch(error: Error, info: React.ErrorInfo): void {
    logger.error('react.error_boundary', {
      message: error.message,
      stack: info.componentStack ?? null,
    });
    this.setState({ stack: info.componentStack ?? null });
  }

  override render(): React.ReactNode {
    if (this.state.error) {
      return (
        <View style={styles.container}>
          <Text style={styles.title}>Something went wrong</Text>
          <Text style={styles.message}>{this.state.error.message}</Text>
          {__DEV__ && this.state.stack ? (
            <ScrollView style={styles.stackScroll}>
              <Text style={styles.stack}>{this.state.stack}</Text>
            </ScrollView>
          ) : null}
        </View>
      );
    }
    return this.props.children;
  }
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0A0A0F',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 24,
  },
  title: {
    color: '#FFFFFF',
    fontSize: 18,
    fontWeight: '600',
    marginBottom: 12,
    textAlign: 'center',
  },
  message: {
    color: '#FF6B6B',
    fontSize: 13,
    fontFamily: 'monospace',
    textAlign: 'center',
    marginBottom: 16,
  },
  stackScroll: {
    maxHeight: 300,
    width: '100%',
  },
  stack: {
    color: '#888888',
    fontSize: 11,
    fontFamily: 'monospace',
  },
});
