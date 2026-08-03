/**
 * Public Reader Rev 1 — pure path parsing for the /public/pages/:slug route.
 *
 * Two callers share this: web reads `window.location.pathname` (leading
 * slash, e.g. "/public/pages/abc123"); native reads the remainder of the
 * initial deep-link URL after the "oryx://" scheme (no leading slash, e.g.
 * "public/pages/abc123") via stripSchemePrefix. Both are tolerant of an
 * optional trailing slash.
 */
export function parsePublicPageSlug(path: string): string | null {
  const match = path.match(/^\/?public\/pages\/([^/?#]+)\/?$/);
  return match ? decodeURIComponent(match[1]!) : null;
}

/** "oryx://public/pages/abc" -> "public/pages/abc" (no-op if there's no scheme). */
export function stripSchemePrefix(url: string): string {
  const idx = url.indexOf('://');
  return idx === -1 ? url : url.slice(idx + 3);
}
