/**
 * Test-only react-native-safe-area-context shim. See ./react-native.js.
 */
const React = require('react');

const host = (type) => {
  const C = React.forwardRef((props, ref) =>
    React.createElement(type, { ...props, ref }),
  );
  C.displayName = type;
  return C;
};

const ZERO = { top: 0, right: 0, bottom: 0, left: 0 };

module.exports = {
  __esModule: true,
  SafeAreaView: host('SafeAreaView'),
  SafeAreaProvider: host('SafeAreaProvider'),
  useSafeAreaInsets: () => ZERO,
  useSafeAreaFrame: () => ({ x: 0, y: 0, width: 1280, height: 800 }),
  initialWindowMetrics: null,
};
