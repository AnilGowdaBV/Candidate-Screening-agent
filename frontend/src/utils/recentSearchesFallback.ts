import { RecentSearchSummary, ScreeningRun } from '../types';
import { searchFingerprint } from './comparisonPlan';

function runConfig(run: ScreeningRun): Record<string, unknown> {
  if (!run.configuration_snapshot) return {};
  try {
    return JSON.parse(run.configuration_snapshot) as Record<string, unknown>;
  } catch {
    return {};
  }
}

function shortenInstahyreUrl(url: string): string {
  if (!url) return '—';
  try {
    const u = new URL(url);
    const bits: string[] = [];
    const saved = u.searchParams.get('saved_search');
    if (saved) bits.push(`saved #${saved}`);
    if (u.searchParams.has('filter_date')) bits.push('filter_date');
    if (/lld|system\+design|system design/i.test(url)) bits.push('LLD');
    const wmin = u.searchParams.get('workex_min') || '';
    const wmax = u.searchParams.get('workex_max') || '';
    if (wmin || wmax) bits.push(`exp ${wmin}-${wmax}y`);
    if (bits.length) return bits.join(' · ');
  } catch {
    /* ignore */
  }
  return url.length > 56 ? `${url.slice(0, 56)}…` : url;
}

/** When /recent-searches is missing (older Render build), build rows from GET /runs. */
export function buildRecentSearchesFromRuns(
  runs: ScreeningRun[],
  technology: string,
  limit = 20
): RecentSearchSummary[] {
  const ordered = [...runs].sort((a, b) => b.id - a.id);
  const out: RecentSearchSummary[] = [];
  const seen = new Set<string>();

  for (const run of ordered) {
    const cfg = runConfig(run);
    const url = (cfg.instahyre_search_url as string) || '';
    const fp = searchFingerprint(url) || `run-${run.id}`;
    if (seen.has(fp)) continue;
    seen.add(fp);

    const tech = ((cfg.technology as string) || technology).toLowerCase();
    out.push({
      run_id: run.id,
      technology: tech,
      status: run.status,
      started_at: run.started_at,
      instahyre_search_short: shortenInstahyreUrl(url),
      instahyre_search_url: url || null,
      google_sheet_tab: `Run #${run.id}`,
      google_sheet_url: '#',
      is_comparison: false,
      comparison: null,
    });
    if (out.length >= limit) break;
  }
  return out;
}