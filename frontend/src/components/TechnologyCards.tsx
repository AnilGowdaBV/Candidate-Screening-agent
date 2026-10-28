import React from 'react';
import { TechnologyKey } from '../types';
import { Database, Sparkles, CheckCircle2 } from 'lucide-react';

export interface TechCardInfo {
  key: TechnologyKey;
  name: string;
  dbFileName: string;
  color: string;
  bgColor: string;
  glowColor: string;
  borderColor: string;
}

export const TECHNOLOGIES: TechCardInfo[] = [
  {
    key: 'golang',
    name: 'Go lang',
    dbFileName: 'screening_golang.db',
    color: '#00ADD8',
    bgColor: 'rgba(0, 173, 216, 0.12)',
    glowColor: 'rgba(0, 173, 216, 0.35)',
    borderColor: 'rgba(0, 173, 216, 0.5)',
  },
  {
    key: 'python',
    name: 'Python',
    dbFileName: 'screening_python.db',
    color: '#38BDF8',
    bgColor: 'rgba(56, 189, 248, 0.12)',
    glowColor: 'rgba(56, 189, 248, 0.35)',
    borderColor: 'rgba(56, 189, 248, 0.5)',
  },
  {
    key: 'java',
    name: 'Java',
    dbFileName: 'screening_java.db',
    color: '#F97316',
    bgColor: 'rgba(249, 115, 22, 0.12)',
    glowColor: 'rgba(249, 115, 22, 0.35)',
    borderColor: 'rgba(249, 115, 22, 0.5)',
  },
  {
    key: 'javascript',
    name: 'JavaScript',
    dbFileName: 'screening_javascript.db',
    color: '#FACC15',
    bgColor: 'rgba(250, 204, 21, 0.12)',
    glowColor: 'rgba(250, 204, 21, 0.35)',
    borderColor: 'rgba(250, 204, 21, 0.5)',
  },
  {
    key: 'typescript',
    name: 'TypeScript',
    dbFileName: 'screening_typescript.db',
    color: '#60A5FA',
    bgColor: 'rgba(96, 165, 250, 0.12)',
    glowColor: 'rgba(96, 165, 250, 0.35)',
    borderColor: 'rgba(96, 165, 250, 0.5)',
  },
  {
    key: 'frontend',
    name: 'Frontend',
    dbFileName: 'screening_frontend.db',
    color: '#EC4899',
    bgColor: 'rgba(236, 72, 153, 0.12)',
    glowColor: 'rgba(236, 72, 153, 0.35)',
    borderColor: 'rgba(236, 72, 153, 0.5)',
  },
  {
    key: 'qa_automation',
    name: 'QA Automation',
    dbFileName: 'screening_qa_automation.db',
    color: '#10B981',
    bgColor: 'rgba(16, 185, 129, 0.12)',
    glowColor: 'rgba(16, 185, 129, 0.35)',
    borderColor: 'rgba(16, 185, 129, 0.5)',
  },
];

