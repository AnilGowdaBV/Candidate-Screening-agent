import React from 'react';
import {
  Users,
  CheckCircle,
  Hourglass,
  Github,
  SearchX,
  Code2,
  FileX,
  FileCheck2,
  CopyCheck,
  AlertOctagon,
  AlertTriangle,
} from 'lucide-react';
import { DashboardMetrics, TechnologyKey } from '../types';
import { TECHNOLOGIES } from './TechnologyCards';

interface MetricsCardsProps {
  metrics: DashboardMetrics | null;
  onSelectFilter?: (filterId: string) => void;
  activeFilter?: string;
  selectedTechnology?: TechnologyKey;
}

export const MetricsCards: React.FC<MetricsCardsProps> = ({
  metrics,
  onSelectFilter,
  activeFilter,
  selectedTechnology = 'golang',
}) => {
  const currentTech = TECHNOLOGIES.find(t => t.key === selectedTechnology) || TECHNOLOGIES[0];
  const detectedLabel = `${currentTech.name} Detected`;
  const notFoundLabel = `${currentTech.name} Not Found`;

  const cards = [
    {
      label: 'Discovered',
      value: metrics?.candidates_discovered ?? 0,
      icon: Users,
      color: '#6366f1',
      glow: 'rgba(99, 102, 241, 0.25)',
      filterId: '',
    },
    {
      label: 'Processed',
      value: metrics?.candidates_processed ?? 0,
      icon: CheckCircle,
      color: '#10b981',
      glow: 'rgba(16, 185, 129, 0.25)',
      filterId: '',
    },
    {
      label: 'Remaining',
      value: metrics?.candidates_remaining ?? 0,
      icon: Hourglass,
      color: '#94a3b8',
      glow: 'rgba(148, 163, 184, 0.2)',
      filterId: '',
    },
    {
      label: 'GitHub Found',
      value: metrics?.github_profiles_found ?? 0,
      icon: Github,
      color: '#06b6d4',
      glow: 'rgba(6, 182, 212, 0.25)',
      filterId: 'GITHUB_FOUND',
    },
    {
      label: 'GitHub Missing',
      value: metrics?.github_profiles_missing ?? 0,
      icon: SearchX,
      color: '#f59e0b',
      glow: 'rgba(245, 158, 11, 0.25)',
      filterId: 'GITHUB_NOT_FOUND',
    },
    {
      label: detectedLabel,
      value: metrics?.go_detected ?? 0,
      icon: Code2,
      color: '#10b981',
      glow: 'rgba(16, 185, 129, 0.35)',
      highlight: true,
      filterId: 'TECH_DETECTED',
    },
    {
      label: notFoundLabel,
      value: metrics?.go_not_detected ?? 0,
      icon: FileX,
      color: '#94a3b8',
      glow: 'rgba(148, 163, 184, 0.2)',
      filterId: 'TECH_NOT_DETECTED',
    },
    {
      label: 'Notes Added',
      value: metrics?.notes_added ?? 0,
      icon: FileCheck2,
      color: '#06b6d4',
      glow: 'rgba(6, 182, 212, 0.25)',
      filterId: 'NOTE_ADDED',
    },
    {
      label: 'Notes Existed',
      value: metrics?.notes_already_present ?? 0,
      icon: CopyCheck,
      color: '#a855f7',
      glow: 'rgba(168, 85, 247, 0.25)',
      filterId: 'NOTE_ADDED',
    },
    {
      label: 'Needs Review',
      value: metrics?.candidates_needing_review ?? 0,
      icon: AlertOctagon,
      color: '#f59e0b',
      glow: 'rgba(245, 158, 11, 0.25)',
      filterId: 'NEEDS_REVIEW',
    },
    {
      label: 'Errors',
      value: metrics?.errors ?? 0,
      icon: AlertTriangle,
      color: '#ef4444',
      glow: 'rgba(239, 68, 68, 0.25)',
      filterId: '',
    },
  ];

  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(130px, 1fr))',
        gap: '12px',
      }}
    >
      {cards.map((item) => {
        const Icon = item.icon;
        const isSelected = Boolean(item.filterId && activeFilter === item.filterId);

        return (
          <div
            key={item.label}
            onClick={() => {
              if (item.filterId !== undefined && onSelectFilter) {
                onSelectFilter(item.filterId);
              }
            }}
            style={{
              background: isSelected
                ? 'linear-gradient(180deg, rgba(99, 102, 241, 0.2) 0%, var(--bg-card) 100%)'
                : item.highlight
                ? 'linear-gradient(180deg, rgba(16, 185, 129, 0.12) 0%, var(--bg-card) 100%)'
                : 'var(--bg-card)',
              border: isSelected
                ? `1.5px solid var(--accent-primary)`
                : item.highlight
                ? '1px solid rgba(16, 185, 129, 0.4)'
                : '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-sm)',
              padding: '12px 14px',
              display: 'flex',
              flexDirection: 'column',
              gap: '6px',
              cursor: item.filterId !== undefined ? 'pointer' : 'default',
              transition: 'all 0.2s cubic-bezier(0.16, 1, 0.3, 1)',
              boxShadow: isSelected
                ? '0 0 16px rgba(99, 102, 241, 0.35)'
                : item.highlight
                ? '0 0 16px rgba(16, 185, 129, 0.2)'
                : '0 2px 8px rgba(0, 0, 0, 0.3)',
              position: 'relative',
              overflow: 'hidden',
            }}
            title={item.filterId ? `Click to filter table by ${item.label}` : undefined}
          >
            {/* Top Indicator Accent */}
            <div
              style={{
                position: 'absolute',
                top: 0,
                left: 0,
                right: 0,
                height: '2px',
                background: item.color,
                opacity: isSelected || item.highlight ? 1 : 0.6,
              }}
            />

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span
                style={{
                  fontSize: '11px',
                  color: isSelected ? '#ffffff' : 'var(--text-muted)',
                  fontWeight: 600,
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                }}
              >
                {item.label}
              </span>
              <div
                style={{
                  width: '20px',
                  height: '20px',
                  borderRadius: '5px',
                  background: `${item.color}15`,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <Icon size={12} color={item.color} />
              </div>
            </div>

            <div
              style={{
                fontSize: '22px',
                fontWeight: 800,
                color: item.highlight ? '#34d399' : '#ffffff',
                fontFamily: 'var(--font-mono)',
                lineHeight: '1.1',
              }}
            >
              {item.value}
            </div>
          </div>
        );
      })}
    </div>
  );
};
