/**
 * Metro config for the monorepo.
 *
 * Two non-default things matter here:
 * 1. watchFolders includes the repo root so Metro picks up changes in packages/*
 * 2. nodeModulesPaths covers both the app and the repo root so hoisted
 *    workspace dependencies resolve correctly.
 */
const path = require('path');
const { getDefaultConfig } = require('expo/metro-config');

const projectRoot = __dirname;
const workspaceRoot = path.resolve(projectRoot, '..', '..');

const config = getDefaultConfig(projectRoot);

config.watchFolders = [workspaceRoot];
config.resolver.nodeModulesPaths = [
  path.resolve(projectRoot, 'node_modules'),
  path.resolve(workspaceRoot, 'node_modules'),
];

module.exports = config;
