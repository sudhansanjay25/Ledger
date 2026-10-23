'use client';

import React from 'react';
import { Cpu, Activity, Clock, Hash } from 'lucide-react';

export default function Header({
  backendHealth,
  isRunning,
  finalOutcome,
  executionTime,
  stepCount
}) {
  return (
    <header
      style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '28px',
        paddingBottom: '20px',
        borderBottom: '1px solid var(--border-subtle)'
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
        <div
          style={{
            width: '44px',
            height: '44px',
            borderRadius: '12px',
            background: 'linear-gradient(135deg, #6366f1 0%, #06b6d4 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 0 20px rgba(99, 102, 241, 0.4)'
          }}
        >
          <Cpu size={24} color="#ffffff" />
        </div>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <h1 style={{ fontSize: '1.4rem', fontWeight: 800, letterSpacing: '-0.02em' }}>
              Ledger <span style={{ color: 'var(--accent-indigo-light)', fontWeight: 400 }}>| Agent Hub</span>
            </h1>
            <span className="badge badge-indigo">Autonomous LangGraph</span>
          </div>
          <p style={{ fontSize: '0.8125rem', color: 'var(--text-muted)', marginTop: '2px' }}>
            Real-time multi-agent compliance pipeline with SSE streaming telemetry
          </p>
        </div>
      </div>

      {/* Status Indicators & Session Info */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        {/* Backend Status */}
        <div
          id="backend-status-indicator"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '6px 14px',
            borderRadius: 'var(--radius-full)',
            background: 'rgba(255, 255, 255, 0.04)',
            border: '1px solid var(--border-subtle)',
            fontSize: '0.75rem',
            fontWeight: 500
          }}
        >
          <span
            style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              backgroundColor: backendHealth === 'healthy' ? '#10b981' : '#f43f5e',
              boxShadow: backendHealth === 'healthy' ? '0 0 10px #10b981' : '0 0 10px #f43f5e'
            }}
            className={backendHealth === 'healthy' ? 'dot-pulsing' : ''}
          />
          <span>Flask Backend: {backendHealth === 'healthy' ? 'Connected (Port 5000)' : 'Offline'}</span>
        </div>

        {/* SSE Stream State */}
        <div
          id="stream-state-badge"
          className={`badge ${
            isRunning
              ? 'badge-cyan dot-pulsing'
              : finalOutcome === 'THREAT_BLOCKED'
              ? 'badge-rose'
              : finalOutcome === 'SUCCESS'
              ? 'badge-emerald'
              : 'badge-indigo'
          }`}
          style={{ padding: '6px 14px' }}
        >
          <Activity size={14} />
          <span>
            {isRunning
              ? 'SSE Streaming Live'
              : finalOutcome === 'THREAT_BLOCKED'
              ? 'Security Blocked'
              : finalOutcome === 'SUCCESS'
              ? 'Execution Complete'
              : finalOutcome === 'ERROR'
              ? 'Execution Error'
              : 'Agent Idle'}
          </span>
        </div>

        {/* Timer & Step Counter */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
            padding: '6px 14px',
            borderRadius: 'var(--radius-full)',
            background: 'rgba(255, 255, 255, 0.04)',
            border: '1px solid var(--border-subtle)',
            fontSize: '0.75rem',
            fontFamily: 'var(--font-mono)'
          }}
        >
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px', color: 'var(--text-muted)' }}>
            <Clock size={13} /> {executionTime}s
          </span>
          <span style={{ color: 'var(--border-medium)' }}>|</span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px', color: 'var(--text-muted)' }}>
            <Hash size={13} /> {stepCount} Steps
          </span>
        </div>
      </div>
    </header>
  );
}
