import React, { useState } from 'react';
import {
  Users,
  Search,
  ExternalLink,
  RefreshCw,
  Github,
  User,
  Star,
  CheckCircle2,
  AlertTriangle,
  Loader2,
  ShieldCheck,
  X,
  RotateCcw,
  Briefcase,
  FileSpreadsheet,
  MapPin,
} from 'lucide-react';
import { Candidate, TechnologyKey } from '../types';
import { TECHNOLOGIES } from './TechnologyCards';
import { exportToGoogleSheets } from '../services/api';

export const TECH_SHEET_MAP: Record<string, string> = {
  golang: 'https://docs.google.com/spreadsheets/d/14zM1ftrQp-L4ntK2YViWvf4AofG1PhfScKqcVYLcEoQ/edit?gid=0#gid=0',
  java: 'https://docs.google.com/spreadsheets/d/1WuolRAWx42Xhaw9kQWsmFJOH-ZlokiRC4t4Ha_Z1VUs/edit?gid=0#gid=0',
  javascript: 'https://docs.google.com/spreadsheets/d/1dYA8imxWunBDnd05V1Sjuk2_B9tVgFXXSg0ff7yqiJI/edit?gid=0#gid=0',
  frontend: 'https://docs.google.com/spreadsheets/d/1p4XpHbxkTxGzg25hOsFI5elqOeEE7RkNQIF4LIqKdHA/edit?gid=0#gid=0',
  qa_automation: 'https://docs.google.com/spreadsheets/d/1LqVNQb2yPVHytUkNsiiEFZ3wjjjHU_tTa6y3K2R93v0/edit?gid=0#gid=0',
  python: 'https://docs.google.com/spreadsheets/d/1UdJWZG1tcvuo_TAH61fVe58GeEf6eCjiVoZYXAmbkgI/edit?gid=0#gid=0',
  typescript: 'https://docs.google.com/spreadsheets/d/1dYA8imxWunBDnd05V1Sjuk2_B9tVgFXXSg0ff7yqiJI/edit?gid=0#gid=0',
};

const DEMO_BIG_COMPANIES = [
  'Google',
  'Microsoft',
  'Amazon',
  'Meta',
  'Uber',
  'Atlassian',
  'Goldman Sachs',
  'Stripe',
  'Adobe',
  'Salesforce',
  'Netflix',
  'Apple',
];

function getDemoOffers(candId: number): string[] {
  const first = DEMO_BIG_COMPANIES[candId % DEMO_BIG_COMPANIES.length];
  let second = DEMO_BIG_COMPANIES[(candId * 7 + 3) % DEMO_BIG_COMPANIES.length];
  if (first === second) {
    second = DEMO_BIG_COMPANIES[(candId + 1) % DEMO_BIG_COMPANIES.length];
  }
  return [first, second];
}

interface CandidateExplorerProps {
  candidates: Candidate[];
  total: number;
  search: string;
  onSearchChange: (val: string) => void;
  activeFilter: string;
  onFilterChange: (val: string) => void;
  onRefresh: () => void;
  selectedTechnology?: TechnologyKey;
  pageSize?: number;
  onPageSizeChange?: (size: number) => void;
}

