import type { Session } from '@oryx/shared-types';

/**
 * "3 DEVICES" / "1 DEVICE" — the Sessions CardHeader sub. Pure so it is
 * testable under tsx --test (no react-native import); mirrors the
 * workspaceCountSub / deviceCountSub precedent (research/list.ts).
 */
export function deviceCountSub(sessions: Session[] | undefined): string | undefined {
  if (!sessions) return undefined;
  return `${sessions.length} ${sessions.length === 1 ? 'DEVICE' : 'DEVICES'}`;
}
