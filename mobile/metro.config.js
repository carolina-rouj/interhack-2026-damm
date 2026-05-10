const { getDefaultConfig } = require('expo/metro-config')

const config = getDefaultConfig(__dirname)

// Three.js ESM exports conflict with Expo's logging setup (__expoSetLogging).
// Disabling package exports forces Metro to resolve Three.js via its CJS build.
config.resolver.unstable_enablePackageExports = false

module.exports = config
