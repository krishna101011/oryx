import assert from 'node:assert/strict';
import { test } from 'node:test';
import { parsePublicPageSlug, stripSchemePrefix } from './publicPageSlug';

test('parses a web pathname (leading slash) into its slug', () => {
  assert.equal(parsePublicPageSlug('/public/pages/abc123'), 'abc123');
});

test('parses a native deep-link remainder (no leading slash) into its slug', () => {
  assert.equal(parsePublicPageSlug('public/pages/abc123'), 'abc123');
});

test('tolerates an optional trailing slash', () => {
  assert.equal(parsePublicPageSlug('/public/pages/abc123/'), 'abc123');
});

test('decodes a percent-encoded slug', () => {
  assert.equal(parsePublicPageSlug('/public/pages/a%20b'), 'a b');
});

test('does not match an unrelated path', () => {
  assert.equal(parsePublicPageSlug('/settings/profile'), null);
  assert.equal(parsePublicPageSlug('/public/pages/'), null);
  assert.equal(parsePublicPageSlug('/public/pages'), null);
});

test('does not match a public/pages path carrying a nested segment', () => {
  assert.equal(parsePublicPageSlug('/public/pages/abc/extra'), null);
});

test('stripSchemePrefix removes the oryx:// scheme, leaving the raw path', () => {
  assert.equal(stripSchemePrefix('oryx://public/pages/abc123'), 'public/pages/abc123');
});

test('stripSchemePrefix is a no-op when there is no scheme', () => {
  assert.equal(stripSchemePrefix('public/pages/abc123'), 'public/pages/abc123');
});
