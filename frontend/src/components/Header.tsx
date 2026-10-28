import React from 'react';
import { Database, Github, Globe, Laptop, Cpu, ShieldCheck, Sparkles } from 'lucide-react';
import { SystemStatus, RunState, TechnologyKey } from '../types';
import { TECHNOLOGIES } from './TechnologyCards';

interface HeaderProps {
  status: SystemStatus | null;
  selectedTechnology?: TechnologyKey;
}

export const Header: React.FC<HeaderProps> = ({ status, selectedTechnology = 'golang' }) => {
  const currentTech = TECHNOLOGIES.find(t => t.key === selectedTechnology) || TECHNOLOGIES[0];

  const getRunBadgeClass = (state?: RunState) => {
    switch (state) {
      case 'RUNNING':
        return 'pill-running';
      case 'PAUSED':
      case 'PAUSE_REQUESTED':
        return 'pill-paused';
      case 'COMPLETED':
        return 'pill-completed';
      case 'FAILED':
      case 'STOPPED':
        return 'pill-failed';
      default:
        return 'pill-idle';
    }
  };

  const isRunning = status?.run_state === 'RUNNING';

  return (
    <header
      className="agent-card"
      style={{
        padding: '16px 24px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '16px',
        borderBottom: '1px solid var(--border-medium)',
      }}
    >
      {/* Brand & Active System State */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        {/* Glowing Futuristic Agent Emblem */}
        <div style={{ position: 'relative' }}>
          <div
            style={{
              position: 'absolute',
              inset: '-3px',
              borderRadius: '14px',
              background: 'linear-gradient(135deg, #6366f1, #06b6d4, #10b981)',
              opacity: isRunning ? 0.9 : 0.4,
              filter: 'blur(8px)',
              transition: 'opacity 0.3s ease',
            }}
          />
          <div
            style={{
              position: 'relative',
              width: '44px',
              height: '44px',
              borderRadius: '12px',
              background: 'linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%)',
              border: '1px solid rgba(255, 255, 255, 0.2)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#38bdf8',
              boxShadow: '0 4px 16px rgba(0, 0, 0, 0.4)',
            }}
          >
            <Cpu size={22} className={isRunning ? 'dot-pulse' : ''} />
          </div>
        </div>

        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
            <h1
              style={{
                fontSize: '19px',
                fontWeight: '800',
                letterSpacing: '-0.02em',
                fontFamily: 'var(--font-display)',
                background: 'linear-gradient(180deg, #ffffff 30%, #cbd5e1 100%)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
              }}
            >
              Candidate Screening Agent
            </h1>

            <span className="code-tag" style={{ fontSize: '10px', color: 'var(--accent-cyan)', borderColor: 'rgba(6, 182, 212, 0.3)' }}>
              v2.4 Multi-DB
            </span>

            <span className={`status-pill ${getRunBadgeClass(status?.run_state)}`}>
              <span className={`status-dot ${isRunning ? 'dot-indigo dot-pulse' : 'dot-green'}`} />
              {status?.run_state || 'READY'}
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '3px' }}>
            <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              Instahyre Candidate Inspection & GitHub Repository Verification
            </p>
            <span style={{ color: 'var(--border-medium)' }}>•</span>
            <div style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '11px', color: currentTech.color }}>
              <Sparkles size={11} />
              <span style={{ fontWeight: 600 }}>Active Workspace: {currentTech.name}</span>
            </div>
          </div>
        </div>
      </div>

      {/* System Status Indicators */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
        <div
          className="status-pill pill-idle"
          title="Running locally on Windows workstation"
          style={{ background: 'rgba(255, 255, 255, 0.04)', borderColor: 'rgba(255, 255, 255, 0.08)' }}
        >
          <Laptop size={13} color="#94a3b8" />
          <span>Local Engine</span>
        </div>

        <div
          className="status-pill pill-idle"
          title={status?.database_ready ? 'SQLite DB connected' : 'Database unreachable'}
          style={{ background: 'rgba(16, 185, 129, 0.06)', borderColor: 'rgba(16, 185, 129, 0.25)' }}
        >
          <Database size={13} color={status?.database_ready ? '#10b981' : '#ef4444'} />
          <span style={{ color: status?.database_ready ? '#a7f3d0' : '#fca5a5' }}>
            SQLite Multi-DB
          </span>
        </div>

        <div
          className="status-pill pill-idle"
          title={status?.is_github_configured ? 'GitHub Token Ready' : 'GitHub Token Missing in .env'}
          style={{ background: 'rgba(6, 182, 212, 0.06)', borderColor: 'rgba(6, 182, 212, 0.25)' }}
        >
          <Github size={13} color={status?.is_github_configured ? '#06b6d4' : '#f59e0b'} />
          <span style={{ color: status?.is_github_configured ? '#a5f3fc' : '#fde68a' }}>
            GitHub API
          </span>
        </div>

        <div
          className="status-pill pill-idle"
          title={status?.is_instahyre_configured ? 'Instahyre Auth Ready' : 'Manual Login / Pending in .env'}
          style={{ background: 'rgba(99, 102, 241, 0.06)', borderColor: 'rgba(99, 102, 241, 0.25)' }}
        >
          <Globe size={13} color={status?.is_instahyre_configured ? '#818cf8' : '#f59e0b'} />
          <span style={{ color: status?.is_instahyre_configured ? '#c7d2fe' : '#fde68a' }}>
            Instahyre Session
          </span>
        </div>

        {status?.dry_run && (
          <div className="status-pill pill-paused" title="Dry Run Enabled: No notes will be written to Instahyre">
            <ShieldCheck size={13} />
            <span>DRY-RUN ON</span>
          </div>
        )}
      </div>
    </header>
  );
};
