import React from 'react';
import { StyleSheet, TextInput, View, type TextInputProps } from 'react-native';
import { Spacer, Text, useTheme } from '@anant/design-system';

export interface AuthFormFieldProps extends Omit<TextInputProps, 'style'> {
  label: string;
  errorText?: string | null;
}

/** Single reusable input row for the auth + settings forms. */
export const AuthFormField: React.FC<AuthFormFieldProps> = ({
  label,
  errorText,
  ...rest
}) => {
  const t = useTheme();
  const hasError = Boolean(errorText);
  return (
    <View>
      <Text variant="caption" color="tertiary">
        {label.toUpperCase()}
      </Text>
      <Spacer size={1} />
      <TextInput
        placeholderTextColor={t.colors.text.tertiary}
        selectionColor={t.colors.accent.gold}
        autoCapitalize="none"
        autoCorrect={false}
        {...rest}
        style={[
          styles.input,
          {
            color: t.colors.text.primary,
            backgroundColor: t.colors.bg.card,
            borderColor: hasError ? t.colors.semantic.danger : t.colors.border.default,
          },
        ]}
      />
      {hasError ? (
        <>
          <Spacer size={1} />
          <Text variant="caption" color="danger">
            {errorText}
          </Text>
        </>
      ) : null}
    </View>
  );
};

const styles = StyleSheet.create({
  input: {
    height: 48,
    borderRadius: 10,
    borderWidth: 1,
    paddingHorizontal: 16,
    fontSize: 16,
  },
});