// Rich Vector Icons for Technologies
const TechIcon: React.FC<{ tech: TechnologyKey; size?: number }> = ({ tech, size = 22 }) => {
  switch (tech) {
    case 'golang':
      return (
        <svg width={size} height={size} viewBox="0 0 48 48" fill="none">
          <circle cx="24" cy="24" r="22" fill="#00ADD8" fillOpacity="0.18" stroke="#00ADD8" strokeWidth="1.5" />
          <path d="M12 24c0-5 3.5-9 8.5-9 3.5 0 6 1.8 7 4.2l-3.3 1.8c-.8-1.5-2.2-2.4-3.7-2.4-3 0-4.8 2.3-4.8 5.4s1.8 5.4 4.8 5.4c1.5 0 3-1 3.7-2.4l3.3 1.8c-1 2.4-3.5 4.2-7 4.2-5 0-8.5-4-8.5-9z" fill="#00ADD8" />
          <path d="M29 20h11v4H33.2v5h-4.2V20z" fill="#00ADD8" />
        </svg>
      );
    case 'python':
      return (
        <svg width={size} height={size} viewBox="0 0 48 48" fill="none">
          <circle cx="24" cy="24" r="22" fill="#38BDF8" fillOpacity="0.15" stroke="#38BDF8" strokeWidth="1.5" />
          <path d="M23.5 12c-4.7 0-4.4 2-4.4 2l.01 2.1h4.5v.7h-6.4c-2.1 0-3.7 1.3-3.7 3.7 0 2.4 1.5 3.6 3.7 3.6h1.2v-1.7c0-2 1.7-3.7 3.7-3.7h4.4c1.7 0 3-1.3 3-3V15c0-1.7-1.3-3-3-3h-3.01zm-1.3 1.6c.4 0 .7.3.7.7s-.3.7-.7.7-.7-.3-.7-.7.3-.7.7-.7z" fill="#38BDF8" />
          <path d="M24.5 36c4.7 0 4.4-2 4.4-2l-.01-2.1h-4.5v-.7h6.4c2.1 0 3.7-1.3 3.7-3.7 0-2.4-1.5-3.6-3.7-3.6h-1.2v1.7c0 2-1.7 3.7-3.7 3.7h-4.4c-1.7 0-3 1.3-3 3v2.7c0 1.7 1.3 3 3 3h3.01zm1.3-1.6c-.4 0-.7-.3-.7-.7s.3-.7.7-.7.7.3.7.7-.3.7-.7.7z" fill="#FACC15" />
        </svg>
      );
    case 'java':
      return (
        <svg width={size} height={size} viewBox="0 0 48 48" fill="none">
          <circle cx="24" cy="24" r="22" fill="#F97316" fillOpacity="0.15" stroke="#F97316" strokeWidth="1.5" />
          <path d="M21 13c1.5 2-1 3.5 0 5.5s3-1 2-3c-.8-1.5-1.5-2-2-2.5z" fill="#F97316" />
          <path d="M26 14c1.5 1.5-1 3 0 4.5s2.5-1 1.5-2.5c-.5-1-1-1.5-1.5-2z" fill="#F97316" />
          <path d="M15 25h16c0 3.5-2.5 6-7 6s-7-2.5-7-6h-2z" fill="#F97316" />
          <path d="M31 25c1.5 0 3 1 3 2.5s-1.5 2.5-3 2.5v-1c.8 0 1.5-.7 1.5-1.5s-.7-1.5-1.5-1.5v-1z" fill="#F97316" />
          <path d="M13 33h20v2H13v-2z" fill="#F97316" />
        </svg>
      );
    case 'javascript':
      return (
        <svg width={size} height={size} viewBox="0 0 48 48" fill="none">
          <circle cx="24" cy="24" r="22" fill="#FACC15" fillOpacity="0.15" stroke="#FACC15" strokeWidth="1.5" />
          <rect x="14" y="14" width="20" height="20" rx="4" fill="#FACC15" />
          <path d="M20 28.5c0 1.8 1.2 2.7 2.8 2.7.9 0 1.6-.2 2-.5v-1.6c-.4.2-.8.3-1.3.3-.8 0-1.4-.4-1.4-1.2v-4.7H20v4.5z" fill="#0F172A" />
          <path d="M27.2 29.3c.7.4 1.6.6 2.4.6 1.1 0 1.7-.5 1.7-1.2 0-.7-.5-1.1-1.5-1.5-1.5-.6-2.4-1.3-2.4-2.5 0-1.5 1.2-2.5 3-2.5.8 0 1.6.2 2.2.5l-.6 1.5c-.5-.3-1.1-.4-1.6-.4-.8 0-1.3.4-1.3 1 0 .6.5 1 1.5 1.4 1.6.6 2.4 1.4 2.4 2.6 0 1.6-1.2 2.6-3.2 2.6-.9 0-1.9-.3-2.6-.7l.6-1.7z" fill="#0F172A" />
        </svg>
      );
    case 'typescript':
      return (
        <svg width={size} height={size} viewBox="0 0 48 48" fill="none">
          <circle cx="24" cy="24" r="22" fill="#60A5FA" fillOpacity="0.15" stroke="#60A5FA" strokeWidth="1.5" />
          <rect x="14" y="14" width="20" height="20" rx="4" fill="#3178C6" />
          <path d="M17 19h7v2.2h-2.3v7.3H19.3v-7.3H17V19z" fill="#ffffff" />
          <path d="M25.2 26.8c.7.4 1.6.6 2.4.6 1.1 0 1.7-.5 1.7-1.2 0-.7-.5-1.1-1.5-1.5-1.5-.6-2.4-1.3-2.4-2.5 0-1.5 1.2-2.5 3-2.5.8 0 1.6.2 2.2.5l-.6 1.5c-.5-.3-1.1-.4-1.6-.4-.8 0-1.3.4-1.3 1 0 .6.5 1 1.5 1.4 1.6.6 2.4 1.4 2.4 2.6 0 1.6-1.2 2.6-3.2 2.6-.9 0-1.9-.3-2.6-.7l.6-1.7z" fill="#ffffff" />
        </svg>
      );
    case 'frontend':
      return (
        <svg width={size} height={size} viewBox="0 0 48 48" fill="none">
          <circle cx="24" cy="24" r="22" fill="#EC4899" fillOpacity="0.15" stroke="#EC4899" strokeWidth="1.5" />
          <rect x="12" y="14" width="24" height="20" rx="3" stroke="#EC4899" strokeWidth="1.8" fill="none" />
          <path d="M12 20h24" stroke="#EC4899" strokeWidth="1.5" />
          <circle cx="15.5" cy="17" r="1" fill="#EC4899" />
          <circle cx="18.5" cy="17" r="1" fill="#EC4899" />
          <path d="M20 25l-3 3 3 3M28 25l3 3-3 3" stroke="#EC4899" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      );
    case 'qa_automation':
      return (
        <svg width={size} height={size} viewBox="0 0 48 48" fill="none">
          <circle cx="24" cy="24" r="22" fill="#10B981" fillOpacity="0.15" stroke="#10B981" strokeWidth="1.5" />
          <rect x="11" y="13" width="26" height="22" rx="3.5" stroke="#10B981" strokeWidth="1.8" fill="none" />
          <path d="M11 19h26" stroke="#10B981" strokeWidth="1.4" />
          <circle cx="15" cy="16" r="1.2" fill="#10B981" />
          <circle cx="18.5" cy="16" r="1.2" fill="#10B981" />
          <circle cx="22" cy="16" r="1.2" fill="#10B981" />
          <path d="M18 27.5l3.5 3.5 8-8" stroke="#34D399" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      );
    default:
      return null;
  }
};

