import {
  SystemStatus,
  DashboardMetrics,
  CandidateListResponse,
  ScreeningRun,
  ActivityEvent,
} from '../types';

const API_BASE = '/api';

export async function fetchStatus(): Promise<SystemStatus> {
  const res = await fetch(`${API_BASE}/status`);
  if (!res.ok) throw new Error(`Status error: ${res.statusText}`);
  return res.json();
}

export async function fetchMetrics(technology = 'golang', runId?: number): Promise<DashboardMetrics> {
  const params = new URLSearchParams({ technology });
  if (runId) params.append('run_id', runId.toString());
  const res = await fetch(`${API_BASE}/metrics?${params.toString()}`);
  if (!res.ok) throw new Error(`Metrics error: ${res.statusText}`);
  return res.json();
}

export async function fetchEvents(limit = 50, runId?: number): Promise<ActivityEvent[]> {
  const params = new URLSearchParams({ limit: limit.toString() });
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

export async function startRun(
  technology = 'golang',
  searchUrl?: string
): Promise<{ success: boolean; message: string }> {
  const res = await fetch(`${API_BASE}/runs/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      technology,
      search_url: searchUrl && searchUrl.trim() ? searchUrl.trim() : null,
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

