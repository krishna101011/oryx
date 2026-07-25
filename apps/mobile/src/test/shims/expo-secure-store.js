/**
 * Test-only expo-secure-store shim (lib/secure-store.ts, pulled in transitively
 * by store/thunks/auth.ts). See ./react-native.js. The shimmed Platform.OS is
 * 'web', so secure-store.ts's real code path never calls these — they only
 * need to exist so the eager `import * as SecureStore` doesn't load the real
 * native module.
 */
module.exports = {
  __esModule: true,
  getItemAsync: async () => null,
  setItemAsync: async () => {},
  deleteItemAsync: async () => {},
};
