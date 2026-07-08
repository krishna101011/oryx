import React from 'react';
import { View, StyleSheet } from 'react-native';
import { Button, Screen, Spacer, Text, useTheme } from '@oryx/design-system';

export interface OnboardingShellProps {
  stepIndex: number; // 0..3
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  onContinue: () => void | Promise<void>;
  continueLabel?: string;
  continueDisabled?: boolean;
  loading?: boolean;
}

const TOTAL_STEPS = 4;

export const OnboardingShell: React.FC<OnboardingShellProps> = ({
  stepIndex,
  title,
  subtitle,
  children,
  onContinue,
  continueLabel = 'Continue',
  continueDisabled,
  loading,
}) => {
  const t = useTheme();
  return (
    <Screen background="primary">
      <Spacer size={6} />
      <View style={styles.progressRow}>
        {Array.from({ length: TOTAL_STEPS }).map((_, i) => {
          const active = i <= stepIndex;
          return (
            <View
              key={i}
              style={[
                styles.pip,
                {
                  backgroundColor: active
                    ? t.colors.semantic.positiveText
                    : t.colors.border.default,
                  flex: 1,
                  marginRight: i === TOTAL_STEPS - 1 ? 0 : 6,
                },
              ]}
            />
          );
        })}
      </View>
      <Spacer size={6} />
      <Text variant="caption" color="brand">
        STEP {stepIndex + 1} OF {TOTAL_STEPS}
      </Text>
      <Spacer size={2} />
      <Text variant="display">{title}</Text>
      {subtitle ? (
        <>
          <Spacer size={2} />
          <Text variant="body" color="secondary">
            {subtitle}
          </Text>
        </>
      ) : null}
      <Spacer size={6} />
      <View style={{ flex: 1 }}>{children}</View>
      <Spacer size={4} />
      <Button
        label={continueLabel}
        fullWidth
        onPress={onContinue}
        disabled={continueDisabled}
        loading={loading}
      />
      <Spacer size={6} />
    </Screen>
  );
};

const styles = StyleSheet.create({
  progressRow: { flexDirection: 'row' },
  pip: { height: 4, borderRadius: 2 },
});
