/**
 * Rendered expand-on-press regression for the Automation Hub log rows
 * (design-foundation wave, AH-3). The log row's press-to-reveal detail block
 * (Channel/Trigger/Reason, wired in the "four decorative surfaces" wave) must
 * survive the row-anatomy rebuild — this renders the REAL AutomationHubScreen,
 * switches to the Log tab, presses a rendered row, and asserts the real
 * persisted detail lines appear, then disappear on the second press.
 *
 * Same harness rules as research/rowNavigation.test.tsx: register the
 * platform shims BEFORE anything importing react-native, and load every
 * runtime module through the same require function so react-query stays one
 * CJS instance (see that file's module note for the two traps).
 */
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { test } from 'node:test';
import type * as ReactNS from 'react';
import type * as ReactReduxNS from 'react-redux';
import type * as TestRendererNS from 'react-test-renderer';
import type { ReactTestRenderer } from 'react-test-renderer';
import type * as ReactQueryNS from '@tanstack/react-query';
import type * as StoreNS from '../../store';
import type * as HubScreenNS from './screens/AutomationHubScreen';
import type { AlertPreference, Automation, MeResponse } from '@oryx/shared-types';

const req = createRequire(import.meta.url);
req('../../test/shims/register.js');

(globalThis as Record<string, unknown>).IS_REACT_ACT_ENVIRONMENT = true;

/** Just enough of /auth/me for FeatureGate (flags) + useMe's workspace effect. */
const ME = {
  workspace: { id: 'ws-1' },
  flags: { ff_automation: true },
} as unknown as MeResponse;

const PREFS: AlertPreference[] = (
  ['security', 'system', 'verification', 'publishing'] as const
).flatMap((type) =>
  (['in_app', 'push', 'email'] as const).map(
    (channel) =>
      ({ type, channel, frequency: 'instant', quietHours: null }) as AlertPreference,
  ),
);

const LOG: Automation.AutomationLogResponse = {
  entries: [
    {
      id: 'f0000000-0000-0000-0000-000000000001',
      kind: 'dispatch',
      action: 'push_failed',
      eventType: 'intake.item.received',
      category: null,
      frequency: null,
      windowStart: null,
      windowEnd: null,
      activityInboxId: null,
      channel: 'push',
      detail: 'fcm: unregistered token',
      createdAt: '2026-07-15T10:00:00Z',
    },
    {
      id: 'f0000000-0000-0000-0000-000000000002',
      kind: 'dispatch',
      action: 'notification_created',
      eventType: 'content.published',
      category: null,
      frequency: null,
      windowStart: null,
      windowEnd: null,
      activityInboxId: null,
      channel: 'in_app',
      detail: null,
      createdAt: '2026-07-15T09:00:00Z',
    },
  ],
};

function renderHub() {
  const React = req('react') as typeof ReactNS;
  const { create, act } = req('react-test-renderer') as typeof TestRendererNS;
  const { Provider } = req('react-redux') as typeof ReactReduxNS;
  const { store } = req('../../store') as typeof StoreNS;
  const { QueryClient, QueryClientProvider } = req(
    '@tanstack/react-query',
  ) as typeof ReactQueryNS;
  const { AutomationHubScreen } = req(
    './screens/AutomationHubScreen',
  ) as typeof HubScreenNS;

  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: Infinity } },
  });
  qc.setQueryData(['me'], ME);
  qc.setQueryData(['alerts', 'preferences'], PREFS);
  qc.setQueryData(['automation', 'log'], LOG);

  let tree!: ReactTestRenderer;
  act(() => {
    tree = create(
      React.createElement(
        Provider,
        { store, children: undefined } as ReactReduxNS.ProviderProps,
        React.createElement(
          QueryClientProvider,
          { client: qc },
          React.createElement(AutomationHubScreen),
        ),
      ),
    );
  });

  const pressByLabel = (label: string) => {
    const matches = tree.root.findAll(
      (node) =>
        (node.type as unknown) === 'Pressable' &&
        node.props.accessibilityLabel === label &&
        typeof node.props.onPress === 'function',
    );
    assert.equal(matches.length, 1, `exactly one pressable labeled "${label}"`);
    act(() => {
      matches[0]!.props.onPress();
    });
  };

  const rendered = () => JSON.stringify(tree.toJSON());

  return { tree, act, pressByLabel, rendered };
}

test('pressing a rendered log row still reveals its real Channel/Trigger/Reason lines, and re-pressing hides them', () => {
  const { tree, act, pressByLabel, rendered } = renderHub();

  pressByLabel('Log'); // the Rules tab is the default; switch to the log
  assert.ok(rendered().includes('Push failed'), 'the failed row renders');
  assert.ok(rendered().includes('FAIL'), 'the failed row carries its outcome chip');
  assert.ok(
    !rendered().includes('fcm: unregistered token'),
    'detail lines start collapsed',
  );

  pressByLabel('Push failed — show details');
  const expanded = rendered();
  for (const fragment of ['Channel', 'Push', 'Trigger', 'Intake item received', 'Reason', 'fcm: unregistered token']) {
    assert.ok(expanded.includes(fragment), `expanded row must show "${fragment}"`);
  }

  pressByLabel('Push failed — hide details');
  assert.ok(
    !rendered().includes('fcm: unregistered token'),
    'the second press collapses the detail block again',
  );

  act(() => tree.unmount());
});

test('each log row expands independently — opening one leaves its neighbor collapsed', () => {
  const { tree, act, pressByLabel, rendered } = renderHub();

  pressByLabel('Log');
  pressByLabel('Push failed — show details');
  assert.ok(rendered().includes('fcm: unregistered token'));
  assert.ok(
    rendered().includes('Notification delivered — show details'),
    'the delivered row is still collapsed (its label still says show)',
  );

  act(() => tree.unmount());
});
