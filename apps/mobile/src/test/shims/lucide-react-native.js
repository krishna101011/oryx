/**
 * Test-only lucide-react-native shim. Only the glyphs the rendered screens
 * actually reference need to exist; design-system Icon renders null for any
 * name that resolves to undefined, which is harmless in tests.
 * See ./react-native.js for the rationale.
 */
const React = require('react');

const glyph = (name) => {
  const C = (props) => React.createElement(name, props);
  C.displayName = name;
  return C;
};

module.exports = {
  __esModule: true,
  ChevronRight: glyph('ChevronRight'),
};
