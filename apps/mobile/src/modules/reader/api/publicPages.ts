/**
 * Public Reader Rev 1 — GET /public/pages/{slug}.
 *
 * Deliberately bypasses the shared `apiClient()` singleton and calls `fetch`
 * directly with no Authorization / X-Workspace-Id headers. This endpoint is
 * genuinely unauthenticated on the backend (no CurrentPrincipal dependency,
 * services/reader/router.py) — a visitor who happens to already have an
 * authenticated session elsewhere in the app must never have that session
 * ride along on this request. One real HTTP call combines the page content
 * and its citations (services/reader/router.py calls get_by_slug +
 * list_citations internally and returns both in one envelope), so this is
 * the only network call a page view makes.
 */
import type { EpistemicType } from '@oryx/shared-types';

const DEFAULT_BASE_URL =
  process.env.EXPO_PUBLIC_API_BASE_URL ?? 'http://localhost:8000/v1';

export interface PublicPageCitation {
  headline: string;
  epistemicType: EpistemicType;
  confidenceScore: number | null;
  scoringVersion: number;
  snapshottedAt: string;
}

export interface PublicPageResponse {
  content: string;
  publishedAt: string;
  citations: PublicPageCitation[];
}

export class PublicPageNotFoundError extends Error {
  constructor(slug: string) {
    super(`Public page not found: ${slug}`);
    this.name = 'PublicPageNotFoundError';
  }
}

export async function fetchPublicPage(slug: string): Promise<PublicPageResponse> {
  const res = await fetch(
    `${DEFAULT_BASE_URL}/public/pages/${encodeURIComponent(slug)}`,
    { method: 'GET', headers: { Accept: 'application/json' } },
  );

  if (res.status === 404) {
    throw new PublicPageNotFoundError(slug);
  }

  const text = await res.text();
  const parsed = text.length > 0 ? JSON.parse(text) : undefined;

  if (!res.ok) {
    const message =
      parsed && typeof parsed === 'object' && 'error' in parsed
        ? (parsed as { error: { message: string } }).error.message
        : `HTTP ${res.status}`;
    throw new Error(message);
  }

  return (parsed && typeof parsed === 'object' && 'data' in parsed
    ? (parsed as { data: PublicPageResponse }).data
    : parsed) as PublicPageResponse;
}
