'use client';

import React from 'react';
import { Cpu } from 'lucide-react';

export default function ReasoningTab({ messages }) {
  const finalAiMessage = messages
    ?.filter((m) => m.role === 'assistant' && m.content)
    ?.slice(-1)[0]?.content;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {finalAiMessage ? (
        <div
          id="agent-final-response-box"
          style={{
            background: 'var(--bg-surface-elevated)',
            borderRadius: 'var(--radius-md)',
            padding: '20px',
            border: '1px solid var(--border-medium)',
            lineHeight: 1.65,
            fontSize: '0.875rem',
            whiteSpace: 'pre-wrap'
          }}
        >
          {finalAiMessage}
        </div>
      ) : (
        <div style={{ padding: '60px 20px', textAlign: 'center', color: 'var(--text-muted)' }}>
          <Cpu size={36} style={{ opacity: 0.3, margin: '0 auto 12px' }} />
          <h3 style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--text-main)' }}>
            No Reasoning Summary Available
          </h3>
          <p style={{ fontSize: '0.8125rem', marginTop: '4px' }}>
            Once the agent workflow executes, the planner agent synthesizes circular observations,
            deadlines, and findings here.
          </p>
        </div>
      )}
    </div>
  );
}
