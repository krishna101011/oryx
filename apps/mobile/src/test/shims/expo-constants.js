/**
 * Test-only expo-constants shim (lib/push/expoPushEffects.ts, pulled in
 * transitively by store/thunks/auth.ts). See ./react-native.js.
 */
const ExecutionEnvironment = {
  Bare: 'bare',
  Standalone: 'standalone',
  StoreClient: 'storeClient',
};

module.exports = {
  __esModule: true,
  default: { executionEnvironment: ExecutionEnvironment.Bare, expoConfig: { version: '0.0.0-test' } },
  ExecutionEnvironment,
};
