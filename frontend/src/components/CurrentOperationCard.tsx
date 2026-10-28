import React from 'react';
import { Activity, CheckCircle, ArrowRight, AlertTriangle, Radio } from 'lucide-react';
import { CurrentOperation, RunState } from '../types';

interface CurrentOperationCardProps {
  operation?: CurrentOperation;
  runState?: RunState;
}

export const CurrentOperationCard: React.FC<CurrentOperationCardProps> = ({
  operation,
  runState,
}) => {
  const isRunning = runState === 'RUNNING' || runState === 'VALIDATING';

  return (
    <div
      className="agent-card"
      style={{
        borderLeft: isRunning ? '3px solid var(--accent-primary)' : '1px solid var(--border-subtle)',
        background: isRunning
          ? 'linear-gradient(135deg, rgba(99, 102, 241, 0.08) 0%, var(--bg-card) 60%)'
          : 'var(--bg-card)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
        <div className="card-title" style={{ margin: 0 }}>
          <Activity size={15} color={isRunning ? 'var(--accent-primary)' : 'var(--text-muted)'} />
          Agent Live Telemetry
        </div>

        {isRunning ? (
          <span className="status-pill pill-running" style={{ fontSize: '10px', padding: '2px 8px' }}>
            <Radio size={11} className="dot-pulse" />
            LIVE EXECUTION
          </span>
        ) : (
          <span className="status-pill pill-idle" style={{ fontSize: '10px', padding: '2px 8px' }}>
            STANDBY
          </span>
        )}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '16px' }}>
        {/* Main Status & Operation */}
        <div style={{ background: 'rgba(6, 10, 20, 0.5)', padding: '12px 14px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
          <div style={{ fontSize: '11px', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '6px', fontWeight: 600 }}>
            Current Operation
          </div>
          <div style={{ fontSize: '15px', fontWeight: '700', color: '#ffffff', display: 'flex', alignItems: 'center', gap: '8px' }}>
            {isRunning && <span className="status-dot dot-indigo dot-pulse" />}
            {operation?.current_operation || 'Agent is idle'}
          </div>

          <div style={{ marginTop: '8px', fontSize: '12px', color: 'var(--text-muted)' }}>
            Status: <span style={{ color: '#e2e8f0', fontWeight: '600' }}>{operation?.current_status || 'Ready for screening'}</span>
          </div>

          {operation?.candidate_reference && (
            <div style={{ marginTop: '8px', fontSize: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ color: 'var(--text-dim)' }}>Candidate:</span>
              <span className="code-tag" style={{ color: 'var(--accent-cyan)', borderColor: 'rgba(6, 182, 212, 0.3)' }}>
                {operation.candidate_reference}
              </span>
            </div>
          )}
        </div>

        {/* Stage & Plan */}
        <div style={{ background: 'rgba(6, 10, 20, 0.5)', padding: '12px 14px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
          <div style={{ fontSize: '11px', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '6px', fontWeight: 600 }}>
            Workflow Stage
          </div>
          <div style={{ fontSize: '14px', fontWeight: '700', color: 'var(--accent-cyan)' }}>
            {operation?.workflow_stage || 'IDLE'}
          </div>

          <div style={{ marginTop: '10px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {operation?.last_completed_action && (
              <div style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <CheckCircle size={13} color="var(--accent-emerald)" />
                <span>Last: <span style={{ color: '#cbd5e1' }}>{operation.last_completed_action}</span></span>
              </div>
            )}
            {operation?.next_planned_action && (
              <div style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <ArrowRight size={13} color="var(--accent-primary)" />
                <span>Next: <span style={{ color: '#cbd5e1' }}>{operation.next_planned_action}</span></span>
              </div>
            )}
          </div>
        </div>

        {/* Warning or Error if present */}
        {operation?.warning_or_error && (
          <div style={{
            gridColumn: '1 / -1',
            background: 'rgba(239, 68, 68, 0.12)',
            border: '1px solid rgba(239, 68, 68, 0.35)',
            borderRadius: 'var(--radius-sm)',
            padding: '10px 14px',
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            color: '#f87171',
            fontSize: '12px'
          }}>
            <AlertTriangle size={16} />
            <span>{operation.warning_or_error}</span>
          </div>
        )}
      </div>
    </div>
  );
};
