/**
 * Test-only expo-notifications shim (lib/push/expoPushEffects.ts, pulled in
 * transitively by store/thunks/auth.ts). See ./react-native.js.
 */
module.exports = {
  __esModule: true,
  getPermissionsAsync: async () => ({ status: 'undetermined', canAskAgain: true }),
  requestPermissionsAsync: async () => ({ status: 'undetermined', canAskAgain: true }),
  getDevicePushTokenAsync: async () => ({ data: 'test-token', type: 'expo' }),
  addPushTokenListener: () => ({ remove() {} }),
};
