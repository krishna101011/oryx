/**
 * Public Reader Rev 1 — the top-level branch decision, pulled out as a pure
 * function so it's provable by inspection AND by test that it structurally
 * cannot depend on auth state: its input type carries no auth.status, no
 * useMe() data, nothing from the auth store — only what usePublicPageRoute()
 * resolves from the URL. RootNavigator calls this BEFORE ever mounting
 * AuthenticatedRootNavigator (the only component that calls useMe()/
 * useAppSelector(auth)), so a public route can never touch auth state, not
 * just "happens not to" today.
 */
export type RootBranch = 'splash' | 'public' | 'auth-gated';

export interface PublicRouteState {
  resolved: boolean;
  isPublicRoute: boolean;
}

export function decideRootBranch(publicRoute: PublicRouteState): RootBranch {
  if (!publicRoute.resolved) return 'splash';
  if (publicRoute.isPublicRoute) return 'public';
  return 'auth-gated';
}
