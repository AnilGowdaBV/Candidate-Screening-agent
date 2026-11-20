import {
  SystemStatus,
  DashboardMetrics,
  CandidateListResponse,
  ScreeningRun,
  RecentSearchSummary,
  ActivityEvent,
  ComparisonResolveResult,
} from '../types';
import { buildMultiComparisonPlan } from '../utils/comparisonPlan';
import { buildRecentSearchesFromRuns } from '../utils/recentSearchesFallback';

const configuredApi = (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, "");
export const API_BASE = configuredApi ? `${configuredApi}/api` : "/api";

export async function fetchStatus(): Promise<SystemStatus> {
  const res = await fetch(`${API_BASE}/status`);
  if (!res.ok) throw new Error(`Status error: ${res.statusText}`);
  return res.json();
}

export async function fetchTechnologyCounts(): Promise<Record<string, number>> {
  const res = await fetch(`${API_BASE}/technology-counts`);
  if (!res.ok) throw new Error(`Technology counts error: ${res.statusText}`);
  return res.json();
}

export async function fetchMetrics(technology = 'golang', runId?: number): Promise<DashboardMetrics> {
  const params = new URLSearchParams({ technology });
  if (runId) params.append('run_id', runId.toString());
  const res = await fetch(`${API_BASE}/metrics?${params.toString()}`);
  if (!res.ok) throw new Error(`Metrics error: ${res.statusText}`);
  return res.json();
}

export async function fetchEvents(limit = 50, runId?: number, technology = 'golang'): Promise<ActivityEvent[]> {
  const params = new URLSearchParams({ limit: limit.toString(), technology });
  if (runId) params.append('run_id', runId.toString());
  const res = await fetch(`${API_BASE}/events?${params.toString()}`);
  if (!res.ok) throw new Error(`Events error: ${res.statusText}`);
  return res.json();
}

export async function fetchCandidates(
  search = '',
  filter = '',
  limit = 50,
  offset = 0,
  technology = 'golang'
): Promise<CandidateListResponse> {
  const params = new URLSearchParams({
    limit: limit.toString(),
    offset: offset.toString(),
    technology,
  });
  if (search) params.append('search', search);
  if (filter) params.append('filter_status', filter);

  const res = await fetch(`${API_BASE}/candidates?${params.toString()}`);
  if (!res.ok) throw new Error(`Candidates error: ${res.statusText}`);
  return res.json();
}

export async function fetchRuns(limit = 20, technology = 'golang'): Promise<ScreeningRun[]> {
  const res = await fetch(`${API_BASE}/runs?limit=${limit}&technology=${encodeURIComponent(technology)}`);
  if (!res.ok) throw new Error(`Runs error: ${res.statusText}`);
  return res.json();
}

export async function fetchRecentSearches(limit = 5, technology = 'golang'): Promise<RecentSearchSummary[]> {
  const capped = Math.min(Math.max(limit, 1), 20);
  try {
    const res = await fetch(
      `${API_BASE}/recent-searches?limit=${capped}&technology=${encodeURIComponent(technology)}`
    );
    if (res.ok) {
      return res.json();
    }
    if (res.status === 404 || res.status === 405 || res.status === 500) {
      const runs = await fetchRuns(80, technology);
      return buildRecentSearchesFromRuns(runs, technology, capped);
    }
    throw new Error(`Recent searches error: ${res.statusText}`);
  } catch (err) {
    if (err instanceof Error && err.message.startsWith('Recent searches error')) {
      throw err;
    }
    const runs = await fetchRuns(80, technology);
    return buildRecentSearchesFromRuns(runs, technology, capped);
  }
}

