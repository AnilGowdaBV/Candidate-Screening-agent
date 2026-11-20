import React, { useCallback, useEffect, useState } from 'react';
import { ExternalLink, History, RefreshCw } from 'lucide-react';
import { fetchRecentSearches, fetchRuns } from '../services/api';
import { RecentSearchSummary, ScreeningRun, SearchComparisonSummary } from '../types';

interface RunHistoryProps {
  technology: string;
}

const linkBtnStyle: React.CSSProperties = {
  padding: '5px 11px',
  fontSize: '11px',
  fontWeight: 600,
  gap: '5px',
  textDecoration: 'none',
  display: 'inline-flex',
  alignItems: 'center',
  whiteSpace: 'nowrap',
};

function InstahyreLinkButton({
  href,
  label,
  title,
}: {
  href: string;
  label: string;
  title?: string;
}) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      title={title || href}
      className="btn btn-secondary"
      style={linkBtnStyle}
    >
      {label}
      <ExternalLink size={11} />
    </a>
  );
}

function SheetLinkButton({
  href,
  label,
  variant = 'secondary',
}: {
  href: string;
  label: string;
  variant?: 'secondary' | 'primary';
}) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      title={`Open ${label} in Google Sheets`}
      className={variant === 'primary' ? 'btn btn-primary' : 'btn btn-secondary'}
      style={{ ...linkBtnStyle, fontSize: '11px' }}
    >
      {label}
      <ExternalLink size={11} />
    </a>
  );
}

function runConfig(run: ScreeningRun | undefined): Record<string, unknown> {
  if (!run?.configuration_snapshot) return {};
  try {
    return JSON.parse(run.configuration_snapshot) as Record<string, unknown>;
  } catch {
    return {};
  }
}

function enrichComparisonRows(
  rows: RecentSearchSummary[],
  runs: ScreeningRun[]
): RecentSearchSummary[] {
  const byId = new Map(runs.map((run) => [run.id, run]));
  return rows.map((row) => {
    if (row.is_comparison && row.comparison) return row;
    const cfg = runConfig(byId.get(row.run_id));
    const rawDiff = cfg.diff_exclude_run_id;
    const diffId =
      typeof rawDiff === 'number'
        ? rawDiff
        : typeof rawDiff === 'string'
          ? parseInt(rawDiff, 10)
          : NaN;
    if (!diffId || Number.isNaN(diffId)) return row;
    const baseRun = byId.get(diffId);
    const baseCfg = runConfig(baseRun);
    const baseUrl = (baseCfg.instahyre_search_url as string) || null;
    const newUrl = (cfg.instahyre_search_url as string) || row.instahyre_search_url || null;
    const comparison: SearchComparisonSummary = {
      baseline_run_id: diffId,
      baseline_search_short: `Run #${diffId}`,
      baseline_search_url: baseUrl,
      baseline_sheet_tab: row.comparison?.baseline_sheet_tab ?? '—',
      baseline_sheet_url: row.comparison?.baseline_sheet_url ?? row.google_sheet_url,
      new_run_id: row.run_id,
      new_search_short: row.instahyre_search_short,
      new_search_url: newUrl,
      new_only_sheet_tab: row.google_sheet_tab,
      new_only_sheet_url: row.google_sheet_url,
    };
    if (row.comparison?.baseline_sheet_tab) {
      comparison.baseline_sheet_tab = row.comparison.baseline_sheet_tab;
      comparison.baseline_sheet_url = row.comparison.baseline_sheet_url;
    }
    return { ...row, is_comparison: true, comparison };
  });
}

