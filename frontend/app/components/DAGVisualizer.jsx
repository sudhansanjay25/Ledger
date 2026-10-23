'use client';

import React from 'react';
import { Activity, FileText, Cpu, Database, ShieldCheck, ShieldAlert, Sparkles } from 'lucide-react';

export default function DAGVisualizer({
  activeNode,
  currentNodeActivity,
  agentState,
  finalOutcome
}) {
  return (
    <div className="glass-panel" style={{ padding: '20px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Activity size={18} color="var(--accent-cyan)" />
          <h2 style={{ fontSize: '0.95rem', fontWeight: 700 }}>LangGraph Execution Pipeline</h2>
        </div>
        {currentNodeActivity && (
          <span
            style={{
              fontSize: '0.75rem',
              color: 'var(--accent-indigo-light)',
              background: 'rgba(99, 102, 241, 0.1)',
              padding: '3px 10px',
              borderRadius: 'var(--radius-full)',
              border: '1px solid rgba(99, 102, 241, 0.25)'
            }}
          >
            Current: {currentNodeActivity}
          </span>
        )}
      </div>

      {/* Interactive Graph Node Strip */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gap: '14px',
          position: 'relative'
        }}
      >
        {/* Node 1: Ingestion */}
        <div
          id="graph-node-ingest"
          style={{
            padding: '14px',
            borderRadius: 'var(--radius-md)',
            background: agentState.document?.id ? 'rgba(16, 185, 129, 0.1)' : 'var(--bg-surface)',
            border: agentState.document?.id ? '1px solid rgba(16, 185, 129, 0.4)' : '1px solid var(--border-subtle)',
            textAlign: 'center',
            transition: 'all 0.3s ease'
          }}
        >
          <div style={{ display: 'inline-flex', padding: '8px', borderRadius: '50%', background: 'rgba(255, 255, 255, 0.05)', marginBottom: '8px' }}>
            <FileText size={18} color={agentState.document?.id ? '#10b981' : 'var(--text-dim)'} />
          </div>
          <div style={{ fontSize: '0.8125rem', fontWeight: 700 }}>1. Ingest & Cache</div>
          <div style={{ fontSize: '0.6875rem', color: 'var(--text-dim)', marginTop: '4px' }}>
            {agentState.document?.id ? 'Document Loaded' : 'Waiting...'}
          </div>
        </div>

        {/* Node 2: Planner Agent */}
        <div
          id="graph-node-planner"
          className={activeNode === 'planner' ? 'node-active' : ''}
          style={{
            padding: '14px',
            borderRadius: 'var(--radius-md)',
            background: activeNode === 'planner' ? 'rgba(99, 102, 241, 0.15)' : 'var(--bg-surface)',
            border: activeNode === 'planner' ? '1px solid rgba(99, 102, 241, 0.6)' : '1px solid var(--border-subtle)',
            textAlign: 'center',
            transition: 'all 0.3s ease'
          }}
        >
          <div style={{ display: 'inline-flex', padding: '8px', borderRadius: '50%', background: 'rgba(255, 255, 255, 0.05)', marginBottom: '8px' }}>
            <Cpu size={18} color={activeNode === 'planner' ? '#818cf8' : 'var(--text-dim)'} />
          </div>
          <div style={{ fontSize: '0.8125rem', fontWeight: 700 }}>2. Planner Agent</div>
          <div style={{ fontSize: '0.6875rem', color: 'var(--text-dim)', marginTop: '4px' }}>
            {activeNode === 'planner' ? 'Reasoning / Deciding...' : 'Decision Node'}
          </div>
        </div>

        {/* Node 3: ToolNode */}
        <div
          id="graph-node-tools"
          className={activeNode === 'tools' ? 'node-active' : ''}
          style={{
            padding: '14px',
            borderRadius: 'var(--radius-md)',
            background: activeNode === 'tools' ? 'rgba(6, 182, 212, 0.15)' : 'var(--bg-surface)',
            border: activeNode === 'tools' ? '1px solid rgba(6, 182, 212, 0.6)' : '1px solid var(--border-subtle)',
            textAlign: 'center',
            transition: 'all 0.3s ease'
          }}
        >
          <div style={{ display: 'inline-flex', padding: '8px', borderRadius: '50%', background: 'rgba(255, 255, 255, 0.05)', marginBottom: '8px' }}>
            <Database size={18} color={activeNode === 'tools' ? '#06b6d4' : 'var(--text-dim)'} />
          </div>
          <div style={{ fontSize: '0.8125rem', fontWeight: 700 }}>3. Tool Executions</div>
          <div style={{ fontSize: '0.6875rem', color: 'var(--text-dim)', marginTop: '4px' }}>
            {activeNode === 'tools' ? 'Invoking Tool...' : 'Security / OCR / MAPs'}
          </div>
        </div>

        {/* Node 4: Synthesis & Output */}
        <div
          id="graph-node-verdict"
          style={{
            padding: '14px',
            borderRadius: 'var(--radius-md)',
            background:
              finalOutcome === 'THREAT_BLOCKED'
                ? 'rgba(244, 63, 94, 0.15)'
                : finalOutcome === 'SUCCESS'
                ? 'rgba(16, 185, 129, 0.15)'
                : finalOutcome === 'ERROR'
                ? 'rgba(244, 63, 94, 0.15)'
                : 'var(--bg-surface)',
            border:
              finalOutcome === 'THREAT_BLOCKED' || finalOutcome === 'ERROR'
                ? '1px solid rgba(244, 63, 94, 0.6)'
                : finalOutcome === 'SUCCESS'
                ? '1px solid rgba(16, 185, 129, 0.6)'
                : '1px solid var(--border-subtle)',
            textAlign: 'center',
            transition: 'all 0.3s ease'
          }}
        >
          <div style={{ display: 'inline-flex', padding: '8px', borderRadius: '50%', background: 'rgba(255, 255, 255, 0.05)', marginBottom: '8px' }}>
            {finalOutcome === 'THREAT_BLOCKED' || finalOutcome === 'ERROR' ? (
              <ShieldAlert size={18} color="#f43f5e" />
            ) : finalOutcome === 'SUCCESS' ? (
              <ShieldCheck size={18} color="#10b981" />
            ) : (
              <Sparkles size={18} color="var(--text-dim)" />
            )}
          </div>
          <div style={{ fontSize: '0.8125rem', fontWeight: 700 }}>4. State Verdict</div>
          <div style={{ fontSize: '0.6875rem', color: 'var(--text-dim)', marginTop: '4px' }}>
            {finalOutcome === 'THREAT_BLOCKED'
              ? 'Security Flagged'
              : finalOutcome === 'SUCCESS'
              ? `${agentState.extracted_maps?.length || 0} MAPs Generated`
              : finalOutcome === 'ERROR'
              ? 'Error Halting'
              : 'Awaiting Run'}
          </div>
        </div>
      </div>
    </div>
  );
}
