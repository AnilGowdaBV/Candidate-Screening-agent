import React, { useState } from 'react';
import {
  Play,
  Pause,
  RotateCcw,
  Square,
  ExternalLink,
  Search,
  X,
  ShieldAlert,
  Zap,
  GitCompare,
  Link2,
  Plus,
  Trash2,
} from 'lucide-react';
import { SystemStatus, TechnologyKey } from '../types';
import { TECHNOLOGIES } from './TechnologyCards';
import { resolveComparison, startComparisonRun, startRun } from '../services/api';

type SearchMode = 'unique' | 'comparison';

interface ControlPanelProps {
  status: SystemStatus | null;
  selectedTechnology: TechnologyKey;
  onSelectTechnology: (tech: TechnologyKey) => void;
  onPause: () => void;
  onResume: () => void;
  onStop: () => void;
  isLoading: boolean;
  onRunStarted: () => void;
}

const urlBoxStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: '8px',
  background: '#ffffff',
  border: '1px solid var(--border-medium)',
  borderRadius: 'var(--radius-sm)',
  padding: '7px 12px',
  minWidth: '240px',
  width: '100%',
};

const urlInputStyle: React.CSSProperties = {
  background: 'transparent',
  border: 'none',
  outline: 'none',
  color: 'var(--text-main)',
  fontSize: '12px',
  fontFamily: 'var(--font-mono)',
  flex: 1,
  minWidth: 0,
  width: '100%',
};

