#!/usr/bin/env tsx
/**
 * gen-market-chart-bundle.ts — Phase 9 Wave B
 * (docs/PHASE_9_MARKET_TERMINAL_ARCHITECTURE.md §2/§4 Wave B).
 *
 * Reads the real, installed `lightweight-charts` standalone browser bundle
 * (apps/mobile/node_modules/lightweight-charts/dist/
 * lightweight-charts.standalone.production.js — a self-contained IIFE with
 * no external script dependencies, confirmed by inspection: it sets
 * `window.LightweightCharts` and has zero `<script src>`/import statements)
 * and emits it as a committed TypeScript string constant
 * (apps/mobile/src/modules/markets/charts/lightweightChartsBundle.generated.ts).
 *
 * WHY a committed string constant instead of a runtime CDN <script src> or a
 * Metro static asset: the native WebView bridge (MarketChartNative.tsx) needs
 * the charting library available inside the WebView's HTML with no runtime
 * network dependency — the same "real, working code, no live vendor
 * required" discipline this project already applies to
 * core/video_provider.py/core/market_data_provider.py, just for a bundled
 * library instead of a live vendor credential.
 *
 * Regenerate whenever apps/mobile/package.json's `lightweight-charts` version
 * changes: `tsx infra/scripts/gen-market-chart-bundle.ts`. Same
 * "committed mirror, not build-time generated" convention as
 * gen-pydantic.ts's target file — this script is a one-shot writer, not part
 * of any build or CI step.
 */
import { readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';

const REPO_ROOT = path.resolve(__dirname, '..', '..');
const SOURCE = path.join(
  REPO_ROOT,
  'apps/mobile/node_modules/lightweight-charts/dist/lightweight-charts.standalone.production.js',
);
const TARGET = path.join(
  REPO_ROOT,
  'apps/mobile/src/modules/markets/charts/lightweightChartsBundle.generated.ts',
);
const PACKAGE_JSON = path.join(REPO_ROOT, 'apps/mobile/package.json');

function main(): void {
  const source = readFileSync(SOURCE, 'utf-8');
  const version = JSON.parse(readFileSync(PACKAGE_JSON, 'utf-8')).dependencies['lightweight-charts'];

  const versionInFile = /Lightweight Charts™ v([\d.]+)/.exec(source)?.[1];
  if (versionInFile !== version) {
    throw new Error(
      `apps/mobile/package.json declares lightweight-charts@${version} but the ` +
        `installed standalone bundle's own header says v${versionInFile}. Run ` +
        `pnpm install first so the bundle on disk matches the declared version.`,
    );
  }

  const output = `/**
 * GENERATED — do not hand-edit. Regenerate with:
 *   tsx infra/scripts/gen-market-chart-bundle.ts
 *
 * The verbatim contents of lightweight-charts@${version}'s standalone
 * production browser bundle (dist/lightweight-charts.standalone.production.js),
 * embedded as a string so MarketChartNative's WebView HTML (marketChartHtml.ts)
 * can load the charting library with no runtime network dependency. Sets
 * \`window.LightweightCharts\` when evaluated as a <script>.
 */
export const LIGHTWEIGHT_CHARTS_STANDALONE_JS: string = ${JSON.stringify(source)};
`;

  writeFileSync(TARGET, output, 'utf-8');
  console.warn(`Wrote ${TARGET} (${(output.length / 1024).toFixed(1)} KB, lightweight-charts@${version})`);
}

main();
