import React from 'react';
import { GitCommit, CheckCircle2, Loader2 } from 'lucide-react';

interface WorkflowTrackerProps {
  currentStage?: string;
  isRunActive: boolean;
}

const STAGES = [
  'Config validation',
  'Instahyre search',
  'Profile inspection',
  'GitHub discovery',
  'Repo analysis',
  'Classification',
  'Note handling',
  'SQLite checkpoint',
  'Completion',
];

export const WorkflowTracker: React.FC<WorkflowTrackerProps> = ({
  currentStage = 'IDLE',
  isRunActive,
}) => {
  const currentIndex = STAGES.findIndex(
    (s) => s.toLowerCase() === (currentStage || '').toLowerCase()
  );

  return (
    <div className="agent-card">
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
        <div className="card-title" style={{ margin: 0 }}>
          <GitCommit size={15} color="var(--accent-cyan)" />
          Workflow Execution Pipeline
        </div>
        <span style={{ fontSize: '11px', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
          9 Automated Stages
        </span>
      </div>

      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '6px',
          overflowX: 'auto',
          padding: '8px 4px 6px 4px',
        }}
      >
        {STAGES.map((stage, idx) => {
          let status: 'completed' | 'active' | 'pending' = 'pending';

          if (currentIndex !== -1) {
            if (idx < currentIndex) status = 'completed';
            else if (idx === currentIndex) status = isRunActive ? 'active' : 'completed';
          } else if (currentStage === 'Completion' || currentStage === 'COMPLETED') {
            status = 'completed';
          }

          return (
            <React.Fragment key={stage}>
              <div
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  gap: '8px',
                  minWidth: '95px',
                  textAlign: 'center',
                }}
              >
                <div
                  style={{
                    width: '32px',
                    height: '32px',
                    borderRadius: '50%',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    background:
                      status === 'completed'
                        ? 'rgba(16, 185, 129, 0.15)'
                        : status === 'active'
                        ? 'rgba(99, 102, 241, 0.25)'
                        : 'rgba(255, 255, 255, 0.04)',
                    border:
                      status === 'completed'
                        ? '1.5px solid #10b981'
                        : status === 'active'
                        ? '2px solid #6366f1'
                        : '1px solid rgba(255, 255, 255, 0.1)',
                    color:
                      status === 'completed'
                        ? '#10b981'
                        : status === 'active'
                        ? '#a5b4fc'
                        : '#64748b',
                    boxShadow:
                      status === 'completed'
                        ? '0 0 10px rgba(16, 185, 129, 0.3)'
                        : status === 'active'
                        ? '0 0 16px rgba(99, 102, 241, 0.5)'
                        : 'none',
                    transition: 'all 0.25s ease',
                  }}
                >
                  {status === 'completed' ? (
                    <CheckCircle2 size={16} />
                  ) : status === 'active' ? (
                    <Loader2 size={16} className="dot-pulse" />
                  ) : (
                    <span style={{ fontSize: '11px', fontWeight: '700', fontFamily: 'var(--font-mono)' }}>
                      {idx + 1}
                    </span>
                  )}
                </div>

                <span
                  style={{
                    fontSize: '11px',
                    fontWeight: status === 'active' ? '700' : '500',
                    color:
                      status === 'completed'
                        ? '#34d399'
                        : status === 'active'
                        ? '#ffffff'
                        : 'var(--text-dim)',
                    lineHeight: '1.2',
                  }}
                >
                  {stage}
                </span>
              </div>

              {idx < STAGES.length - 1 && (
                <div
                  style={{
                    flex: 1,
                    height: '2px',
                    background:
                      status === 'completed'
                        ? 'linear-gradient(90deg, #10b981, rgba(16, 185, 129, 0.4))'
                        : 'rgba(255, 255, 255, 0.07)',
                    minWidth: '14px',
                    marginBottom: '20px',
                    transition: 'all 0.25s ease',
                  }}
                />
              )}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
};
