import { ComparisonResolveResult, ScreeningRun, ComparisonUrlSlot } from '../types';

export function searchFingerprint(url: string): string {
  if (!url) return '';
  try {
    const u = new URL(url);
    const saved = u.searchParams.get('saved_search') || '';
    const wmin = u.searchParams.get('workex_min') || '';
    const wmax = u.searchParams.get('workex_max') || '';
    if (saved) {
      return `saved:${saved}|${wmin}-${wmax}`;
    }
    const filterDate = u.searchParams.has('filter_date') ? '1' : '0';
    const lld = /lld|system\+design|system design/i.test(url) ? '1' : '0';
    return `raw|${filterDate}|${lld}|${wmin}-${wmax}|${url.slice(0, 120)}`;
  } catch {
    return url;
  }
}

function runConfig(run: ScreeningRun): Record<string, unknown> {
  if (!run?.configuration_snapshot) return {};
  try {
    return JSON.parse(run.configuration_snapshot) as Record<string, unknown>;
  } catch {
    return {};
  }
}

function urlFromRun(run: ScreeningRun): string {
  const u = runConfig(run).instahyre_search_url;
  return typeof u === 'string' ? u.trim() : '';
}

function diffExcludeId(run: ScreeningRun): number | null {
  const raw = runConfig(run).diff_exclude_run_id;
  if (typeof raw === 'number') return raw;
  if (typeof raw === 'string') {
    const n = parseInt(raw, 10);
    return Number.isNaN(n) ? null : n;
  }
  return null;
}

function findRunForExactUrl(runs: ScreeningRun[], url: string): ScreeningRun | undefined {
  const target = url.trim().replace(/\/$/, '');
  return runs.find((r) => urlFromRun(r).replace(/\/$/, '') === target);
}

export function findBaselineRunForUrl(runs: ScreeningRun[], url: string): ScreeningRun | undefined {
  const exact = findRunForExactUrl(runs, url);
  if (exact) return exact;
  const fp = searchFingerprint(url);
  if (!fp) return undefined;
  const matches = runs.filter((r) => searchFingerprint(urlFromRun(r)) === fp);
  if (!matches.length) return undefined;
  const baselines = matches.filter((r) => diffExcludeId(r) == null);
  const pool = baselines.length ? baselines : matches;
  const completed = pool.filter((r) => r.status === 'COMPLETED');
  const pick = (completed.length ? completed : pool).sort((a, b) => b.id - a.id);
  return pick[0];
}

export function buildMultiComparisonPlan(
  runs: ScreeningRun[],
  urls: string[]
): ComparisonResolveResult {
  const cleaned = urls.map((u) => u.trim()).filter((u) => u.startsWith('http'));
  if (cleaned.length < 2) {
    return {
      ready: false,
      message: 'Add at least 2 links (older lists first, newest last).',
    };
  }
  const slots: ComparisonUrlSlot[] = [];
  const excludeIds: number[] = [];
  const missingRefs: number[] = [];

  cleaned.forEach((u, i) => {
    const run = findBaselineRunForUrl(runs, u);
    const isTarget = i === cleaned.length - 1;
    slots.push({
      index: i + 1,
      url: u,
      run_id: run?.id ?? null,
      status: run?.status ?? null,
      in_db: Boolean(run),
      role: isTarget ? 'target' : 'reference',
    });
    if (!isTarget) {
      if (run) {
        if (!excludeIds.includes(run.id)) excludeIds.push(run.id);
      } else {
        missingRefs.push(i + 1);
      }
    }
  });

  if (missingRefs.length) {
    return {
      ready: false,
      message: `Link(s) ${missingRefs.join(', ')} not in DB. Run each as Unique search first, then compare.`,
      url_slots: slots,
      exclude_run_ids: excludeIds,
      target_url_index: cleaned.length,
    };
  }

  const target = cleaned[cleaned.length - 1];
  const targetRun = findRunForExactUrl(runs, target);
  const refLabel = excludeIds.map((id) => `#${id}`).join(', ');

  let message: string;
  if (targetRun) {
    message = `Target already run #${targetRun.id}. Re-diff vs ${refLabel} uses DB only (references not re-screened).`;
  } else {
    message = `Ready: screen the last link only; skip anyone in reference run(s) ${refLabel}.`;
  }

  return {
    ready: true,
    message,
    url_slots: slots,
    exclude_run_ids: excludeIds,
    target_url_index: cleaned.length,
    baseline_run_id: excludeIds[0] ?? null,
    new_existing_run_id: targetRun?.id ?? null,
    target_existing_run_id: targetRun?.id ?? null,
  };
}

/** @deprecated use buildMultiComparisonPlan */
export function buildComparisonPlanLocal(
  runs: ScreeningRun[],
  baselineUrl: string,
  newUrl: string
): ComparisonResolveResult {
  return buildMultiComparisonPlan(runs, [baselineUrl, newUrl]);
}