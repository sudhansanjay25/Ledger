'use client';

import React from 'react';
import { ShieldCheck, AlertOctagon, Lock, ChevronRight } from 'lucide-react';

export default function SecurityShieldTab({ securityScan }) {
  const isSafe = securityScan?.is_safe;
  const threatDetected = securityScan?.threat_detected;
  const details = securityScan?.details;
  const logs = securityScan?.logs || [];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {/* Security Verdict Banner */}
      <div
        id="security-verdict-banner"
        style={{
          padding: '18px',
          borderRadius: 'var(--radius-md)',
          background:
            isSafe === false
              ? 'rgba(244, 63, 94, 0.12)'
              : isSafe === true
              ? 'rgba(16, 185, 129, 0.12)'
              : 'rgba(255, 255, 255, 0.03)',
          border:
            isSafe === false
              ? '1px solid rgba(244, 63, 94, 0.4)'
              : isSafe === true
              ? '1px solid rgba(16, 185, 129, 0.4)'
              : '1px solid var(--border-subtle)',
          display: 'flex',
          alignItems: 'center',
          gap: '14px'
        }}
      >
        {isSafe === false ? (
          <AlertOctagon size={32} color="#f43f5e" />
        ) : isSafe === true ? (
          <ShieldCheck size={32} color="#10b981" />
        ) : (
          <Lock size={32} color="var(--text-dim)" />
        )}
        <div>
          <h3 style={{ fontSize: '0.95rem', fontWeight: 700 }}>
            {isSafe === false
              ? `Security Threat Blocked: ${threatDetected}`
              : isSafe === true
              ? 'All Security Guardrails Passed'
              : 'Security Scan Pending'}
          </h3>
          <p style={{ fontSize: '0.8125rem', color: 'var(--text-muted)', marginTop: '2px' }}>
            {details ||
              'Pre-ingestion scanner inspects domain whitelists, Unicode homoglyphs, BiDi RTL overrides, and prompt injection attacks.'}
          </p>
        </div>
      </div>

      {/* 4 Guardrail Checklist Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '12px' }}>
        {[
          {
            name: 'Domain Whitelist Verification',
            desc: 'Validates source URL matches trusted regulator portals (e.g. rbi.org.in, gov.in).',
            passed: isSafe !== undefined,
            failed: threatDetected === 'Untrusted Source Domain'
          },
          {
            name: 'Unicode Homoglyph Detection',
            desc: 'Scans for spoofed Cyrillic / visually identical characters disguised as English letters.',
            passed: isSafe !== undefined,
            failed: threatDetected === 'Unicode Homoglyph Attack'
          },
          {
            name: 'Directional RTL Character Scan',
            desc: 'Detects hidden right-to-left directional override markers (\\u202E) used to distort instructions.',
            passed: isSafe !== undefined,
            failed: threatDetected === 'BiDi/RTL Text Override Attack'
          },
          {
            name: 'Prompt Injection Defense',
            desc: 'Flags regex and semantic instruction-override triggers (e.g., "[SYSTEM OVERRIDE DETECTED]").',
            passed: isSafe === true,
            failed: threatDetected === 'Prompt Injection Attempt'
          }
        ].map((check, i) => (
          <div
            key={i}
            style={{
              padding: '14px',
              borderRadius: 'var(--radius-md)',
              background: 'var(--bg-surface-elevated)',
              border: '1px solid var(--border-subtle)',
              display: 'flex',
              flexDirection: 'column',
              gap: '6px'
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '0.8125rem', fontWeight: 600 }}>{check.name}</span>
              {check.failed ? (
                <span className="badge badge-rose">Threat Detected</span>
              ) : check.passed ? (
                <span className="badge badge-emerald">Verified</span>
              ) : (
                <span className="badge badge-indigo">Ready</span>
              )}
            </div>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', lineHeight: 1.4 }}>{check.desc}</p>
          </div>
        ))}
      </div>

      {/* Security Scan Logs */}
      {logs.length > 0 && (
        <div
          style={{
            background: 'var(--bg-surface)',
            borderRadius: 'var(--radius-md)',
            padding: '14px',
            border: '1px solid var(--border-subtle)'
          }}
        >
          <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-dim)', display: 'block', marginBottom: '8px' }}>
            DETAILED SCAN AUDIT LOGS
          </span>
          <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {logs.map((log, idx) => (
              <li
                key={idx}
                style={{
                  fontSize: '0.75rem',
                  fontFamily: 'var(--font-mono)',
                  color: log.includes('FAILED') ? '#f43f5e' : '#10b981',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px'
                }}
              >
                <ChevronRight size={12} /> {log}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
