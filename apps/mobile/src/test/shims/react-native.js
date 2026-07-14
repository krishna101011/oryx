/**
 * Test-only react-native shim (rowNavigation.test.tsx harness).
 *
 * The frontend suite runs under `tsx --test` in plain Node, where the real
 * react-native package cannot load (Flow-typed source, native modules). This
 * shim replaces ONLY the platform layer with inert host components so that
 * real ORYX components (design-system primitives, WorkspaceCard, screens) can
 * render through react-test-renderer. Behavior-free by design: every host
 * component just forwards its props, so tests exercise the app's own wiring,
 * not this file.
 *
 * Wired up by ./register.js — never imported by product code.
 */
const React = require('react');

/** A host component that renders as a named host element with its props. */
const host = (type) => {
  const C = React.forwardRef((props, ref) =>
    React.createElement(type, { ...props, ref }),
  );
  C.displayName = type;
  return C;
};

const flatten = (style) => {
  if (!style) return {};
  if (Array.isArray(style)) {
    return Object.assign({}, ...style.map((s) => flatten(s)));
  }
  return style;
};

class AnimatedValue {
  constructor(value) {
    this._value = value;
  }
  setValue(value) {
    this._value = value;
  }
  interpolate() {
    return this;
  }
}

const finished = (cb) => cb && cb({ finished: true });

module.exports = {
  __esModule: true,
  View: host('View'),
  Text: host('Text'),
  ScrollView: host('ScrollView'),
  TextInput: host('TextInput'),
  StatusBar: host('StatusBar'),
  ActivityIndicator: host('ActivityIndicator'),
  Pressable: host('Pressable'),
  TouchableOpacity: host('TouchableOpacity'),
  Image: host('Image'),
  Animated: {
    View: host('Animated.View'),
    Text: host('Animated.Text'),
    Value: AnimatedValue,
    timing: () => ({ start: finished, stop() {} }),
    sequence: () => ({ start: finished, stop() {} }),
    parallel: () => ({ start: finished, stop() {} }),
    loop: () => ({ start() {}, stop() {} }),
  },
  Easing: {
    linear: (t) => t,
    ease: (t) => t,
    quad: (t) => t,
    cubic: (t) => t,
    in: (f) => f,
    out: (f) => f,
    inOut: (f) => f,
    bezier: () => (t) => t,
  },
  StyleSheet: {
    create: (styles) => styles,
    flatten,
    compose: (a, b) => [a, b],
    hairlineWidth: 1,
    absoluteFill: { position: 'absolute', top: 0, right: 0, bottom: 0, left: 0 },
    absoluteFillObject: { position: 'absolute', top: 0, right: 0, bottom: 0, left: 0 },
  },
  Platform: {
    OS: 'web',
    Version: 0,
    isTesting: true,
    select: (spec) => ('web' in spec ? spec.web : spec.default),
  },
  Dimensions: {
    get: () => ({ width: 1280, height: 800, scale: 2, fontScale: 1 }),
    addEventListener: () => ({ remove() {} }),
    removeEventListener() {},
  },
  useWindowDimensions: () => ({ width: 1280, height: 800, scale: 2, fontScale: 1 }),
  PixelRatio: {
    get: () => 2,
    getFontScale: () => 1,
    roundToNearestPixel: (n) => n,
  },
  I18nManager: { isRTL: false, getConstants: () => ({ isRTL: false }) },
  Linking: {
    addEventListener: () => ({ remove() {} }),
    removeEventListener() {},
    getInitialURL: async () => null,
    openURL: async () => {},
    canOpenURL: async () => false,
  },
  BackHandler: {
    addEventListener: () => ({ remove() {} }),
    removeEventListener() {},
    exitApp() {},
  },
  AppState: {
    currentState: 'active',
    addEventListener: () => ({ remove() {} }),
  },
  Keyboard: {
    dismiss() {},
    addListener: () => ({ remove() {} }),
  },
  Alert: { alert() {} },
  DeviceEventEmitter: { addListener: () => ({ remove() {} }) },
  NativeModules: {},
  requireNativeComponent: (name) => host(name),
};
