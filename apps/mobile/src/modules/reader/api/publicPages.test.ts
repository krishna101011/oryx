/**
 * Isolation proof (direction 1 — "an authenticated user's own session must
 * never leak into a public page request"): fetchPublicPage is asserted to
 * send NO Authorization header and NO X-Workspace-Id header, even though the
 * fake backend below would happily tell us if one showed up. This module
 * calls the global `fetch` directly instead of the shared `apiClient()`
 * singleton specifically so a signed-in visitor's bearer token can never
 * ride along — see the module header comment.
 */
import assert from 'node:assert/strict';
import { test } from 'node:test';
import { PublicPageNotFoundError, fetchPublicPage } from './publicPages';

function withFakeFetch<T>(
  handler: (input: unknown, init?: RequestInit) => Response,
  run: () => Promise<T>,
): Promise<T> {
  const original = globalThis.fetch;
  const calls: { input: unknown; init?: RequestInit }[] = [];
  (globalThis as unknown as { fetch: typeof fetch }).fetch = (async (
    input: unknown,
    init?: RequestInit,
  ) => {
    calls.push({ input, init });
    return handler(input, init);
  }) as unknown as typeof fetch;
  (globalThis as unknown as { __fetchCalls: unknown }).__fetchCalls = calls;
  return run().finally(() => {
    (globalThis as unknown as { fetch: typeof fetch }).fetch = original;
  });
}

function lastCall(): { input: unknown; init?: RequestInit } {
  const calls = (globalThis as unknown as { __fetchCalls: { input: unknown; init?: RequestInit }[] })
    .__fetchCalls;
  return calls[calls.length - 1]!;
}

const json = (data: unknown, status = 200): Response =>
  new Response(JSON.stringify(data), { status, headers: { 'content-type': 'application/json' } });

test('a successful fetch never sends Authorization or X-Workspace-Id headers', async () => {
  await withFakeFetch(
    () =>
      json({
        data: {
          content: 'Hello.',
          publishedAt: '2026-08-01T00:00:00Z',
          citations: [],
        },
      }),
    async () => {
      await fetchPublicPage('abc123');
      const { init } = lastCall();
      const headers = new Headers(init?.headers);
      assert.equal(headers.has('authorization'), false, 'no bearer token ever attached');
      assert.equal(headers.has('x-workspace-id'), false, 'no workspace header ever attached');
    },
  );
});

test('the request targets the real single combined endpoint — exactly one call per page view', async () => {
  await withFakeFetch(
    () => json({ data: { content: 'Hi.', publishedAt: '2026-08-01T00:00:00Z', citations: [] } }),
    async () => {
      await fetchPublicPage('my-slug');
      const calls = (
        globalThis as unknown as { __fetchCalls: unknown[] }
      ).__fetchCalls;
      assert.equal(calls.length, 1, 'one HTTP call per page view');
      const { input } = lastCall();
      assert.match(String(input), /\/public\/pages\/my-slug$/);
    },
  );
});

test('unwraps the envelope: content, publishedAt, and citations all come back verbatim', async () => {
  const citation = {
    headline: 'Acme raised $5B',
    epistemicType: 'fact' as const,
    confidenceScore: 0.9,
    scoringVersion: 1,
    snapshottedAt: '2026-07-09T10:00:00Z',
  };
  await withFakeFetch(
    () =>
      json({
        data: {
          content: 'First.\n\nSecond.',
          publishedAt: '2026-08-01T12:00:00Z',
          citations: [citation],
        },
      }),
    async () => {
      const page = await fetchPublicPage('abc123');
      assert.equal(page.content, 'First.\n\nSecond.');
      assert.equal(page.publishedAt, '2026-08-01T12:00:00Z');
      assert.deepEqual(page.citations, [citation]);
    },
  );
});

test('a 404 throws PublicPageNotFoundError, distinguishable from any other failure', async () => {
  await withFakeFetch(
    () => json({ error: { code: 'NOT_FOUND', message: 'Page not found', requestId: 'rid' } }, 404),
    async () => {
      await assert.rejects(() => fetchPublicPage('unknown-slug'), PublicPageNotFoundError);
    },
  );
});

test('a rate-limited (429) response throws a distinct, non-404 error', async () => {
  await withFakeFetch(
    () =>
      json(
        { error: { code: 'PUBLIC_PAGE_RATE_LIMITED', message: 'Too many requests', requestId: 'rid' } },
        429,
      ),
    async () => {
      await assert.rejects(async () => {
        try {
          await fetchPublicPage('abc123');
        } catch (e) {
          assert.equal(e instanceof PublicPageNotFoundError, false);
          throw e;
        }
      }, /Too many requests/);
    },
  );
});
