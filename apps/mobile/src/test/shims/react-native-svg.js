/**
 * Test-only react-native-svg shim — inert host elements so design-system
 * glyphs (Candles, Card texture, GensparkIcon, HornMark, Spark) render under
 * react-test-renderer. See ./react-native.js for the rationale.
 */
const React = require('react');

const host = (type) => {
  const C = React.forwardRef((props, ref) =>
    React.createElement(type, { ...props, ref }),
  );
  C.displayName = type;
  return C;
};

const Svg = host('Svg');

module.exports = {
  __esModule: true,
  default: Svg,
  Svg,
  G: host('G'),
  Line: host('Line'),
  Rect: host('Rect'),
  Text: host('SvgText'),
  Circle: host('Circle'),
  Path: host('Path'),
  Defs: host('Defs'),
  LinearGradient: host('LinearGradient'),
  Stop: host('Stop'),
  Polyline: host('Polyline'),
};