function searchFingerprint(url: string | null | undefined): string {
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

export const RunHistory: React.FC<RunHistoryProps> = ({ technology }) => {
  const [rows, setRows] = useState<RecentSearchSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [data, runs] = await Promise.all([
        fetchRecentSearches(20, technology),
        fetchRuns(40, technology),
      ]);
      const enriched = enrichComparisonRows(data, runs);
      const seen = new Set<string>();
      const unique: RecentSearchSummary[] = [];
      for (const row of enriched) {
        const fp = row.is_comparison
          ? `compare-${row.comparison?.baseline_run_id}-${row.run_id}`
          : searchFingerprint(row.instahyre_search_url) || `run-${row.run_id}`;
        if (seen.has(fp)) continue;
        seen.add(fp);
        unique.push(row);
        if (unique.length >= 5) break;
      }
      setRows(unique);
    } catch (err) {
      console.error('Failed to load recent searches:', err);
      setError('Could not load searches. Restart the backend (port 8000) and click Refresh.');
      setRows([]);
    } finally {
      setLoading(false);
    }
  }, [technology]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="agent-card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
        <div className="card-title" style={{ margin: 0 }}>
          <History size={15} color="var(--accent-purple)" />
          Recent Searches
          <span style={{ fontSize: '11px', color: 'var(--text-dim)', textTransform: 'none', fontWeight: 500, marginLeft: '6px' }}>
            (Last 5 unique searches)
          </span>
        </div>
        <button
          className="btn btn-secondary"
          onClick={load}
          disabled={loading}
          style={{ padding: '5px 12px', fontSize: '11px', gap: '6px' }}
        >
          <RefreshCw size={12} />
          <span>{loading ? 'Loading…' : 'Refresh'}</span>
        </button>
      </div>

      {error && (
        <p style={{ fontSize: '12px', color: '#dc2626', marginBottom: '10px' }}>{error}</p>
      )}
      <div className="data-table-container">
        <table className="data-table">
          <thead>
            <tr>
              <th style={{ width: '64px' }}>Run</th>
              <th style={{ width: '88px' }}>Tech</th>
              <th>Instahyre search</th>
              <th style={{ width: '140px' }}>Results sheet</th>
              <th style={{ width: '100px' }}>Status</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={5} style={{ textAlign: 'center', padding: '28px', color: 'var(--text-dim)' }}>
                  No searches yet for this technology.
                </td>
              </tr>
            ) : (
              rows.map((r) => (
                <tr key={r.run_id}>
                  <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--accent-cyan)' }}>
                    {r.is_comparison && r.comparison ? (
                      <div style={{ fontSize: '11px', lineHeight: 1.35 }}>
                        <div>#{r.comparison.baseline_run_id}</div>
                        <div style={{ color: 'var(--accent-purple)' }}>→ #{r.run_id}</div>
                      </div>
                    ) : (
                      `#${r.run_id}`
                    )}
                  </td>
                  <td style={{ fontWeight: 600, textTransform: 'uppercase', fontSize: '12px' }}>
                    {r.technology}
                  </td>
                  <td>
                    {r.is_comparison && r.comparison ? (
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', alignItems: 'center' }}>
                        {r.comparison.baseline_search_url ? (
                          <InstahyreLinkButton
                            href={r.comparison.baseline_search_url}
                            label={`Link 1 · #${r.comparison.baseline_run_id}`}
                            title={r.comparison.baseline_search_short}
                          />
                        ) : null}
                        {r.comparison.new_search_url ? (
                          <InstahyreLinkButton
                            href={r.comparison.new_search_url}
                            label={`Link 2 · #${r.comparison.new_run_id}`}
                            title={r.comparison.new_search_short}
                          />
                        ) : null}
                      </div>
                    ) : r.instahyre_search_url ? (
                      <InstahyreLinkButton
                        href={r.instahyre_search_url}
                        label="Open search"
                        title={`${r.instahyre_search_short}\n\n${r.instahyre_search_url}`}
                      />
                    ) : (
                      <span style={{ color: 'var(--text-secondary)', fontSize: '12px' }}>
                        {r.instahyre_search_short}
                      </span>
                    )}
                  </td>
                  <td>
                    {r.is_comparison && r.comparison ? (
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                        {r.comparison.baseline_sheet_tab &&
                        r.comparison.baseline_sheet_tab !== '—' ? (
                          <SheetLinkButton
                            href={r.comparison.baseline_sheet_url}
                            label={r.comparison.baseline_sheet_tab}
                          />
                        ) : null}
                        <SheetLinkButton
                          href={r.comparison.new_only_sheet_url}
                          label={
                            r.comparison.baseline_sheet_tab &&
                            r.comparison.baseline_sheet_tab !== '—'
                              ? `${r.comparison.new_only_sheet_tab} · new`
                              : r.comparison.new_only_sheet_tab
                          }
                          variant="primary"
                        />
                      </div>
                    ) : (
                      <SheetLinkButton href={r.google_sheet_url} label={r.google_sheet_tab} />
                    )}
                  </td>
                  <td>
                    <span
                      className={`status-pill ${
                        r.status === 'COMPLETED'
                          ? 'pill-completed'
                          : r.status === 'RUNNING'
                            ? 'pill-running'
                            : r.status === 'FAILED'
                              ? 'pill-failed'
                              : 'pill-idle'
                      }`}
                    >
                      {r.status}
                    </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};