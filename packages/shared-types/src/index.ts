// ---- Common ----
export * from './common';

// ---- Phase 2 domains ----
export * from './accounts';
export * from './profiles';
export * from './workspaces';
export * from './preferences';
export * from './sources';
export * from './sessions';
export * from './auth';
export * from './activity';
export * from './alerts';
export * from './feature-flags';
export * from './onboarding';

// ---- Phase 1 compat ----
export * from './users';

// ---- Later-phase domain stubs (empty in Phase 2) ----
export * from './intake';
// ---- Phase 3 intake (Batch 1) ----
export * from './intake-sources';
export * from './intake-events';
export * from './intake-webhooks';

// ---- Phase 4 Wave A ----
export * from './claims';

// ---- Phase 4 Wave B ----
export * from './evidence';

export * as Verification from './verification';
export * as Research from './research';
export * as Content from './content';
export * as Publishing from './publishing';
export * as Automation from './automation';
export * as Analytics from './analytics';
export * as Training from './training';
