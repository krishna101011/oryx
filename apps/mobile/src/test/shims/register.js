/**
 * Aliases the native platform packages to the test shims in this directory,
 * for BOTH module systems tsx might use (CJS require today; ESM hooks kept as
 * a forward guard). Load this (via createRequire) at the very top of any test
 * that renders real components, BEFORE importing anything that touches
 * react-native. Product code never imports this.
 */
const Module = require('node:module');
const path = require('node:path');
const { pathToFileURL } = require('node:url');

const SHIMS = {
  'react-native': path.join(__dirname, 'react-native.js'),
  'react-native-svg': path.join(__dirname, 'react-native-svg.js'),
  'react-native-safe-area-context': path.join(
    __dirname,
    'react-native-safe-area-context.js',
  ),
  'expo-blur': path.join(__dirname, 'expo-blur.js'),
  'lucide-react-native': path.join(__dirname, 'lucide-react-native.js'),
};

const hasShim = (specifier) =>
  Object.prototype.hasOwnProperty.call(SHIMS, specifier);

// CJS path — tsx compiles this repo's TS to CJS (no "type": "module").
const originalResolve = Module._resolveFilename;
Module._resolveFilename = function resolveWithShims(request, ...rest) {
  if (hasShim(request)) return SHIMS[request];
  return originalResolve.call(this, request, ...rest);
};

// ESM path — harmless no-op under CJS, correct if tsx ever goes ESM here.
if (typeof Module.registerHooks === 'function') {
  Module.registerHooks({
    resolve(specifier, context, nextResolve) {
      if (hasShim(specifier)) {
        return { url: pathToFileURL(SHIMS[specifier]).href, shortCircuit: true };
      }
      return nextResolve(specifier, context);
    },
  });
}
