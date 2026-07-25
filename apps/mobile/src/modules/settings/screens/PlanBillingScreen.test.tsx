/**
 * PlanBillingScreen — real subscribe-button press against a fake backend
 * returning the real PAYMENT_PROVIDER_UNAVAILABLE envelope (exactly what
 * the live endpoint returns today, no live Stripe/Razorpay keys). Proves
 * the screen renders the honest "not live yet" message — never a crash,
 * never a fake success — same harness rules as
 * intake/catalogActivationWiring.test.tsx: register shims first, monkey-
 * patch global.fetch, load every module through the same require so
 * react-query stays one CJS instance.
 */
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { test } from 'node:test';
import type * as ReactNS from 'react';
import type * as TestRendererNS from 'react-test-renderer';
import type { ReactTestRenderer } from 'react-test-renderer';
import type * as ReactQueryNS from '@tanstack/react-query';
import type * as ClientNS from '../../../lib/api/client';
import type * as PlanBillingScreenNS from './PlanBillingScreen';
import type { PlansResponse, SubscriptionSummary } from '@oryx/shared-types';

const req = createRequire(import.meta.url);
req('../../../test/shims/register.js');

(globalThis as Record<string, unknown>).IS_REACT_ACT_ENVIRONMENT = true;

const PLANS: PlansResponse = {
  plans: [
    { planId: 'focus_monthly_usd', tier: 'focus', cadence: 'monthly', currency: 'USD', amount: 19.99 },
    { planId: 'focus_quarterly_usd', tier: 'focus', cadence: 'quarterly', currency: 'USD', amount: 53.99 },
    { planId: 'focus_yearly_usd', tier: 'focus', cadence: 'yearly', currency: 'USD', amount: 199.99 },
    { planId: 'clarity_monthly_usd', tier: 'clarity', cadence: 'monthly', currency: 'USD', amount: 44.99 },
    { planId: 'clarity_quarterly_usd', tier: 'clarity', cadence: 'quarterly', currency: 'USD', amount: 121.99 },
    { planId: 'clarity_yearly_usd', tier: 'clarity', cadence: 'yearly', currency: 'USD', amount: 449.99 },
    { planId: 'vision_monthly_usd', tier: 'vision', cadence: 'monthly', currency: 'USD', amount: 99.99 },
    { planId: 'vision_quarterly_usd', tier: 'vision', cadence: 'quarterly', currency: 'USD', amount: 269.99 },
    { planId: 'vision_yearly_usd', tier: 'vision', cadence: 'yearly', currency: 'USD', amount: 999.99 },
  ],
};

const SUMMARY: SubscriptionSummary = { currentPlan: 'glimpse', subscription: null };

function makeFakeBackend() {
  const calls: { method: string; path: string }[] = [];

  const json = (data: unknown, status = 200): Response =>
    new Response(JSON.stringify(data), {
      status,
      headers: { 'content-type': 'application/json' },
    });

  const fetchImpl = async (input: unknown, init?: RequestInit): Promise<Response> => {
    const full = String(input);
    const path = full.replace(/^https?:\/\/[^/]+\/v1/, '');
    const method = (init?.method ?? 'GET').toUpperCase();
    calls.push({ method, path });

    if (method === 'POST' && path === '/billing/subscribe') {
      // The exact real envelope services/billing/router.py's subscribe
      // endpoint returns today (PaymentProviderError -> 503).
      return json(
        {
          error: {
            code: 'PAYMENT_PROVIDER_UNAVAILABLE',
            message: "Payments aren't configured yet",
            requestId: 'test-request-id',
            details: { provider: 'stripe', kind: 'permanent', reason: 'STRIPE_API_KEY is not configured' },
          },
        },
        503,
      );
    }
    throw new Error(`unhandled fake fetch: ${method} ${path}`);
  };

  return { fetchImpl, calls };
}

function renderScreen() {
  const backend = makeFakeBackend();
  const originalFetch = globalThis.fetch;
  (globalThis as unknown as { fetch: typeof fetch }).fetch = backend.fetchImpl as unknown as typeof fetch;

  const { configureApiClient } = req('../../../lib/api/client') as typeof ClientNS;
  configureApiClient({
    baseUrl: 'http://test.local/v1',
    getAccessToken: () => 'test-token',
    getWorkspaceId: () => 'ws-1',
    refreshAccessToken: async () => null,
  });

  const React = req('react') as typeof ReactNS;
  const { create, act } = req('react-test-renderer') as typeof TestRendererNS;
  const { QueryClient, QueryClientProvider } = req(
    '@tanstack/react-query',
  ) as typeof ReactQueryNS;
  const { PlanBillingScreen } = req('./PlanBillingScreen') as typeof PlanBillingScreenNS;

  const qc = new QueryClient({
    defaultOptions: {
      queries: { retry: false, staleTime: Infinity },
      mutations: { retry: false },
    },
  });
  qc.setQueryData(['billing', 'plans'], PLANS);
  qc.setQueryData(['billing', 'subscription'], SUMMARY);

  let tree!: ReactTestRenderer;
  act(() => {
    tree = create(
      React.createElement(QueryClientProvider, { client: qc }, React.createElement(PlanBillingScreen)),
    );
  });

  const pressByTestId = (testId: string) => {
    const matches = tree.root.findAll(
      (node) =>
        (node.type as unknown) === 'Pressable' &&
        node.props.testID === testId &&
        typeof node.props.onPress === 'function',
    );
    assert.equal(matches.length, 1, `exactly one pressable with testID "${testId}"`);
    act(() => {
      matches[0]!.props.onPress();
    });
  };

  const flush = async () => {
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 0));
      await new Promise((resolve) => setTimeout(resolve, 0));
    });
  };

  const rendered = () => JSON.stringify(tree.toJSON());
  const restore = () => {
    (globalThis as unknown as { fetch: typeof fetch }).fetch = originalFetch;
  };

  return { tree, act, pressByTestId, flush, rendered, backend, restore };
}

test('renders the real plan catalog and current tier', () => {
  const { tree, rendered, restore } = renderScreen();
  assert.ok(rendered().includes('Glimpse'), 'shows the real current tier');
  assert.ok(rendered().includes('19.99'), 'shows a real catalog price');
  assert.ok(rendered().includes('No active subscription'));
  restore();
  tree.unmount();
});

test('pressing Subscribe surfaces the honest not-configured message, never a crash or fake success', async () => {
  const { tree, pressByTestId, flush, rendered, backend, restore } = renderScreen();

  assert.ok(!rendered().includes("aren't live yet"), 'no premature unavailable message');

  pressByTestId('subscribe-focus_monthly_usd');
  await flush();

  assert.equal(backend.calls.length, 1);
  assert.equal(backend.calls[0]!.path, '/billing/subscribe');

  const after = rendered();
  assert.ok(
    after.includes("Payments aren't live yet"),
    'the real honest unavailable message renders',
  );
  assert.ok(!after.includes('undefined'), 'no crash artifact leaked into the render');

  restore();
  tree.unmount();
});

test('a second subscribe attempt on a different plan still shows the honest message, not a stuck loading state', async () => {
  const { tree, pressByTestId, flush, rendered, restore } = renderScreen();

  pressByTestId('subscribe-vision_yearly_usd');
  await flush();

  assert.ok(rendered().includes("Payments aren't live yet"));
  assert.ok(!rendered().includes('ActivityIndicator'), 'loading state clears after settling');

  restore();
  tree.unmount();
});