interface TechnologyCardsProps {
  selectedTechnology: TechnologyKey;
  onSelectTechnology: (tech: TechnologyKey) => void;
  candidateCounts?: Record<TechnologyKey, number>;
}

export const TechnologyCards: React.FC<TechnologyCardsProps> = ({
  selectedTechnology,
  onSelectTechnology,
  candidateCounts = { golang: 177, python: 0, java: 0, javascript: 0, typescript: 0, frontend: 0, qa_automation: 0 },
}) => {
  return (
    <div>
      {/* Sleek Subheader */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: '8px',
          padding: '0 2px',
        }}
      >
        <div
          style={{
            fontSize: '11px',
            fontWeight: 700,
            textTransform: 'uppercase',
            letterSpacing: '0.07em',
            color: 'var(--text-muted)',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
          }}
        >
          <Sparkles size={13} color="var(--accent-cyan)" />
          <span>Technology Workspaces</span>
        </div>
        <div style={{ fontSize: '11px', color: 'var(--text-dim)', display: 'flex', alignItems: 'center', gap: '5px' }}>
          <Database size={11} color="var(--accent-emerald)" />
          <span>Isolated SQLite database per language</span>
        </div>
      </div>

      {/* Compact, Sleek Technology Cards Strip */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))',
          gap: '10px',
          width: '100%',
        }}
      >
        {TECHNOLOGIES.map((t) => {
          const isSelected = selectedTechnology === t.key;
          const count = candidateCounts[t.key] ?? 0;
          const isGoCompleted = t.key === 'golang' && count >= 177;

          return (
            <div
              key={t.key}
              onClick={() => onSelectTechnology(t.key)}
              style={{
                cursor: 'pointer',
                background: isSelected
                  ? `linear-gradient(135deg, ${t.bgColor} 0%, rgba(13, 20, 38, 0.95) 100%)`
                  : 'rgba(11, 16, 30, 0.7)',
                border: isSelected
                  ? `1.5px solid ${t.color}`
                  : '1px solid rgba(255, 255, 255, 0.08)',
                borderRadius: 'var(--radius-sm)',
                padding: '12px 14px',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                gap: '8px',
                minHeight: '76px',
                transition: 'all 0.2s cubic-bezier(0.16, 1, 0.3, 1)',
                boxShadow: isSelected
                  ? `0 0 16px ${t.glowColor}, inset 0 1px 0 rgba(255, 255, 255, 0.15)`
                  : '0 2px 6px rgba(0, 0, 0, 0.3)',
                position: 'relative',
                overflow: 'hidden',
              }}
            >
              {/* Active Indicator Top Glow Line */}
              {isSelected && (
                <div
                  style={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    right: 0,
                    height: '2px',
                    background: t.color,
                    boxShadow: `0 0 6px ${t.color}`,
                  }}
                />
              )}

              {/* Top Row: Icon + Name (Left) & Big Number (Right) */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px', minWidth: 0 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: 0, flex: '1 1 auto' }}>
                  <div style={{ flexShrink: 0 }}>
                    <TechIcon tech={t.key} size={20} />
                  </div>
                  <span
                    style={{
                      fontWeight: 700,
                      fontSize: '13.5px',
                      color: isSelected ? '#ffffff' : 'var(--text-secondary)',
                      lineHeight: '1.2',
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                    }}
                    title={t.name}
                  >
                    {t.name}
                  </span>
                </div>

                {/* Candidate Count - High Prominence & Never Clipped */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '4px', flexShrink: 0 }}>
                  <span
                    style={{
                      fontSize: '17px',
                      fontWeight: 800,
                      fontFamily: 'var(--font-mono)',
                      color: count > 0 ? (isGoCompleted ? '#34d399' : t.color) : 'var(--text-muted)',
                      lineHeight: '1',
                      letterSpacing: '-0.02em',
                    }}
                  >
                    {count}
                  </span>
                  {isSelected && <CheckCircle2 size={13} color={t.color} style={{ flexShrink: 0 }} />}
                </div>
              </div>

              {/* Bottom Row: DB Name (Left) & Status Badge (Right) */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px', minWidth: 0 }}>
                <span
                  style={{
                    fontSize: '10px',
                    fontFamily: 'var(--font-mono)',
                    color: 'var(--text-dim)',
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    minWidth: 0,
                  }}
                  title={t.dbFileName}
                >
                  {t.dbFileName.replace('screening_', '')}
                </span>

                <span
                  style={{
                    flexShrink: 0,
                    fontSize: '9.5px',
                    fontWeight: 700,
                    textTransform: 'uppercase',
                    letterSpacing: '0.04em',
                    padding: '1px 6px',
                    borderRadius: '4px',
                    whiteSpace: 'nowrap',
                    background: isGoCompleted
                      ? 'rgba(16, 185, 129, 0.15)'
                      : isSelected
                      ? t.bgColor
                      : 'rgba(255, 255, 255, 0.04)',
                    color: isGoCompleted
                      ? '#34d399'
                      : isSelected
                      ? t.color
                      : 'var(--text-dim)',
                    border: `1px solid ${
                      isGoCompleted
                        ? 'rgba(16, 185, 129, 0.3)'
                        : isSelected
                        ? t.borderColor
                        : 'rgba(255, 255, 255, 0.06)'
                    }`,
                  }}
                >
                  {isGoCompleted ? 'Complete' : isSelected ? 'Active' : 'Select'}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
