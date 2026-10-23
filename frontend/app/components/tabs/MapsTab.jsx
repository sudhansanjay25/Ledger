'use client';

import React from 'react';
import { ListFilter } from 'lucide-react';

export default function MapsTab({ extractedMaps, finalOutcome }) {
  if (!extractedMaps || extractedMaps.length === 0) {
    return (
      <div style={{ padding: '60px 20px', textAlign: 'center', color: 'var(--text-muted)' }}>
        <ListFilter size={36} style={{ opacity: 0.3, margin: '0 auto 12px' }} />
        <h3 style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--text-main)' }}>
          No Measurable Action Points Generated Yet
        </h3>
        <p style={{ fontSize: '0.8125rem', marginTop: '4px' }}>
          {finalOutcome === 'THREAT_BLOCKED'
            ? 'Processing was halted due to security threat detection. No action points were created.'
            : 'Trigger the agent workflow above to ingest the circular and extract action points.'}
        </p>
      </div>
    );
  }

  const criticalCount = extractedMaps.filter((m) => m.priority === 'Critical').length;
  const requiredCount = extractedMaps.filter((m) => m.obligation_type === 'REQUIRED').length;

  return (
    <div>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '16px',
          background: 'rgba(99, 102, 241, 0.06)',
          padding: '12px 18px',
          borderRadius: 'var(--radius-md)',
          border: '1px solid rgba(99, 102, 241, 0.2)'
        }}
      >
        <div>
          <span style={{ fontSize: '0.875rem', fontWeight: 700, color: 'var(--text-main)' }}>
            {extractedMaps.length} Action Points Extracted
          </span>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '2px' }}>
            Each action point contains structured departmental routing, deadline parsing, and confidence scoring.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <span className="badge badge-rose">{criticalCount} Critical</span>
          <span className="badge badge-indigo">{requiredCount} Required</span>
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {extractedMaps.map((mapItem, idx) => (
          <div
            key={mapItem.action_id || idx}
            id={`map-item-card-${idx}`}
            style={{
              padding: '16px',
              borderRadius: 'var(--radius-md)',
              background: 'var(--bg-surface-elevated)',
              border: '1px solid var(--border-medium)',
              display: 'flex',
              flexDirection: 'column',
              gap: '10px'
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span
                  style={{
                    fontFamily: 'var(--font-mono)',
                    fontSize: '0.75rem',
                    fontWeight: 700,
                    color: 'var(--accent-indigo-light)',
                    background: 'rgba(99, 102, 241, 0.1)',
                    padding: '2px 8px',
                    borderRadius: 'var(--radius-sm)'
                  }}
                >
                  {mapItem.action_id}
                </span>
                <span className={`badge ${mapItem.priority === 'Critical' ? 'badge-rose' : 'badge-amber'}`}>
                  {mapItem.priority} Priority
                </span>
                <span className="badge badge-indigo">{mapItem.obligation_type}</span>
              </div>

              {/* AI Confidence Meter */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ fontSize: '0.6875rem', color: 'var(--text-dim)' }}>Confidence:</span>
                <div
                  style={{
                    width: '50px',
                    height: '6px',
                    background: 'rgba(255, 255, 255, 0.1)',
                    borderRadius: '3px',
                    overflow: 'hidden'
                  }}
                >
                  <div
                    style={{
                      width: `${(mapItem.confidence || 0.8) * 100}%`,
                      height: '100%',
                      backgroundColor: (mapItem.confidence || 0.8) > 0.85 ? '#10b981' : '#f59e0b'
                    }}
                  />
                </div>
                <span style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
                  {((mapItem.confidence || 0.8) * 100).toFixed(0)}%
                </span>
              </div>
            </div>

            {/* Action Statement */}
            <p style={{ fontSize: '0.875rem', fontWeight: 500, lineHeight: 1.5, color: 'var(--text-main)' }}>
              {mapItem.action}
            </p>

            {/* Meta Details Row */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                fontSize: '0.75rem',
                color: 'var(--text-muted)',
                paddingTop: '6px',
                borderTop: '1px solid rgba(255, 255, 255, 0.05)'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ color: 'var(--text-dim)' }}>Departments:</span>
                {Array.isArray(mapItem.department) ? (
                  mapItem.department.map((dept) => (
                    <span
                      key={dept}
                      style={{
                        background: 'rgba(255, 255, 255, 0.05)',
                        padding: '2px 6px',
                        borderRadius: '4px'
                      }}
                    >
                      {dept}
                    </span>
                  ))
                ) : (
                  <span>{mapItem.department}</span>
                )}
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ color: 'var(--text-dim)' }}>Deadline:</span>
                <span
                  style={{
                    fontWeight: 600,
                    color: mapItem.deadline !== 'None' ? '#38bdf8' : 'var(--text-dim)'
                  }}
                >
                  {mapItem.deadline} ({mapItem.deadline_type})
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
