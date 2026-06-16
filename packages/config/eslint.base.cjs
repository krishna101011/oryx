/**
 * Shared ESLint base for ORYX workspaces.
 * Each package extends this and adds environment-specific overrides.
 */
module.exports = {
  root: false,
  env: {
    es2022: true,
    node: true,
  },
  parser: '@typescript-eslint/parser',
  parserOptions: {
    ecmaVersion: 2022,
    sourceType: 'module',
  },
  plugins: ['@typescript-eslint'],
  extends: [
    'eslint:recommended',
    'plugin:@typescript-eslint/recommended',
    'prettier',
  ],
  rules: {
    // Enforce design-token usage — no inline hex colors.
    'no-restricted-syntax': [
      'error',
      {
        selector: "Literal[value=/^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$/]",
        message:
          'Inline hex color detected. Use tokens from @oryx/design-system instead.',
      },
    ],

    // Hygiene
    '@typescript-eslint/consistent-type-imports': 'error',
    '@typescript-eslint/no-unused-vars': [
      'error',
      { argsIgnorePattern: '^_', varsIgnorePattern: '^_' },
    ],
    '@typescript-eslint/no-explicit-any': 'warn',
    'no-console': ['warn', { allow: ['warn', 'error'] }],

    // Import order
    'sort-imports': ['warn', { ignoreDeclarationSort: true }],
  },
  overrides: [
    {
      // Matched relative to the linted package's CWD (each package runs
      // `eslint src`), so the repo-rooted form never fired.
      files: ['**/src/tokens/**/*'],
      rules: {
        // The design system IS allowed to define hex values.
        'no-restricted-syntax': 'off',
      },
    },
  ],
};
