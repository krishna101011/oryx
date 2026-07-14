/**
 * Test-only expo-blur shim (Card's BlurView). See ./react-native.js.
 */
const React = require('react');

const BlurView = React.forwardRef((props, ref) =>
  React.createElement('BlurView', { ...props, ref }),
);
BlurView.displayName = 'BlurView';

module.exports = { __esModule: true, BlurView };
