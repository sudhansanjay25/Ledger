'use client';

import React from 'react';
import {
  Terminal,
  Cpu,
  Zap,
  Database,
  ShieldAlert,
  CheckCircle2,
  AlertTriangle
} from 'lucide-react';

export default function TerminalFeed({ eventsFeed, terminalEndRef }) {
  return (
    <div className="glass-panel" style={{ padding: '18px', display: 'flex', flexDirection: 'column', flex: 1, maxHeight: '420px' }}>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '12px',
          paddingBottom: '8px',
          borderBottom: '1px solid var(--border-subtle)'
        }}
      >
        <span style={{ fontSize: '0.8125rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Terminal size={15} color="var(--accent-cyan)" />
          Telemetry & Event Stream
        </span>
        <span style={{ fontSize: '0.6875rem', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
          {eventsFeed.length} events
        </span>
      </div>

      <div
        id="sse-telemetry-feed"
        style={{
          flex: 1,
          overflowY: 'auto',
          display: 'flex',
          flexDirection: 'column',
          gap: '8px',
          paddingRight: '4px'
        }}
      >
        {eventsFeed.length === 0 ? (
          <div
            style={{
              padding: '30px 10px',
              textAlign: 'center',
              color: 'var(--text-dim)',
              fontSize: '0.8125rem'
            }}
          >
            <Cpu size={24} style={{ opacity: 0.3, margin: '0 auto 8px' }} />
            Press &ldquo;Trigger Agent Workflow&rdquo; to initiate LangGraph state execution
          </div>
        ) : (
          eventsFeed.map((ev) => {
            let badgeClass = 'badge-indigo';
            let icon = <Cpu size={12} />;

            if (ev.type === 'agent_start') {
              badgeClass = 'badge-cyan';
              icon = <Zap size={12} />;
            } else if (ev.node === 'tools') {
              badgeClass = 'badge-emerald';
              icon = <Database size={12} />;
            } else if (ev.outcome === 'THREAT_BLOCKED') {
              badgeClass = 'badge-rose';
              icon = <ShieldAlert size={12} />;
            } else if (ev.type === 'agent_complete') {
              badgeClass = 'badge-emerald';
              icon = <CheckCircle2 size={12} />;
            } else if (ev.type === 'agent_error') {
              badgeClass = 'badge-rose';
              icon = <AlertTriangle size={12} />;
            }

            return (
              <div
                key={ev.id}
                style={{
                  padding: '8px 10px',
                  background: 'rgba(0, 0, 0, 0.3)',
                  borderRadius: 'var(--radius-sm)',
                  borderLeft: `3px solid ${
                    ev.outcome === 'THREAT_BLOCKED' || ev.type === 'agent_error'
                      ? '#f43f5e'
                      : ev.node === 'tools'
                      ? '#10b981'
                      : '#6366f1'
                  }`,
                  fontSize: '0.75rem',
                  fontFamily: 'var(--font-mono)'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '3px' }}>
                  <span className={`badge ${badgeClass}`} style={{ fontSize: '0.625rem', padding: '2px 6px' }}>
                    {icon}
                    {ev.node ? `Node: ${ev.node}` : ev.type}
                  </span>
                  <span style={{ fontSize: '0.6875rem', color: 'var(--text-dim)' }}>
                    {ev.timestamp ? new Date(ev.timestamp).toLocaleTimeString() : ''}
                  </span>
                </div>
                <div style={{ color: 'var(--text-main)', marginTop: '4px', lineHeight: 1.4 }}>
                  {ev.activity || ev.message || ev.error || (ev.outcome && `Finished with: ${ev.outcome}`)}
                </div>
              </div>
            );
          })
        )}
        <div ref={terminalEndRef} />
      </div>
    </div>
  );
}
