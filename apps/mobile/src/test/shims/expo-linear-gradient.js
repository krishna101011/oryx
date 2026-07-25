/**
 * Test-only expo-linear-gradient shim (WebSidebar's foot/avatar gradients).
 * See ./react-native.js.
 */
const React = require('react');

const LinearGradient = React.forwardRef((props, ref) =>
  React.createElement('LinearGradient', { ...props, ref }),
);
LinearGradient.displayName = 'LinearGradient';

module.exports = { __esModule: true, LinearGradient };
