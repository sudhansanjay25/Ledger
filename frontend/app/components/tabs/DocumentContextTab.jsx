'use client';

import React from 'react';

export default function DocumentContextTab({ document, selectedDocId }) {
  const quality = document?.quality_score ?? 1.0;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: '12px'
        }}
      >
        <div style={{ padding: '14px', borderRadius: 'var(--radius-md)', background: 'var(--bg-surface-elevated)', border: '1px solid var(--border-subtle)' }}>
          <span style={{ fontSize: '0.6875rem', color: 'var(--text-dim)', fontWeight: 600 }}>DOCUMENT ID</span>
          <div style={{ fontSize: '0.875rem', fontWeight: 600, fontFamily: 'var(--font-mono)', marginTop: '4px' }}>
            {document?.id || selectedDocId}
          </div>
        </div>

        <div style={{ padding: '14px', borderRadius: 'var(--radius-md)', background: 'var(--bg-surface-elevated)', border: '1px solid var(--border-subtle)' }}>
          <span style={{ fontSize: '0.6875rem', color: 'var(--text-dim)', fontWeight: 600 }}>FORMAT & ENCODING</span>
          <div style={{ fontSize: '0.875rem', fontWeight: 600, marginTop: '4px' }}>
            {document?.format ? document.format.replace('_', ' ').toUpperCase() : 'DIGITAL PDF'}
          </div>
        </div>

        <div style={{ padding: '14px', borderRadius: 'var(--radius-md)', background: 'var(--bg-surface-elevated)', border: '1px solid var(--border-subtle)' }}>
          <span style={{ fontSize: '0.6875rem', color: 'var(--text-dim)', fontWeight: 600 }}>OCR READING QUALITY</span>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '4px' }}>
            <div
              style={{
                flex: 1,
                height: '8px',
                background: 'rgba(255, 255, 255, 0.1)',
                borderRadius: '4px',
                overflow: 'hidden'
              }}
            >
              <div
                style={{
                  width: `${quality * 100}%`,
                  height: '100%',
                  backgroundColor: quality < 0.5 ? '#f43f5e' : '#10b981'
                }}
              />
            </div>
            <span style={{ fontSize: '0.8125rem', fontFamily: 'var(--font-mono)', fontWeight: 700 }}>
              {(quality * 100).toFixed(0)}%
            </span>
          </div>
        </div>
      </div>

      {/* Cleaned Text Preview */}
      <div style={{ background: 'var(--bg-surface)', borderRadius: 'var(--radius-md)', padding: '16px', border: '1px solid var(--border-subtle)' }}>
        <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-dim)', display: 'block', marginBottom: '8px' }}>
          INGESTED & CLEANED TEXT PREVIEW
        </span>
        <div
          style={{
            maxHeight: '260px',
            overflowY: 'auto',
            fontSize: '0.8125rem',
            fontFamily: 'var(--font-mono)',
            lineHeight: 1.6,
            color: 'var(--text-muted)',
            whiteSpace: 'pre-wrap',
            background: 'rgba(0, 0, 0, 0.25)',
            padding: '12px',
            borderRadius: 'var(--radius-sm)'
          }}
        >
          {document?.cleaned_text || document?.raw_text || 'No document text ingested yet.'}
        </div>
      </div>
    </div>
  );
}
