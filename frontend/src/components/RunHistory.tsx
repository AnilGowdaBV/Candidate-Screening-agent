import React from 'react';
import { History, RefreshCw } from 'lucide-react';
import { ScreeningRun } from '../types';

interface RunHistoryProps {
  runs: ScreeningRun[];
  onRefresh: () => void;
}

export const RunHistory: React.FC<RunHistoryProps> = ({ runs, onRefresh }) => {
  const displayedRuns = runs.slice(0, 5);

  return (
    <div className="agent-card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
        <div className="card-title" style={{ margin: 0 }}>
          <History size={15} color="var(--accent-purple)" />
          Screening Run History
          <span style={{ fontSize: '11px', color: 'var(--text-dim)', textTransform: 'none', fontWeight: 500, marginLeft: '6px' }}>
            (Last 5 Runs)
          </span>
        </div>
        <button className="btn btn-secondary" onClick={onRefresh} style={{ padding: '5px 12px', fontSize: '11px', gap: '6px' }}>
          <RefreshCw size={12} />
          <span>Refresh Runs</span>
        </button>
      </div>

      <div className="data-table-container">
        <table className="data-table">
          <thead>
            <tr>
              <th style={{ width: '80px' }}>Run ID</th>
              <th>Status</th>
              <th>Started At</th>
              <th>Finished At</th>
              <th>Processed</th>
              <th>Errors</th>
              <th>Last Checkpoint</th>
            </tr>
          </thead>
          <tbody>
            {displayedRuns.length === 0 ? (
              <tr>
                <td colSpan={7} style={{ textAlign: 'center', padding: '28px', color: 'var(--text-dim)' }}>
                  No prior screening runs recorded in this workspace.
                </td>
              </tr>
            ) : (
              displayedRuns.map((r) => {
                const startTime = new Date(r.started_at).toLocaleString();
                const finishTime = r.finished_at ? new Date(r.finished_at).toLocaleString() : 'In Progress';

                return (
                  <tr key={r.id}>
                    <td style={{ fontFamily: 'var(--font-mono)', fontWeight: '700', color: 'var(--accent-cyan)' }}>
                      #{r.id}
                    </td>
                    <td>
                      <span className={`status-pill ${
                        r.status === 'COMPLETED' ? 'pill-completed' :
                        r.status === 'RUNNING' ? 'pill-running' :
                        r.status === 'FAILED' ? 'pill-failed' : 'pill-idle'
                      }`}>
                        {r.status}
                      </span>
                    </td>
                    <td style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                      {startTime}
                    </td>
                    <td style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                      {finishTime}
                    </td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: '#f8fafc' }}>
                      {r.processed_count}
                    </td>
                    <td style={{ fontFamily: 'var(--font-mono)', color: r.error_count > 0 ? '#ef4444' : 'var(--text-dim)' }}>
                      {r.error_count}
                    </td>
                    <td style={{ fontSize: '11px', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
                      {r.last_checkpoint || '—'}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
