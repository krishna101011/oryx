import { useEffect, useState } from 'react';
import { Linking, Platform } from 'react-native';
import { parsePublicPageSlug, stripSchemePrefix } from '../modules/reader/publicPageSlug';
import type { PublicRouteState } from './rootNavigatorDecision';

function resolveWebRoute(): PublicRouteState {
  const slug = parsePublicPageSlug(window.location.pathname);
  return { resolved: true, isPublicRoute: slug !== null };
}

/**
 * Answers "is the app's initial route a public reader link" from the URL —
 * web resolves synchronously from window.location; native resolves async
 * from the initial deep-link URL (Linking.getInitialURL never fires again
 * after first mount, matching how a cold-launched deep link works). Only
 * answers the routing question: it never reads auth.status, never calls
 * useMe() — see rootNavigatorDecision.ts for why that separation matters.
 */
export function usePublicPageRoute(): PublicRouteState {
  const [state, setState] = useState<PublicRouteState>(() =>
    Platform.OS === 'web' && typeof window !== 'undefined'
      ? resolveWebRoute()
      : { resolved: false, isPublicRoute: false },
  );

  useEffect(() => {
    if (Platform.OS === 'web') return;
    let cancelled = false;
    Linking.getInitialURL().then((url) => {
      if (cancelled) return;
      const slug = url ? parsePublicPageSlug(stripSchemePrefix(url)) : null;
      setState({ resolved: true, isPublicRoute: slug !== null });
    });
    return () => {
      cancelled = true;
    };
  }, []);

  return state;
}
