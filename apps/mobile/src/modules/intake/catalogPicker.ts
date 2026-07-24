import type { Focus, IntakeSource, SourceCatalogEntry } from '@oryx/shared-types';

/**
 * the_block has no confirmed real feed URL yet (source_catalog.url is still
 * its homepage, per migration 0026/0027's own standard) — excluded from the
 * picker until a real feed exists, rather than offering a tile that would
 * create a decorative, permanently-failing intake source.
 */
const UNACTIVATABLE_CATALOG_KEYS = new Set<string>(['the_block']);

export function activatableCatalogEntries(
  catalog: SourceCatalogEntry[],
): SourceCatalogEntry[] {
  return catalog.filter((entry) => !UNACTIVATABLE_CATALOG_KEYS.has(entry.key));
}

export interface CatalogSection {
  title: string;
  entries: SourceCatalogEntry[];
}

/** Real sections only — a focus with zero activatable entries gets no section. */
export function groupCatalogBySection(catalog: SourceCatalogEntry[]): CatalogSection[] {
  const entries = activatableCatalogEntries(catalog);
  const crypto = entries.filter((e) => e.focus === 'crypto');
  const markets = entries.filter((e) => e.focus === 'markets' || e.focus === 'both');
  const sections: CatalogSection[] = [];
  if (crypto.length > 0) sections.push({ title: 'Crypto', entries: crypto });
  if (markets.length > 0) sections.push({ title: 'Markets', entries: markets });
  return sections;
}

export function filterCatalogByFocus(
  catalog: SourceCatalogEntry[],
  focus: Focus,
): SourceCatalogEntry[] {
  if (focus === 'both') return catalog;
  return catalog.filter((e) => e.focus === focus || e.focus === 'both');
}

/** origin_catalog_key -> the real intake_sources row activating it, if any. */
export type CatalogActivationMap = Record<string, IntakeSource>;

export function buildCatalogActivationMap(sources: IntakeSource[]): CatalogActivationMap {
  const map: CatalogActivationMap = {};
  for (const s of sources) {
    if (s.originKind === 'catalog' && s.originCatalogKey) {
      map[s.originCatalogKey] = s;
    }
  }
  return map;
}

export function isCatalogKeyEnabled(map: CatalogActivationMap, key: string): boolean {
  return map[key]?.enabled === true;
}

export type ToggleAction =
  | { kind: 'create'; catalogKey: string }
  | { kind: 'patch'; sourceId: string; enabled: boolean };

/**
 * Decides whether enabling/disabling a tile must create the FIRST real
 * intake_sources row for this catalog key (origin_kind='catalog') or just
 * flip `enabled` on the one that already exists — never the WorkspaceSource
 * toggle, which has no real pipeline effect.
 */
export function resolveToggleAction(
  key: string,
  map: CatalogActivationMap,
): ToggleAction {
  const existing = map[key];
  if (!existing) {
    return { kind: 'create', catalogKey: key };
  }
  return { kind: 'patch', sourceId: existing.id, enabled: !existing.enabled };
}

/** Activatable catalog keys with no real intake_sources row yet. */
export function keysMissingActivation(
  catalog: SourceCatalogEntry[],
  map: CatalogActivationMap,
): string[] {
  return activatableCatalogEntries(catalog)
    .map((e) => e.key)
    .filter((key) => !map[key]);
}