export const ControlPanel: React.FC<ControlPanelProps> = ({
  status,
  selectedTechnology,
  onSelectTechnology,
  onPause,
  onResume,
  onStop,
  isLoading,
  onRunStarted,
}) => {
  const [mode, setMode] = useState<SearchMode>('unique');
  const [uniqueUrl, setUniqueUrl] = useState('');
  const [compareUrls, setCompareUrls] = useState<string[]>(['', '']);
  const [compareHint, setCompareHint] = useState<string | null>(null);
  const [compareReady, setCompareReady] = useState(false);
  const [busy, setBusy] = useState(false);

  const cleanedCompareUrls = compareUrls.map((u) => u.trim()).filter((u) => u.startsWith('http'));
  const compareValid =
    cleanedCompareUrls.length >= 2 &&
    new Set(cleanedCompareUrls.map((u) => u.replace(/\/$/, ''))).size === cleanedCompareUrls.length;

  const runState = status?.run_state || 'IDLE';
  const agentCanStart =
    runState === 'IDLE' ||
    runState === 'COMPLETED' ||
    runState === 'STOPPED' ||
    runState === 'FAILED';

  const uniqueValid = uniqueUrl.trim().startsWith('http');

  const canStartUnique = agentCanStart && uniqueValid;

  const updateCompareUrl = (index: number, value: string) => {
    setCompareUrls((prev) => prev.map((u, i) => (i === index ? value : u)));
    setCompareReady(false);
  };

  const addCompareUrl = () => {
    setCompareUrls((prev) => [...prev, '']);
    setCompareReady(false);
  };

  const removeCompareUrl = (index: number) => {
    if (compareUrls.length <= 2) return;
    setCompareUrls((prev) => prev.filter((_, i) => i !== index));
    setCompareReady(false);
  };
  const canStartCompare = agentCanStart && compareValid;

  const canPause = runState === 'RUNNING';
  const canResume = runState === 'PAUSED';
  const canStop =
    runState === 'RUNNING' ||
    runState === 'PAUSED' ||
    runState === 'PAUSE_REQUESTED' ||
    runState === 'VALIDATING';

  const currentTech = TECHNOLOGIES.find((t) => t.key === selectedTechnology) || TECHNOLOGIES[0];

  const noteFoundText = `${currentTech.name} found`;
  const noteNotFoundText = `${currentTech.name} not found`;

  const checkPlan = async () => {
    setBusy(true);
    setCompareHint(null);
    setCompareReady(false);
    try {
      const res = await resolveComparison(selectedTechnology, cleanedCompareUrls);
      setCompareHint(res.message);
      setCompareReady(res.ready);
    } catch (e) {
      setCompareHint(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const handleStartUnique = async () => {
    if (!uniqueValid) return;
    setBusy(true);
    try {
      const res = await startRun(selectedTechnology, uniqueUrl.trim());
      if (!res.success) {
        setCompareHint(res.message);
        return;
      }
      onRunStarted();
    } catch (e) {
      alert('Error starting run: ' + String(e));
    } finally {
      setBusy(false);
    }
  };

  const handleStartComparison = async () => {
    if (!compareValid) return;
    setBusy(true);
    try {
      const res = await startComparisonRun(selectedTechnology, cleanedCompareUrls);
      setCompareHint(res.message);
      if (res.success) onRunStarted();
    } catch (e) {
      setCompareHint(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const UrlField = ({
    value,
    onChange,
    placeholder,
    label,
  }: {
    value: string;
    onChange: (v: string) => void;
    placeholder: string;
    label: string;
  }) => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', flex: '1 1 280px' }}>
      <span style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-muted)' }}>{label}</span>
      <div style={urlBoxStyle}>
        <Search size={14} color="var(--accent-cyan)" style={{ flexShrink: 0 }} />
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          style={urlInputStyle}
        />
        {value ? (
          <button
            type="button"
            onClick={() => onChange('')}
            title="Clear"
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--text-dim)',
              cursor: 'pointer',
              padding: '2px',
              display: 'flex',
            }}
          >
            <X size={13} />
          </button>
        ) : null}
        {value.startsWith('http') ? (
          <a
            href={value}
            target="_blank"
            rel="noreferrer"
            style={{
              color: 'var(--accent-cyan)',
              fontSize: '11px',
              fontWeight: 600,
              display: 'flex',
              alignItems: 'center',
              gap: '3px',
              flexShrink: 0,
              textDecoration: 'none',
            }}
          >
            Open <ExternalLink size={10} />
          </a>
        ) : null}
      </div>
    </div>
  );

  return (
    <div
      className="agent-card"
      style={{
        padding: '14px 18px',
        display: 'flex',
        flexDirection: 'column',
        gap: '12px',
        background: '#ffffff',
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '10px',
        }}
      >
        <span
          style={{
            fontSize: '12px',
            fontWeight: 800,
            color: 'var(--text-muted)',
            textTransform: 'uppercase',
            letterSpacing: '0.06em',
          }}
        >
          Start screening
        </span>
        <div
          style={{
            display: 'inline-flex',
            borderRadius: 'var(--radius-sm)',
            border: '1px solid var(--border-medium)',
            overflow: 'hidden',
            background: '#f8fafc',
          }}
        >
          <button
            type="button"
            onClick={() => {
              setMode('unique');
              setCompareHint(null);
            }}
            style={{
              padding: '6px 14px',
              fontSize: '12px',
              fontWeight: 700,
              border: 'none',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              background: mode === 'unique' ? currentTech.color : 'transparent',
              color: mode === 'unique' ? '#fff' : 'var(--text-main)',
            }}
          >
            <Link2 size={13} />
            Unique search
          </button>
          <button
            type="button"
            onClick={() => {
              setMode('comparison');
              setCompareHint(null);
            }}
            style={{
              padding: '6px 14px',
              fontSize: '12px',
              fontWeight: 700,
              border: 'none',
              borderLeft: '1px solid var(--border-medium)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              background: mode === 'comparison' ? 'var(--accent-purple)' : 'transparent',
              color: mode === 'comparison' ? '#fff' : 'var(--text-main)',
            }}
          >
            <GitCompare size={13} />
            Comparison search
          </button>
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'flex-end', gap: '12px', flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', flexShrink: 0 }}>
          <span style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-muted)' }}>Technology</span>
          <select
            value={selectedTechnology}
            onChange={(e) => onSelectTechnology(e.target.value as TechnologyKey)}
            style={{
              background: '#ffffff',
              border: `1.5px solid ${currentTech.color}`,
              borderRadius: 'var(--radius-sm)',
              color: 'var(--text-main)',
              padding: '9px 12px',
              fontSize: '13px',
              fontWeight: 700,
              outline: 'none',
              cursor: 'pointer',
              minWidth: '140px',
            }}
          >
            {TECHNOLOGIES.map((t) => (
              <option key={t.key} value={t.key}>
                {t.name}
              </option>
            ))}
          </select>
        </div>

        {mode === 'unique' ? (
          <UrlField
            label="Instahyre search URL"
            value={uniqueUrl}
            onChange={setUniqueUrl}
            placeholder="Paste one filtered Instahyre URL…"
          />
        ) : null}
      </div>

      {mode === 'comparison' ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          <p style={{ fontSize: '11px', color: 'var(--text-dim)', margin: 0, lineHeight: 1.45 }}>
            Add older → newer links top to bottom. Links already in the DB are not screened again —
            only the <strong>last</strong> link is walked; everyone from earlier lists is skipped
            using stored run data.
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {compareUrls.map((url, index) => {
              const isTarget = index === compareUrls.length - 1;
              const label = isTarget
                ? `Link ${index + 1} — target (screen this)`
                : `Link ${index + 1} — reference (DB only)`;
              return (
                <div
                  key={index}
                  style={{
                    display: 'flex',
                    alignItems: 'flex-end',
                    gap: '8px',
                    flexWrap: 'wrap',
                  }}
                >
                  <div style={{ flex: 1, minWidth: '240px' }}>
                    <UrlField
                      label={label}
                      value={url}
                      onChange={(v) => updateCompareUrl(index, v)}
                      placeholder={
                        isTarget ? 'Newest Instahyre URL…' : 'Older list URL (already screened?)…'
                      }
                    />
                  </div>
                  {compareUrls.length > 2 ? (
                    <button
                      type="button"
                      className="btn btn-secondary"
                      onClick={() => removeCompareUrl(index)}
                      title="Remove link"
                      style={{ padding: '8px', marginBottom: '2px' }}
                    >
                      <Trash2 size={14} />
                    </button>
                  ) : null}
                </div>
              );
            })}
          </div>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={addCompareUrl}
            style={{
              alignSelf: 'flex-start',
              fontSize: '11px',
              padding: '6px 12px',
              gap: '6px',
              display: 'inline-flex',
              alignItems: 'center',
            }}
          >
            <Plus size={13} />
            Add another link
          </button>
        </div>
      ) : null}

      {mode === 'comparison' && compareHint ? (
        <p
          style={{
            fontSize: '11px',
            margin: 0,
            color: compareReady ? '#059669' : 'var(--text-dim)',
            lineHeight: 1.45,
          }}
        >
          {compareHint}
        </p>
      ) : null}

      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          flexWrap: 'wrap',
        }}
      >
        {mode === 'unique' ? (
          <button
            className="btn btn-primary"
            disabled={!canStartUnique || isLoading || busy}
            onClick={handleStartUnique}
            style={{
              padding: '8px 16px',
              fontSize: '13px',
              opacity: canStartUnique ? 1 : 0.45,
              background: canStartUnique
                ? `linear-gradient(135deg, ${currentTech.color} 0%, #4338ca 100%)`
                : undefined,
            }}
          >
            <Play size={14} fill="currentColor" />
            <span>Start {currentTech.name}</span>
          </button>
        ) : (
          <>
            <button
              className="btn btn-secondary"
              type="button"
              disabled={!compareValid || busy || isLoading}
              onClick={checkPlan}
              style={{ fontSize: '12px', padding: '8px 14px' }}
            >
              Check plan
            </button>
            <button
              className="btn btn-primary"
              type="button"
              disabled={!canStartCompare || busy || isLoading}
              onClick={handleStartComparison}
              style={{
                fontSize: '12px',
                padding: '8px 14px',
                gap: '6px',
                opacity: canStartCompare ? 1 : 0.45,
              }}
            >
              <Play size={13} />
              Start comparison
            </button>
          </>
        )}

        <span
          style={{
            width: '1px',
            height: '28px',
            background: 'var(--border-medium)',
            margin: '0 4px',
          }}
        />

        <button
          className="btn btn-amber"
          disabled={!canPause || isLoading}
          onClick={onPause}
          style={{ padding: '8px 12px', fontSize: '12px' }}
        >
          <Pause size={13} />
          <span>Pause</span>
        </button>
        <button
          className="btn btn-emerald"
          disabled={!canResume || isLoading}
          onClick={onResume}
          style={{ padding: '8px 12px', fontSize: '12px' }}
        >
          <RotateCcw size={13} />
          <span>Resume</span>
        </button>
        <button
          className="btn btn-rose"
          disabled={!canStop || isLoading}
          onClick={onStop}
          style={{ padding: '8px 12px', fontSize: '12px' }}
        >
          <Square size={13} />
          <span>Stop</span>
        </button>
      </div>

      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '8px',
          paddingTop: '6px',
          borderTop: '1px solid var(--border-medium)',
          fontSize: '11px',
          color: 'var(--text-dim)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
          <span style={{ color: 'var(--text-muted)', fontWeight: 600 }}>Notes on Instahyre:</span>
          <span className="code-tag" style={{ fontSize: '10.5px' }}>
            No GitHub found
          </span>
          <span
            className="code-tag"
            style={{ fontSize: '10.5px', color: '#34d399', borderColor: 'rgba(16, 185, 129, 0.3)' }}
          >
            {noteFoundText}
          </span>
          <span className="code-tag" style={{ fontSize: '10.5px' }}>
            {noteNotFoundText}
          </span>
        </div>
        <div>
          {status?.dry_run ? (
            <span style={{ color: '#ca8a04', display: 'flex', alignItems: 'center', gap: '4px' }}>
              <ShieldAlert size={12} />
              Dry-Run (no notes pushed)
            </span>
          ) : (
            <span style={{ color: '#059669', display: 'flex', alignItems: 'center', gap: '4px' }}>
              <Zap size={12} />
              Live mode · {currentTech.name}
            </span>
          )}
        </div>
      </div>
    </div>
  );
};