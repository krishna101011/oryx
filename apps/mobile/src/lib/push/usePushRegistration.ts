/**
 * Runs push registration from a user-meaningful surface — Phase 6 Wave C.
 *
 * Mounted on Settings → Notification Preferences (the screen where the user
 * is expressing interest in notifications, so the OS permission dialog has
 * context — deliberately NOT app launch, which iOS punishes). Also
 * re-registers if the OS rotates the token while the screen is alive.
 */
import { useEffect } from 'react';
import {
  expoPushEffects,
  expoPushEnvironment,
  subscribeToTokenRefresh,
} from './expoPushEffects';
import { syncPushRegistration } from './registration';

export function usePushRegistration(enabled: boolean): void {
  useEffect(() => {
    if (!enabled) return undefined;
    const env = expoPushEnvironment();
    // Web / Expo Go would be skipped inside sync anyway, but don't even
    // attach a native token listener where no raw token can exist.
    if (env.platform === 'web' || env.isExpoGo) return undefined;

    void syncPushRegistration(env, expoPushEffects(), { prompt: true });
    const sub = subscribeToTokenRefresh(() => {
      void syncPushRegistration(env, expoPushEffects(), { prompt: false });
    });
    return () => sub.remove();
  }, [enabled]);
}
