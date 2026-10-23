'use client';

import React from 'react';
import { AlertTriangle, RefreshCw, X } from 'lucide-react';

export default function ErrorBanner({ error, onDismiss, onRetry }) {
  if (!error) return null;

  return (
    <div
      style={{
        padding: '14px 18px',
        marginBottom: '20px',
        borderRadius: 'var(--radius-md)',
        background: 'rgba(244, 63, 94, 0.12)',
        border: '1px solid rgba(244, 63, 94, 0.4)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        boxShadow: 'var(--shadow-glow-rose)'
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <AlertTriangle size={20} color="#f43f5e" />
        <div>
          <div style={{ fontSize: '0.875rem', fontWeight: 700, color: '#f43f5e' }}>
            System Execution Notice
          </div>
          <p style={{ fontSize: '0.8125rem', color: 'var(--text-main)', marginTop: '2px' }}>
            {error}
          </p>
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        {onRetry && (
          <button
            onClick={onRetry}
            className="btn btn-secondary"
            style={{ fontSize: '0.75rem', padding: '6px 12px', display: 'flex', alignItems: 'center', gap: '6px' }}
          >
            <RefreshCw size={13} /> Retry
          </button>
        )}
        {onDismiss && (
          <button
            onClick={onDismiss}
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--text-muted)',
              cursor: 'pointer',
              padding: '4px'
            }}
          >
            <X size={16} />
          </button>
        )}
      </div>
    </div>
  );
}