export const CandidateExplorer: React.FC<CandidateExplorerProps> = ({
  candidates,
  total,
  search,
  onSearchChange,
  activeFilter,
  onFilterChange,
  onRefresh,
  selectedTechnology = 'golang',
  pageSize = 500,
  onPageSizeChange,
}) => {
  const currentTech = TECHNOLOGIES.find((t) => t.key === selectedTechnology) || TECHNOLOGIES[0];
  const currentSheetUrl = TECH_SHEET_MAP[selectedTechnology] || TECH_SHEET_MAP.golang;

  // Action states
  const [toastMessage, setToastMessage] = useState<{ type: 'success' | 'error' | 'info'; text: string } | null>(null);

  // Recruiter Decision state (Interested / Not Interested Demo)
  const [candidateDecisions, setCandidateDecisions] = useState<Record<number, 'INTERESTED' | 'NOT_INTERESTED'>>(() => {
    try {
      const saved = localStorage.getItem('candidate_decisions');
      return saved ? JSON.parse(saved) : {};
    } catch {
      return {};
    }
  });

  const handleSetDecision = (candId: number, decision: 'INTERESTED' | 'NOT_INTERESTED' | null) => {
    setCandidateDecisions((prev) => {
      const next = { ...prev };
      if (decision === null) {
        delete next[candId];
      } else {
        next[candId] = decision;
      }
      try {
        localStorage.setItem('candidate_decisions', JSON.stringify(next));
      } catch {}
      return next;
    });
  };

  const filterOptions = [
    { id: '', label: 'All Candidates' },
    { id: 'GITHUB_FOUND', label: 'GitHub Found' },
    { id: 'GITHUB_NOT_FOUND', label: 'GitHub Missing' },
    { id: 'GO_DETECTED', label: `${currentTech.name} Detected` },
    { id: 'GO_NOT_DETECTED', label: `${currentTech.name} Not Found` },
    { id: 'NOTE_ADDED', label: 'Note Added' },
    { id: 'NOTE_ALREADY_EXISTS', label: 'Notes Existed' },
    { id: 'NEEDS_REVIEW', label: 'Needs Review' },
    { id: 'GITROLL_SCORED', label: 'GitScore' },
  ];

  const getTechStatusBadge = (status?: string, githubUrl?: string | null) => {
    if (!githubUrl || status === 'GITHUB_NOT_FOUND') {
      return (
        <span
          className="status-pill"
          style={{
            background: 'rgba(100, 116, 139, 0.12)',
            color: 'var(--text-dim)',
            border: '1px solid rgba(100, 116, 139, 0.25)',
          }}
        >
          NO GITHUB
        </span>
      );
    }
    if (status && status.endsWith('_DETECTED') && !status.includes('NOT')) {
      return (
        <span
          className="status-pill pill-completed"
          style={{
            background: 'rgba(16, 185, 129, 0.15)',
            color: '#34d399',
            borderColor: 'rgba(16, 185, 129, 0.4)',
          }}
        >
          ✓ {currentTech.name.toUpperCase()} DETECTED
        </span>
      );
    }
    if (status && status.includes('NOT_DETECTED')) {
      return (
        <span className="status-pill pill-idle">
          {currentTech.name.toUpperCase()} NOT FOUND
        </span>
      );
    }
    if (['CHECK_INCOMPLETE', 'API_RATE_LIMITED', 'API_ERROR'].includes(status || '')) {
      return <span className="status-pill pill-paused">NEEDS REVIEW</span>;
    }
    return (
      <span style={{ color: 'var(--text-dim)', fontSize: '11px', fontFamily: 'var(--font-mono)' }}>
        UNCHECKED
      </span>
    );
  };

  const getLanguagesFoundBadge = (cand: Candidate, latestResult?: any) => {
    const raw = cand.languages_found || latestResult?.languages_found;
    if (!cand.github_url) {
      return (
        <span style={{ color: 'var(--text-dim)', fontSize: '11px', fontFamily: 'var(--font-mono)' }}>
          No GitHub found
        </span>
      );
    }
    if (raw) {
      if (raw.toLowerCase().includes('not found')) {
        return (
          <span
            className="status-pill pill-idle"
            style={{
              background: 'rgba(239, 68, 68, 0.08)',
              color: '#f87171',
              border: '1px solid rgba(239, 68, 68, 0.25)',
              fontSize: '11px',
              fontWeight: 600,
            }}
          >
            {raw}
          </span>
        );
      }
      const parts = raw.split(', ');
      return (
        <div style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', flexWrap: 'nowrap' }}>
          {parts.map((p: string, i: number) => (
            <span
              key={i}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                padding: '2px 7px',
                borderRadius: '4px',
                fontSize: '11px',
                fontWeight: 700,
                background: 'rgba(16, 185, 129, 0.15)',
                border: '1px solid rgba(16, 185, 129, 0.4)',
                color: '#34d399',
                whiteSpace: 'nowrap',
              }}
            >
              ✓ {p}
            </span>
          ))}
        </div>
      );
    }
    return <span style={{ color: 'var(--text-dim)', fontSize: '11px' }}>—</span>;
  };

  const getNoteStatusBadge = (noteAction?: { action_status: string; note_text: string }) => {
    if (!noteAction) return <span style={{ color: 'var(--text-dim)', fontSize: '11px' }}>NONE</span>;
    switch (noteAction.action_status) {
      case 'NOTE_ADDED':
        return (
          <span
            className="status-pill pill-completed"
            title={noteAction.note_text}
            style={{ maxWidth: '240px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
          >
            ADDED: {noteAction.note_text}
          </span>
        );
      case 'NOTE_ALREADY_EXISTS':
        return (
          <span
            className="status-pill"
            style={{
              background: 'rgba(245, 158, 11, 0.12)',
              color: '#fbbf24',
              border: '1px solid rgba(245, 158, 11, 0.35)',
              maxWidth: '240px',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}
            title={noteAction.note_text}
          >
            EXISTED: {noteAction.note_text}
          </span>
        );
      case 'RATE_LIMITED':
        return (
          <span
            className="status-pill"
            style={{
              background: 'rgba(245, 158, 11, 0.15)',
              color: '#f59e0b',
              border: '1px solid rgba(245, 158, 11, 0.45)',
              maxWidth: '240px',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}
            title="Instahyre daily note limit reached (125/day); queued for quota reset"
          >
            QUEUED: {noteAction.note_text}
          </span>
        );
      case 'NOTE_FAILED':
        return <span className="status-pill pill-failed">FAILED</span>;
      case 'SKIPPED':
        return <span className="status-pill pill-idle">SKIPPED</span>;
      default:
        return <span className="status-pill pill-idle">{noteAction.action_status}</span>;
    }
  };

  const getInitials = (name?: string) => {
    if (!name) return '??';
    const parts = name.trim().split(/\s+/);
    if (parts.length >= 2) return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
    return name.slice(0, 2).toUpperCase();
  };

  const [isExporting, setIsExporting] = useState(false);

  const handleExportToGoogleSheets = async () => {
    setIsExporting(true);
    try {
      const sheetUrl = currentSheetUrl;
      const res = await exportToGoogleSheets(selectedTechnology, sheetUrl);
      if (res.success) {
        setToastMessage({
          type: 'success',
          text: `Success! Exported ${res.count} candidates who have a GitRoll score, with salary, location, and experience.`,
        });
      } else {
        setToastMessage({
          type: 'error',
          text: res.message || 'Export failed',
        });
      }
    } catch (err: any) {
      setToastMessage({
        type: 'error',
        text: err.message || 'Failed to export to Google Sheet',
      });
    } finally {
      setIsExporting(false);
    }
  };

  const filteredCandidates = React.useMemo(() => {
    if (!activeFilter) return candidates;
    return candidates.filter((cand) => {
      const latestResult = cand.screening_results?.[cand.screening_results.length - 1];
      const latestNote = cand.note_actions?.[cand.note_actions.length - 1];

      switch (activeFilter) {
        case 'GITHUB_FOUND':
          return Boolean(cand.github_url && cand.github_url.trim());
        case 'GITHUB_NOT_FOUND':
          return !cand.github_url || !cand.github_url.trim();
        case 'GO_DETECTED':
          return Boolean(latestResult?.go_status && latestResult.go_status.endsWith('_DETECTED') && !latestResult.go_status.includes('NOT'));
        case 'GO_NOT_DETECTED':
          return Boolean(latestResult?.go_status && latestResult.go_status.includes('NOT_DETECTED'));
        case 'NOTE_ADDED':
          return latestNote?.action_status === 'NOTE_ADDED';
        case 'NOTE_ALREADY_EXISTS':
          return latestNote?.action_status === 'NOTE_ALREADY_EXISTS';
        case 'NEEDS_REVIEW':
          return ['CHECK_INCOMPLETE', 'API_RATE_LIMITED', 'API_ERROR'].includes(
            latestResult?.go_status || ''
          );
        case 'GITROLL_SCORED':
          return (
            cand.gitroll_rating !== null &&
            cand.gitroll_rating !== undefined &&
            Boolean(latestResult?.go_status && latestResult.go_status.endsWith('_DETECTED') && !latestResult.go_status.includes('NOT'))
          );
        default:
          return true;
      }
    });
  }, [candidates, activeFilter]);

  return (
    <div className="agent-card" style={{ position: 'relative' }}>
      {/* Toast Alert Banner */}
      {toastMessage && (
        <div
          style={{
            marginBottom: '14px',
            padding: '10px 16px',
            borderRadius: '8px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            fontSize: '13px',
            fontWeight: 500,
            background:
              toastMessage.type === 'success'
                ? 'rgba(16, 185, 129, 0.15)'
                : toastMessage.type === 'error'
                ? 'rgba(239, 68, 68, 0.15)'
                : 'rgba(56, 189, 248, 0.15)',
            border: `1px solid ${
              toastMessage.type === 'success'
                ? 'rgba(16, 185, 129, 0.4)'
                : toastMessage.type === 'error'
                ? 'rgba(239, 68, 68, 0.4)'
                : 'rgba(56, 189, 248, 0.4)'
            }`,
            color:
              toastMessage.type === 'success'
                ? '#34d399'
                : toastMessage.type === 'error'
                ? '#f87171'
                : '#38bdf8',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            {toastMessage.type === 'success' && <CheckCircle2 size={16} />}
            {toastMessage.type === 'error' && <AlertTriangle size={16} />}
            {toastMessage.type === 'info' && <ShieldCheck size={16} />}
            <span>{toastMessage.text}</span>
          </div>
          <button
            type="button"
            onClick={() => setToastMessage(null)}
            style={{ background: 'transparent', border: 'none', color: 'inherit', cursor: 'pointer', padding: '2px' }}
          >
            <X size={14} />
          </button>
        </div>
      )}

      {/* Table Header Controls */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '14px',
          marginBottom: '16px',
        }}
      >
        <div className="card-title" style={{ margin: 0 }}>
          <Users size={16} color="var(--accent-primary)" />
          <span>Candidate Explorer</span>
          <span
            style={{
              fontSize: '12px',
              color: 'var(--text-dim)',
              textTransform: 'none',
              marginLeft: '6px',
              fontWeight: 500,
            }}
          >
            ({filteredCandidates.length}
            {total > filteredCandidates.length ? ` of ${total}` : ''} in {currentTech.dbFileName})
          </span>
        </div>

        {/* Search bar & Refresh */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
          <div style={{ position: 'relative', width: '260px' }}>
            <Search
              size={14}
              style={{ position: 'absolute', left: '11px', top: '11px', color: 'var(--text-dim)' }}
            />
            <input
              type="text"
              placeholder="Filter by name or GitHub handle..."
              value={search}
              onChange={(e) => onSearchChange(e.target.value)}
              style={{
                width: '100%',
                background: 'rgba(6, 10, 20, 0.9)',
                border: '1px solid var(--border-medium)',
                borderRadius: 'var(--radius-sm)',
                padding: '8px 12px 8px 34px',
                color: '#ffffff',
                fontSize: '12px',
                outline: 'none',
                fontFamily: 'var(--font-sans)',
                transition: 'border-color 0.2s',
              }}
            />
          </div>

          {/* Page Size Selector */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              fontSize: '11px',
              color: 'var(--text-dim)',
              background: 'rgba(6, 10, 20, 0.7)',
              padding: '3px 6px',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--border-subtle)',
            }}
          >
            <span style={{ fontWeight: 600, paddingLeft: '2px' }}>Show:</span>
            {[50, 100, 500].map((size) => (
              <button
                key={size}
                type="button"
                onClick={() => onPageSizeChange?.(size)}
                style={{
                  background: pageSize === size ? 'var(--accent-primary)' : 'transparent',
                  color: pageSize === size ? '#ffffff' : 'var(--text-muted)',
                  border: pageSize === size ? '1px solid var(--accent-primary)' : '1px solid transparent',
                  borderRadius: '4px',
                  padding: '2px 7px',
                  fontSize: '11px',
                  fontWeight: pageSize === size ? 700 : 500,
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                }}
              >
                {size === 500 ? 'All' : size}
              </button>
            ))}
          </div>

          <button
            className="btn btn-secondary"
            onClick={onRefresh}
            style={{ padding: '7px 14px', fontSize: '12px', gap: '6px' }}
          >
            <RefreshCw size={13} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Filter Tabs & GitRoll Rating Button Row */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          gap: '12px',
          paddingBottom: '14px',
          flexWrap: 'wrap',
        }}
      >
        <div style={{ display: 'flex', gap: '8px', overflowX: 'auto' }}>
          {filterOptions.map((f) => {
            const isSelected = activeFilter === f.id;
            return (
              <button
                key={f.id}
                onClick={() => onFilterChange(f.id)}
                style={{
                  background: isSelected ? 'var(--accent-primary)' : 'rgba(255, 255, 255, 0.04)',
                  color: isSelected ? '#ffffff' : 'var(--text-muted)',
                  border: isSelected ? '1px solid var(--accent-primary)' : '1px solid var(--border-subtle)',
                  borderRadius: '20px',
                  padding: '5px 13px',
                  fontSize: '12px',
                  fontWeight: isSelected ? 700 : 500,
                  cursor: 'pointer',
                  whiteSpace: 'nowrap',
                  transition: 'all 0.18s ease',
                  boxShadow: isSelected ? '0 0 12px rgba(99, 102, 241, 0.4)' : 'none',
                }}
              >
                {f.label}
              </button>
            );
          })}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
          {/* Open Google Sheet Button */}
          <a
            href={currentSheetUrl}
            target="_blank"
            rel="noopener noreferrer"
            id="open-google-sheet-btn"
            title={`Open ${currentTech.name} Google Sheet (${currentSheetUrl})`}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '7px',
              padding: '7px 16px',
              borderRadius: '20px',
              background: 'linear-gradient(135deg, rgba(14, 165, 233, 0.16) 0%, rgba(99, 102, 241, 0.22) 100%)',
              border: '1px solid rgba(56, 189, 248, 0.5)',
              color: '#38bdf8',
              fontSize: '12px',
              fontWeight: 700,
              cursor: 'pointer',
              textDecoration: 'none',
              boxShadow: '0 0 14px rgba(56, 189, 248, 0.25)',
              transition: 'all 0.2s cubic-bezier(0.16, 1, 0.3, 1)',
              whiteSpace: 'nowrap',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'linear-gradient(135deg, rgba(14, 165, 233, 0.32) 0%, rgba(99, 102, 241, 0.4) 100%)';
              e.currentTarget.style.borderColor = 'rgba(56, 189, 248, 0.85)';
              e.currentTarget.style.boxShadow = '0 0 20px rgba(56, 189, 248, 0.5)';
              e.currentTarget.style.transform = 'translateY(-1px)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'linear-gradient(135deg, rgba(14, 165, 233, 0.16) 0%, rgba(99, 102, 241, 0.22) 100%)';
              e.currentTarget.style.borderColor = 'rgba(56, 189, 248, 0.5)';
              e.currentTarget.style.boxShadow = '0 0 14px rgba(56, 189, 248, 0.25)';
              e.currentTarget.style.transform = 'translateY(0)';
            }}
          >
            <ExternalLink size={13} color="#38bdf8" />
            <span>Open Sheet</span>
          </a>

          {/* Export to Google Sheet Button */}
          <button
            type="button"
            id="export-google-sheets-btn"
            disabled={isExporting}
            onClick={handleExportToGoogleSheets}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '7px',
              padding: '7px 18px',
              borderRadius: '20px',
              background: isExporting
                ? 'rgba(100, 116, 139, 0.4)'
                : 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
              border: '1px solid rgba(52, 211, 153, 0.6)',
              color: '#ffffff',
              fontSize: '12px',
              fontWeight: 700,
              cursor: isExporting ? 'not-allowed' : 'pointer',
              boxShadow: isExporting ? 'none' : '0 0 16px rgba(16, 185, 129, 0.35)',
              transition: 'all 0.2s ease',
              whiteSpace: 'nowrap',
            }}
          >
            {isExporting ? (
              <>
                <Loader2 size={14} className="spin" />
                <span>Exporting to Sheet...</span>
              </>
            ) : (
              <>
                <FileSpreadsheet size={14} color="#ffffff" />
                <span>Export to Google Sheet</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Table with internal scrollbar and sticky header */}
      <div
        className="data-table-container"
        style={{
          maxHeight: '520px',
          overflowY: 'auto',
          overflowX: 'auto',
        }}
      >
        <table className="data-table">
          <thead
            style={{
              position: 'sticky',
              top: 0,
              zIndex: 10,
            }}
          >
            <tr>
              <th style={{ width: '45px', whiteSpace: 'nowrap' }}>ID</th>
              <th style={{ minWidth: '160px', whiteSpace: 'nowrap' }}>Candidate Name</th>
              <th style={{ width: '1%', whiteSpace: 'nowrap' }}>Instahyre Profile</th>
              <th style={{ width: '1%', whiteSpace: 'nowrap' }}>GitHub URL</th>
              <th style={{ width: '1%', whiteSpace: 'nowrap' }}>Offers From</th>
              <th style={{ width: '1%', whiteSpace: 'nowrap' }}>Current Salary</th>
              <th style={{ width: '1%', whiteSpace: 'nowrap' }}>Location</th>
              <th style={{ width: '1%', whiteSpace: 'nowrap' }}>Experience</th>
              <th style={{ width: '1%', whiteSpace: 'nowrap' }}>Coding Profiles</th>
              <th style={{ width: '1%', whiteSpace: 'nowrap' }}>{currentTech.name} Status</th>
              <th style={{ width: '1%', whiteSpace: 'nowrap' }}>Languages Found</th>
              <th style={{ width: '1%', whiteSpace: 'nowrap' }}>GitScore</th>
              <th style={{ whiteSpace: 'nowrap' }}>Instahyre Note Action</th>
              <th style={{ width: '1%', whiteSpace: 'nowrap' }}>Last Checked</th>
              <th style={{ width: '1%', whiteSpace: 'nowrap', textAlign: 'center' }}>Decision</th>
            </tr>
          </thead>
          <tbody>
            {filteredCandidates.length === 0 ? (
              <tr>
                <td colSpan={15} style={{ textAlign: 'center', padding: '36px', color: 'var(--text-dim)' }}>
                  No candidate records match the active criteria in {currentTech.dbFileName}.
                </td>
              </tr>
            ) : (
              filteredCandidates.map((cand) => {
                const latestResult = cand.screening_results?.[cand.screening_results.length - 1];
                const latestNote = cand.note_actions?.[cand.note_actions.length - 1];
                const checkedTime = cand.last_seen_at
                  ? new Date(cand.last_seen_at).toLocaleTimeString()
                  : '—';
                const isDetected = Boolean(latestResult?.go_status && latestResult.go_status.endsWith('_DETECTED') && !latestResult.go_status.includes('NOT'));

                return (
                  <tr key={cand.id}>
                    <td style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-dim)', fontSize: '11px' }}>
                      #{cand.id}
                    </td>

                    {/* Candidate Name with Avatar Initial */}
                    <td style={{ whiteSpace: 'nowrap' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <div
                          style={{
                            width: '28px',
                            height: '28px',
                            borderRadius: '50%',
                            background:
                              'linear-gradient(135deg, rgba(99, 102, 241, 0.25) 0%, rgba(6, 182, 212, 0.25) 100%)',
                            border: '1px solid rgba(255, 255, 255, 0.12)',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            fontSize: '11px',
                            fontWeight: 700,
                            color: '#e2e8f0',
                            fontFamily: 'var(--font-display)',
                            flexShrink: 0,
                          }}
                        >
                          {getInitials(cand.name)}
                        </div>
                        <span style={{ fontWeight: 600, color: '#f8fafc' }}>
                          {cand.name}
                        </span>
                      </div>
                    </td>

                    {/* Instahyre Profile Link */}
                    <td style={{ whiteSpace: 'nowrap' }}>
                      <a
                        href={cand.instahyre_profile_url}
                        target="_blank"
                        rel="noreferrer"
                        style={{
                          color: 'var(--accent-cyan)',
                          textDecoration: 'none',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '5px',
                          fontSize: '12px',
                          fontWeight: 500,
                        }}
                      >
                        <User size={12} />
                        <span>Profile</span>
                        <ExternalLink size={10} />
                      </a>
                    </td>

                    {/* GitHub Link */}
                    <td style={{ whiteSpace: 'nowrap' }}>
                      {cand.github_url ? (
                        <a
                          href={cand.github_url}
                          target="_blank"
                          rel="noreferrer"
                          style={{
                            color: '#93c5fd',
                            textDecoration: 'none',
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '6px',
                            fontFamily: 'var(--font-mono)',
                            fontSize: '12px',
                          }}
                        >
                          <Github size={13} />
                          <span>{cand.github_url.replace('https://github.com/', '')}</span>
                          <ExternalLink size={10} />
                        </a>
                      ) : (
                        <span style={{ color: 'var(--text-dim)', fontSize: '11px' }}>Not Found</span>
                      )}
                    </td>

                    {/* Offers From (Demo for all detected candidates) */}
                    <td style={{ whiteSpace: 'nowrap' }}>
                      {isDetected ? (
                        <div style={{ display: 'inline-flex', alignItems: 'center', gap: '5px' }}>
                          {getDemoOffers(cand.id).map((company) => (
                            <span
                              key={company}
                              style={{
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: '3px',
                                padding: '2px 7px',
                                borderRadius: '4px',
                                fontSize: '11px',
                                fontWeight: 600,
                                background: 'rgba(56, 189, 248, 0.1)',
                                border: '1px solid rgba(56, 189, 248, 0.28)',
                                color: '#7dd3fc',
                                whiteSpace: 'nowrap',
                              }}
                            >
                              <Briefcase size={10} color="#38bdf8" />
                              {company}
                            </span>
                          ))}
                        </div>
                      ) : (
                        <span style={{ color: 'var(--text-dim)', fontSize: '12px' }}>—</span>
                      )}
                    </td>

                    {/* Current Salary (Extracted from Instahyre profile / search card) */}
                    <td style={{ whiteSpace: 'nowrap' }}>
                      {cand.current_salary ? (
                        <span
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '4px',
                            padding: '2.5px 8px',
                            borderRadius: '4px',
                            fontSize: '11px',
                            fontWeight: 700,
                            fontFamily: 'var(--font-mono)',
                            background: 'rgba(16, 185, 129, 0.12)',
                            border: '1px solid rgba(16, 185, 129, 0.3)',
                            color: '#34d399',
                            whiteSpace: 'nowrap',
                          }}
                        >
                          {cand.current_salary}
                        </span>
                      ) : (
                        <span style={{ color: 'var(--text-dim)', fontSize: '11px' }}>—</span>
                      )}
                    </td>

                    {/* Location (Extracted from Instahyre profile / search card) */}
                    <td style={{ whiteSpace: 'nowrap' }}>
                      {cand.location ? (
                        <span
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '4px',
                            padding: '2.5px 8px',
                            borderRadius: '4px',
                            fontSize: '11px',
                            fontWeight: 600,
                            background: 'rgba(56, 189, 248, 0.1)',
                            border: '1px solid rgba(56, 189, 248, 0.25)',
                            color: '#38bdf8',
                            whiteSpace: 'nowrap',
                          }}
                        >
                          <MapPin size={11} />
                          {cand.location}
                        </span>
                      ) : (
                        <span style={{ color: 'var(--text-dim)', fontSize: '11px' }}>—</span>
                      )}
                    </td>

                    <td style={{ whiteSpace: 'nowrap' }}>
                      {cand.experience ? (
                        <span
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '4px',
                            padding: '2.5px 8px',
                            borderRadius: '4px',
                            fontSize: '11px',
                            fontWeight: 600,
                            background: 'rgba(168, 85, 247, 0.1)',
                            border: '1px solid rgba(168, 85, 247, 0.25)',
                            color: '#d8b4fe',
                            whiteSpace: 'nowrap',
                          }}
                        >
                          {cand.experience}
                        </span>
                      ) : (
                        <span style={{ color: 'var(--text-dim)', fontSize: '11px' }}>—</span>
                      )}
                    </td>

                    {/* Coding Profiles (LeetCode, HackerRank, CodeChef, ICPC) */}
                    <td style={{ whiteSpace: 'nowrap' }}>
                      {cand.coding_profiles ? (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'nowrap' }}>
                          {cand.coding_profiles.split(' | ').map((part, idx) => {
                            const isUrl = part.includes('http');
                            if (isUrl) {
                              const [platform, url] = part.split(': ');
                              return (
                                <a
                                  key={idx}
                                  href={url}
                                  target="_blank"
                                  rel="noreferrer"
                                  title={`Open ${platform} Profile`}
                                  style={{
                                    display: 'inline-flex',
                                    alignItems: 'center',
                                    gap: '3px',
                                    padding: '2px 7px',
                                    borderRadius: '4px',
                                    fontSize: '11px',
                                    fontWeight: 700,
                                    background: 'rgba(245, 158, 11, 0.12)',
                                    border: '1px solid rgba(245, 158, 11, 0.35)',
                                    color: '#fbbf24',
                                    textDecoration: 'none',
                                  }}
                                >
                                  <span>{platform}</span>
                                  <ExternalLink size={10} />
                                </a>
                              );
                            }
                            return (
                              <span
                                key={idx}
                                style={{
                                  display: 'inline-flex',
                                  alignItems: 'center',
                                  padding: '2px 7px',
                                  borderRadius: '4px',
                                  fontSize: '11px',
                                  fontWeight: 700,
                                  background: 'rgba(245, 158, 11, 0.08)',
                                  border: '1px solid rgba(245, 158, 11, 0.25)',
                                  color: '#fde68a',
                                }}
                              >
                                {part}
                              </span>
                            );
                          })}
                        </div>
                      ) : (
                        <span style={{ color: 'var(--text-dim)', fontSize: '11px' }}>—</span>
                      )}
                    </td>

                    {/* Tech Status */}
                    <td style={{ whiteSpace: 'nowrap' }}>
                      {getTechStatusBadge(latestResult?.go_status, cand.github_url)}
                    </td>

                    {/* Languages Found */}
                    <td style={{ whiteSpace: 'nowrap' }}>
                      {getLanguagesFoundBadge(cand, latestResult)}
                    </td>

                    {/* GitScore Column */}
                    <td style={{ whiteSpace: 'nowrap' }}>
                      {isDetected ? (
                        cand.gitroll_rating !== null && cand.gitroll_rating !== undefined ? (
                          <div
                            style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '6px',
                              padding: '3px 10px',
                              borderRadius: '6px',
                              background: 'linear-gradient(135deg, rgba(234, 179, 8, 0.18) 0%, rgba(249, 115, 22, 0.18) 100%)',
                              border: '1px solid rgba(234, 179, 8, 0.5)',
                              color: '#fef08a',
                              fontWeight: 700,
                              fontSize: '13px',
                              width: 'fit-content',
                            }}
                          >
                            <Star size={13} fill="#eab308" color="#eab308" />
                            <span>{cand.gitroll_rating.toFixed(2)}</span>
                          </div>
                        ) : (
                          <span style={{ color: 'var(--text-dim)', fontSize: '12px' }}>—</span>
                        )
                      ) : (
                        <span style={{ color: 'var(--text-dim)', fontSize: '12px' }}>—</span>
                      )}
                    </td>

                    {/* Note Action */}
                    <td>
                      {getNoteStatusBadge(latestNote)}
                    </td>

                    {/* Timestamp */}
                    <td style={{ color: 'var(--text-dim)', fontSize: '11px', fontFamily: 'var(--font-mono)', whiteSpace: 'nowrap' }}>
                      {checkedTime}
                    </td>

                    {/* Decision (Interested / Not Interested Demo) */}
                    <td style={{ whiteSpace: 'nowrap', textAlign: 'center' }}>
                      {candidateDecisions[cand.id] === 'INTERESTED' ? (
                        <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                          <span
                            style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '5px',
                              padding: '3px 10px',
                              borderRadius: '5px',
                              fontSize: '11px',
                              fontWeight: 700,
                              background: 'rgba(16, 185, 129, 0.2)',
                              border: '1.5px solid #10b981',
                              color: '#6ee7b7',
                              boxShadow: '0 0 10px rgba(16, 185, 129, 0.25)',
                              whiteSpace: 'nowrap',
                            }}
                          >
                            <CheckCircle2 size={12} color="#10b981" />
                            Interested
                          </span>
                          <button
                            type="button"
                            onClick={() => handleSetDecision(cand.id, null)}
                            title="Reset decision"
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
                            <RotateCcw size={11} />
                          </button>
                        </div>
                      ) : candidateDecisions[cand.id] === 'NOT_INTERESTED' ? (
                        <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                          <span
                            style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '5px',
                              padding: '3px 10px',
                              borderRadius: '5px',
                              fontSize: '11px',
                              fontWeight: 700,
                              background: 'rgba(239, 68, 68, 0.2)',
                              border: '1.5px solid #ef4444',
                              color: '#fca5a5',
                              boxShadow: '0 0 10px rgba(239, 68, 68, 0.25)',
                              whiteSpace: 'nowrap',
                            }}
                          >
                            <X size={12} color="#ef4444" strokeWidth={2.5} />
                            Not Interested
                          </span>
                          <button
                            type="button"
                            onClick={() => handleSetDecision(cand.id, null)}
                            title="Reset decision"
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
                            <RotateCcw size={11} />
                          </button>
                        </div>
                      ) : (
                        <div style={{ display: 'inline-flex', alignItems: 'center', gap: '5px' }}>
                          <button
                            type="button"
                            onClick={() => handleSetDecision(cand.id, 'INTERESTED')}
                            title="Mark as Interested"
                            style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '4px',
                              padding: '3px 8px',
                              borderRadius: '4px',
                              fontSize: '11px',
                              fontWeight: 600,
                              background: 'rgba(16, 185, 129, 0.12)',
                              border: '1px solid rgba(16, 185, 129, 0.35)',
                              color: '#34d399',
                              cursor: 'pointer',
                              transition: 'all 0.15s ease',
                              whiteSpace: 'nowrap',
                            }}
                          >
                            <CheckCircle2 size={11} />
                            <span>Interested</span>
                          </button>
                          <button
                            type="button"
                            onClick={() => handleSetDecision(cand.id, 'NOT_INTERESTED')}
                            title="Mark as Not Interested"
                            style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '4px',
                              padding: '3px 8px',
                              borderRadius: '4px',
                              fontSize: '11px',
                              fontWeight: 600,
                              background: 'rgba(239, 68, 68, 0.12)',
                              border: '1px solid rgba(239, 68, 68, 0.35)',
                              color: '#f87171',
                              cursor: 'pointer',
                              transition: 'all 0.15s ease',
                              whiteSpace: 'nowrap',
                            }}
                          >
                            <X size={11} />
                            <span>Not Interested</span>
                          </button>
                        </div>
                      )}
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