export async function startRun(
  technology = 'golang',
  searchUrl?: string,
  options?: { baselineUrl?: string; diffExcludeRunId?: number }
): Promise<{ success: boolean; message: string }> {
  const res = await fetch(`${API_BASE}/runs/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      technology,
      search_url: searchUrl && searchUrl.trim() ? searchUrl.trim() : null,
      baseline_url:
        options?.baselineUrl && options.baselineUrl.trim()
          ? options.baselineUrl.trim()
          : null,
      diff_exclude_run_id: options?.diffExcludeRunId ?? null,
    }),
  });
  return res.json();
}

async function comparisonPlanFromRuns(
  technology: string,
  urls: string[]
): Promise<ComparisonResolveResult> {
  const cleaned = urls.map((u) => u.trim()).filter((u) => u.startsWith('http'));
  const runs = await fetchRuns(80, technology);
  return buildMultiComparisonPlan(runs, cleaned);
}

export async function resolveComparison(
  technology: string,
  urls: string[]
): Promise<ComparisonResolveResult> {
  let local: ComparisonResolveResult;
  try {
    local = await comparisonPlanFromRuns(technology, urls);
  } catch {
    throw new Error(
      'Could not reach the API. On Vercel, set VITE_API_URL to your Render backend (no trailing slash) and redeploy the frontend.'
    );
  }

  try {
    const res = await fetch(`${API_BASE}/resolve-comparison`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ technology, urls }),
    });
    if (res.ok) {
      const server: ComparisonResolveResult = await res.json();
      if (server.url_slots?.length || server.baseline_sheet_url) {
        return server;
      }
      return server.ready ? server : local;
    }
  } catch {
    // POST optional (older Render builds, CORS blips) — run list plan is enough for Check plan
  }

  if (local.ready) {
    local.message += ' (from run history on API).';
  }
  return local;
}

export async function startComparisonRun(
  technology: string,
  urls: string[]
): Promise<{ success: boolean; message: string }> {
  const cleaned = urls.map((u) => u.trim()).filter((u) => u.startsWith('http'));
  if (cleaned.length < 2) {
    return { success: false, message: 'Add at least 2 links.' };
  }
  const plan = await resolveComparison(technology, cleaned);
  if (!plan.ready) {
    return { success: false, message: plan.message };
  }
  const res = await fetch(`${API_BASE}/runs/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      technology,
      search_url: cleaned[cleaned.length - 1],
      comparison_urls: cleaned,
      diff_exclude_run_ids: plan.exclude_run_ids ?? [],
    }),
  });
  return res.json();
}

export async function pauseRun(): Promise<{ success: boolean; message: string }> {
  const res = await fetch(`${API_BASE}/runs/pause`, { method: 'POST' });
  return res.json();
}

export async function resumeRun(): Promise<{ success: boolean; message: string }> {
  const res = await fetch(`${API_BASE}/runs/resume`, { method: 'POST' });
  return res.json();
}

export async function stopRun(): Promise<{ success: boolean; message: string }> {
  const res = await fetch(`${API_BASE}/runs/stop`, { method: 'POST' });
  return res.json();
}

export async function scanCandidateGitRoll(
  candidateId: number,
  addInstahyreNote: boolean = false,
  dryRun: boolean = false,
  technology: string = 'golang'
): Promise<{
  success: boolean;
  candidate_id: number;
  candidate_name: string;
  github_url: string;
  gitroll_rating?: number;
  gitroll_grade?: string;
  gitroll_profile_url?: string;
  note_text?: string;
  note_status?: string;
  error?: string;
}> {
  const url = `${API_BASE}/candidates/${candidateId}/gitroll-scan?add_instahyre_note=${addInstahyreNote}&dry_run=${dryRun}&technology=${technology}`;
  const res = await fetch(url, { method: 'POST' });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || 'GitRoll scan failed');
  }
  return res.json();
}

export async function setCandidateDecision(
  candidateId: number,
  decision: 'SELECTED' | 'REJECTED' | null,
  technology = 'golang'
): Promise<{ success: boolean; id: number; decision: string | null }> {
  const res = await fetch(
    `${API_BASE}/candidates/${candidateId}/decision?technology=${encodeURIComponent(technology)}`,
    {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ decision }),
    }
  );
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || 'Failed to save decision');
  }
  return res.json();
}

export async function exportToGoogleSheets(
  technology: string = 'javascript',
  sheetUrl?: string
): Promise<{
  success: boolean;
  count: number;
  sheet_url: string;
  message: string;
}> {
  const query = sheetUrl ? `?technology=${technology}&sheet_url=${encodeURIComponent(sheetUrl)}` : `?technology=${technology}`;
  const res = await fetch(`${API_BASE}/candidates/export-google-sheets${query}`, {
    method: 'POST',
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || 'Failed to export to Google Sheets');
  }
  return res.json();
}

