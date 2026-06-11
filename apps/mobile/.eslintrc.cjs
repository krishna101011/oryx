module.exports = {
  root: true,
  extends: ['../../packages/config/eslint.base.cjs'],
  plugins: ['react-native'],
  env: { 'react-native/react-native': true, browser: true },
  settings: {
    react: { version: 'detect' },
  },
};
