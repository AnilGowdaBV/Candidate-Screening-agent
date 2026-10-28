import React from 'react';
import { Play, Pause, RotateCcw, Square, ExternalLink, Search, X, ShieldAlert, Zap } from 'lucide-react';
import { SystemStatus, TechnologyKey } from '../types';
import { TECHNOLOGIES } from './TechnologyCards';

interface ControlPanelProps {
  status: SystemStatus | null;
  selectedTechnology: TechnologyKey;
  onSelectTechnology: (tech: TechnologyKey) => void;
  searchUrl: string;
  onSearchUrlChange: (url: string) => void;
  onStart: () => void;
  onPause: () => void;
  onResume: () => void;
  onStop: () => void;
  isLoading: boolean;
}

export const ControlPanel: React.FC<ControlPanelProps> = ({
  status,
  selectedTechnology,
  onSelectTechnology,
  searchUrl,
  onSearchUrlChange,
  onStart,
  onPause,
  onResume,
  onStop,
  isLoading,
}) => {
  const runState = status?.run_state || 'IDLE';

  const hasValidUrl = Boolean(searchUrl.trim().startsWith('http'));
  const canStart = (runState === 'IDLE' || runState === 'COMPLETED' || runState === 'STOPPED' || runState === 'FAILED') && hasValidUrl;
  const canPause = runState === 'RUNNING';
  const canResume = runState === 'PAUSED';
  const canStop = runState === 'RUNNING' || runState === 'PAUSED' || runState === 'PAUSE_REQUESTED' || runState === 'VALIDATING';

  const currentTech = TECHNOLOGIES.find(t => t.key === selectedTechnology) || TECHNOLOGIES[0];

  const noteFoundText = `${currentTech.name} found`;
  const noteNotFoundText = `${currentTech.name} not found`;

  return (
    <div
      className="agent-card"
      style={{
        padding: '14px 18px',
        display: 'flex',
        flexDirection: 'column',
        gap: '10px',
        background: 'rgba(11, 17, 34, 0.85)',
      }}
    >
      {/* Main Single-Row Command Bar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          flexWrap: 'wrap',
        }}
      >
        {/* 1. Target Technology Selector */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexShrink: 0 }}>
          <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Target:
          </span>
          <select
            value={selectedTechnology}
            onChange={(e) => onSelectTechnology(e.target.value as TechnologyKey)}
            style={{
              background: 'rgba(6, 10, 20, 0.95)',
              border: `1.5px solid ${currentTech.color}`,
              borderRadius: 'var(--radius-sm)',
              color: '#ffffff',
              padding: '7px 12px',
              fontSize: '13px',
              fontWeight: 700,
              outline: 'none',
              cursor: 'pointer',
              boxShadow: `0 0 10px ${currentTech.glowColor}`,
            }}
          >
            {TECHNOLOGIES.map(t => (
              <option key={t.key} value={t.key} style={{ background: '#0b1120', color: '#ffffff' }}>
                {t.name}
              </option>
            ))}
          </select>
        </div>

        {/* 2. Instahyre Search URL Bar */}
        <div
          style={{
            flex: '1 1 340px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            background: 'rgba(6, 10, 20, 0.85)',
            border: '1px solid var(--border-medium)',
            borderRadius: 'var(--radius-sm)',
            padding: '7px 12px',
            transition: 'border-color 0.2s',
            minWidth: '240px',
          }}
        >
          <Search size={14} color="var(--accent-cyan)" style={{ flexShrink: 0 }} />
          <input
            type="text"
            value={searchUrl}
            onChange={(e) => onSearchUrlChange(e.target.value)}
            placeholder="Required: Paste your filtered Instahyre search URL here to start..."
            style={{
              background: 'transparent',
              border: 'none',
              outline: 'none',
              color: '#ffffff',
              fontSize: '12px',
              fontFamily: 'var(--font-mono)',
              flex: 1,
              minWidth: 0,
            }}
          />

          {searchUrl ? (
            <button
              type="button"
              onClick={() => onSearchUrlChange('')}
              title="Clear URL"
              style={{
                background: 'transparent',
                border: 'none',
                color: 'var(--text-dim)',
                cursor: 'pointer',
                padding: '2px',
                display: 'flex',
                alignItems: 'center',
              }}
            >
              <X size={13} />
            </button>
          ) : null}

          {searchUrl.startsWith('http') && (
            <a
              href={searchUrl}
              target="_blank"
              rel="noreferrer"
              title="Open URL in new tab"
              style={{
                color: 'var(--accent-cyan)',
                display: 'flex',
                alignItems: 'center',
                gap: '3px',
                textDecoration: 'none',
                fontSize: '11px',
                fontWeight: 600,
                flexShrink: 0,
              }}
            >
              <span>Open</span>
              <ExternalLink size={10} />
            </a>
          )}
        </div>

        {/* 3. Action Button Group */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexShrink: 0 }}>
          <button
            className="btn btn-primary"
            disabled={!canStart || isLoading}
            onClick={onStart}
            title={!hasValidUrl ? 'Please paste an Instahyre search URL to enable start' : `Start ${currentTech.name} screening workflow`}
            style={{
              padding: '8px 16px',
              fontSize: '13px',
              background: canStart ? `linear-gradient(135deg, ${currentTech.color} 0%, #4338ca 100%)` : 'rgba(255, 255, 255, 0.08)',
              boxShadow: canStart ? `0 2px 14px ${currentTech.glowColor}` : 'none',
              opacity: canStart ? 1 : 0.45,
            }}
          >
            <Play size={14} fill="currentColor" />
            <span>{hasValidUrl ? `Start (${currentTech.name})` : `Paste URL to Start`}</span>
          </button>

          <button
            className="btn btn-amber"
            disabled={!canPause || isLoading}
            onClick={onPause}
            title="Pause workflow at safe boundary"
            style={{ padding: '8px 12px', fontSize: '12px' }}
          >
            <Pause size={13} />
            <span>Pause</span>
          </button>

          <button
            className="btn btn-emerald"
            disabled={!canResume || isLoading}
            onClick={onResume}
            title="Resume workflow from checkpoint"
            style={{ padding: '8px 12px', fontSize: '12px' }}
          >
            <RotateCcw size={13} />
            <span>Resume</span>
          </button>

          <button
            className="btn btn-rose"
            disabled={!canStop || isLoading}
            onClick={onStop}
            title="Stop screening safely and preserve database"
            style={{ padding: '8px 12px', fontSize: '12px' }}
          >
            <Square size={13} />
            <span>Stop</span>
          </button>
        </div>
      </div>

      {/* Sub-strip: Notes & Live Mode Info (Single Compact Line) */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '8px',
          paddingTop: '6px',
          borderTop: '1px solid rgba(255, 255, 255, 0.05)',
          fontSize: '11px',
          color: 'var(--text-dim)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
          <span style={{ color: 'var(--text-muted)', fontWeight: 600 }}>Notes written to Instahyre:</span>
          <span className="code-tag" style={{ fontSize: '10.5px' }}>No GitHub found</span>
          <span className="code-tag" style={{ fontSize: '10.5px', color: '#34d399', borderColor: 'rgba(16, 185, 129, 0.3)' }}>{noteFoundText}</span>
          <span className="code-tag" style={{ fontSize: '10.5px' }}>{noteNotFoundText}</span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          {status?.dry_run ? (
            <span style={{ color: '#fde047', display: 'flex', alignItems: 'center', gap: '4px' }}>
              <ShieldAlert size={12} />
              <span>Dry-Run Active (No notes pushed)</span>
            </span>
          ) : (
            <span style={{ color: '#6ee7b7', display: 'flex', alignItems: 'center', gap: '5px' }}>
              <Zap size={12} color="#10b981" />
              <span>Live Mode: Verified notes added to {currentTech.name} profiles</span>
            </span>
          )}
        </div>
      </div>
    </div>
  );
};
