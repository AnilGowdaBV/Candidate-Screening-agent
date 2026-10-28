import React, { useRef, useEffect } from 'react';
import { Terminal, Clock, ShieldCheck } from 'lucide-react';
import { ActivityEvent } from '../types';

interface ActivityTimelineProps {
  events: ActivityEvent[];
}

export const ActivityTimeline: React.FC<ActivityTimelineProps> = ({ events }) => {
  const containerRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new event
  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [events]);

  const getEventBadge = (type: string) => {
    if (type.includes('DETECTED') || type.includes('CONFIRMED') || type.includes('STARTED') || type.includes('COMPLETED')) {
      return { bg: 'rgba(16, 185, 129, 0.15)', text: '#34d399', border: 'rgba(16, 185, 129, 0.35)' };
    }
    if (type.includes('ERROR') || type.includes('FAILED') || type.includes('STOPPED')) {
      return { bg: 'rgba(239, 68, 68, 0.15)', text: '#f87171', border: 'rgba(239, 68, 68, 0.35)' };
    }
    if (type.includes('PAUSE') || type.includes('REVIEW') || type.includes('RATE_LIMIT') || type.includes('NOT_FOUND')) {
      return { bg: 'rgba(245, 158, 11, 0.15)', text: '#fbbf24', border: 'rgba(245, 158, 11, 0.35)' };
    }
    return { bg: 'rgba(99, 102, 241, 0.15)', text: '#a5b4fc', border: 'rgba(99, 102, 241, 0.35)' };
  };

  return (
    <div
      className="agent-card"
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '380px',
        padding: '0',
        overflow: 'hidden',
        background: 'rgba(7, 11, 22, 0.85)',
      }}
    >
      {/* Terminal Title Bar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '12px 18px',
          background: 'rgba(5, 8, 17, 0.95)',
          borderBottom: '1px solid var(--border-medium)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          {/* Traffic lights */}
          <div style={{ display: 'flex', gap: '6px' }}>
            <div style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#ef4444', opacity: 0.85 }} />
            <div style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#f59e0b', opacity: 0.85 }} />
            <div style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#10b981', opacity: 0.85 }} />
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginLeft: '6px' }}>
            <Terminal size={14} color="var(--accent-primary)" />
            <span style={{ fontSize: '12px', fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>
              LIVE AGENT AUDIT LOG
            </span>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span className="status-pill pill-running" style={{ fontSize: '10px', padding: '2px 8px' }}>
            <span className="status-dot dot-indigo dot-pulse" />
            STREAMING
          </span>
          <span style={{ fontSize: '11px', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
            {events.length} events
          </span>
        </div>
      </div>

      {/* Terminal Log Output */}
      <div
        ref={containerRef}
        style={{
          flex: 1,
          overflowY: 'auto',
          display: 'flex',
          flexDirection: 'column',
          gap: '6px',
          padding: '12px 16px',
          fontFamily: 'var(--font-mono)',
        }}
      >
        {events.length === 0 ? (
          <div
            style={{
              height: '100%',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--text-dim)',
              fontSize: '12px',
              gap: '8px',
            }}
          >
            <ShieldCheck size={24} color="var(--accent-primary)" />
            <span>Ready. Press "Start Screening" to execute the pipeline and stream live telemetry.</span>
          </div>
        ) : (
          events.map((e) => {
            const badge = getEventBadge(e.event_type);
            const timeStr = new Date(e.created_at).toLocaleTimeString();

            return (
              <div
                key={e.id}
                style={{
                  background: 'rgba(15, 23, 42, 0.45)',
                  border: '1px solid rgba(255, 255, 255, 0.04)',
                  borderRadius: '6px',
                  padding: '7px 12px',
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '10px',
                  fontSize: '12px',
                  lineHeight: '1.4',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '4px', color: 'var(--text-dim)', flexShrink: 0, marginTop: '2px', fontSize: '11px' }}>
                  <Clock size={11} />
                  <span>{timeStr}</span>
                </div>

                <span
                  style={{
                    fontSize: '10px',
                    fontWeight: 700,
                    padding: '1px 6px',
                    borderRadius: '4px',
                    background: badge.bg,
                    color: badge.text,
                    border: `1px solid ${badge.border}`,
                    flexShrink: 0,
                  }}
                >
                  {e.event_type}
                </span>

                <span style={{ color: '#e2e8f0', flex: 1, wordBreak: 'break-word', fontSize: '12px' }}>
                  {e.message}
                </span>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
