/**
 * Phase 2: identity is now called Account. This file preserves
 * the Phase 1 type names for any in-flight consumer.
 * New code should import from './accounts'.
 */
export type { Account as User, AccountStatus as UserStatus } from './accounts';
