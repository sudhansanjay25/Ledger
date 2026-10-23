'use client';

import React, { useState, useRef } from 'react';
import {
  Layers,
  Sliders,
  Upload,
  CheckCircle2,
  Zap,
  Play,
  RotateCcw,
  RefreshCw,
  FileUp,
  Radio,
  Globe
} from 'lucide-react';

export default function Launchpad({
  documents,
  selectedDocId,
  setSelectedDocId,
  isRunning,
  backendHealth,
  onRun,
  onReset,
  apiBaseUrl,
  onDocumentUploaded,
  onRefreshDocuments
}) {
  // 'presets' | 'custom' | 'upload' | 'monitor'
  const [mode, setMode] = useState('presets');
  const [customTitle, setCustomTitle] = useState('');
  const [customText, setCustomText] = useState('');

  // Upload state
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState(null);
  const [uploadSuccess, setUploadSuccess] = useState(null);
  const fileInputRef = useRef(null);

  // Crawler state
  const [isCrawling, setIsCrawling] = useState(false);
  const [crawlSummary, setCrawlSummary] = useState(null);

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    setUploadError(null);
    setUploadSuccess(null);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('title', file.name.replace(/\.[^/.]+$/, ''));

    try {
      const res = await fetch(`${apiBaseUrl}/api/documents/upload`, {
        method: 'POST',
        body: formData
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error || 'Failed to upload document');
      }

      const dupMsg = data.is_duplicate ? ' (Identical SHA-256 already indexed)' : '';
      setUploadSuccess(`Uploaded "${data.title}" successfully${dupMsg} (${data.page_count} page(s), ${data.total_words} words).`);
      if (onDocumentUploaded) {
        onDocumentUploaded(data);
      }
      setSelectedDocId(data.document_id);
    } catch (err) {
      setUploadError(err.message);
    } finally {
      setIsUploading(false);
    }
  };

  const handleTriggerCrawl = async () => {
    setIsCrawling(true);
    setCrawlSummary(null);
    try {
      const res = await fetch(`${apiBaseUrl}/api/crawler/trigger`, {
        method: 'POST'
      });
      const data = await res.json();
      if (res.ok && data.summary) {
        setCrawlSummary(data.summary);
        if (onRefreshDocuments) {
          onRefreshDocuments();
        }
      }
    } catch (err) {
      console.error('Crawler trigger error:', err);
    } finally {
      setIsCrawling(false);
    }
  };

  const handleTriggerRun = () => {
    if (mode === 'custom') {
      onRun({
        isCustom: true,
        customTitle: customTitle || 'Custom Regulatory Directive',
        customText: customText || 'No text provided.'
      });
    } else {
      onRun({ isCustom: false });
    }
  };

  return (
    <div className="glass-panel" style={{ padding: '20px' }}>
      {/* Launchpad Navigation Bar */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '16px'
        }}
      >
        <h2 style={{ fontSize: '0.95rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Layers size={17} color="var(--accent-indigo-light)" />
          Target Regulatory Circular
        </h2>

        <div style={{ display: 'flex', gap: '4px' }}>
          <button
            type="button"
            onClick={() => setMode('presets')}
            style={{
              background: mode === 'presets' ? 'rgba(99, 102, 241, 0.2)' : 'none',
              border: mode === 'presets' ? '1px solid rgba(99, 102, 241, 0.4)' : '1px solid transparent',
              color: mode === 'presets' ? 'var(--text-main)' : 'var(--text-dim)',
              fontSize: '0.6875rem',
              fontWeight: 600,
              padding: '4px 8px',
              borderRadius: 'var(--radius-sm)',
              cursor: 'pointer'
            }}
          >
            Catalog
          </button>
          <button
            type="button"
            onClick={() => setMode('monitor')}
            style={{
              background: mode === 'monitor' ? 'rgba(16, 185, 129, 0.2)' : 'none',
              border: mode === 'monitor' ? '1px solid rgba(16, 185, 129, 0.4)' : '1px solid transparent',
              color: mode === 'monitor' ? '#10b981' : 'var(--text-dim)',
              fontSize: '0.6875rem',
              fontWeight: 600,
              padding: '4px 8px',
              borderRadius: 'var(--radius-sm)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '3px'
            }}
          >
            <Radio size={11} /> Monitor
          </button>
          <button
            type="button"
            onClick={() => setMode('upload')}
            style={{
              background: mode === 'upload' ? 'rgba(6, 182, 212, 0.2)' : 'none',
              border: mode === 'upload' ? '1px solid rgba(6, 182, 212, 0.4)' : '1px solid transparent',
              color: mode === 'upload' ? 'var(--accent-cyan)' : 'var(--text-dim)',
              fontSize: '0.6875rem',
              fontWeight: 600,
              padding: '4px 8px',
              borderRadius: 'var(--radius-sm)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '3px'
            }}
          >
            <Upload size={11} /> Upload
          </button>
          <button
            type="button"
            onClick={() => setMode('custom')}
            style={{
              background: mode === 'custom' ? 'rgba(99, 102, 241, 0.2)' : 'none',
              border: mode === 'custom' ? '1px solid rgba(99, 102, 241, 0.4)' : '1px solid transparent',
              color: mode === 'custom' ? 'var(--accent-indigo-light)' : 'var(--text-dim)',
              fontSize: '0.6875rem',
              fontWeight: 600,
              padding: '4px 8px',
              borderRadius: 'var(--radius-sm)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '3px'
            }}
          >
            <Sliders size={11} /> Text
          </button>
        </div>
      </div>

      {/* Mode 1: Presets & Ingested Catalog View */}
      {mode === 'presets' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', maxHeight: '420px', overflowY: 'auto' }}>
          {documents.map((preset) => {
            const isSelected = selectedDocId === preset.id;
            let tagColor = 'badge-indigo';
            if (preset.id === 'malicious_spoof_01') tagColor = 'badge-rose';
            else if (preset.id === 'rbi_2026_low_ocr_02') tagColor = 'badge-amber';
            else if (preset.id.startsWith('upload') || preset.id.startsWith('cir_uploaded')) tagColor = 'badge-cyan';
            else if (preset.id === 'ledger_pdf_official') tagColor = 'badge-emerald';
            else if (preset.id.startsWith('cir_')) tagColor = 'badge-emerald';

            return (
              <div
                key={preset.id}
                id={`preset-card-${preset.id}`}
                onClick={() => !isRunning && setSelectedDocId(preset.id)}
                style={{
                  padding: '12px 14px',
                  borderRadius: 'var(--radius-md)',
                  background: isSelected ? 'rgba(99, 102, 241, 0.12)' : 'rgba(255, 255, 255, 0.02)',
                  border: isSelected ? '1px solid rgba(99, 102, 241, 0.5)' : '1px solid var(--border-subtle)',
                  cursor: isRunning ? 'not-allowed' : 'pointer',
                  transition: 'all 0.2s ease',
                  boxShadow: isSelected ? '0 4px 14px rgba(99, 102, 241, 0.2)' : 'none'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '6px' }}>
                  <span className={`badge ${tagColor}`} style={{ fontSize: '0.6875rem' }}>
                    {preset.type || preset.category}
                  </span>
                  {isSelected && <CheckCircle2 size={16} color="var(--accent-indigo-light)" />}
                </div>
                <h3 style={{ fontSize: '0.8125rem', fontWeight: 600, marginBottom: '4px', lineHeight: 1.35 }}>
                  {preset.title}
                </h3>
                <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', lineHeight: 1.4, marginBottom: '6px' }}>
                  {preset.description}
                </p>
                {preset.expected_outcome && (
                  <div
                    style={{
                      fontSize: '0.6875rem',
                      color: 'var(--accent-cyan)',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px'
                    }}
                  >
                    <Zap size={11} /> {preset.expected_outcome}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Mode 2: Live Regulatory Monitoring Agent View */}
      {mode === 'monitor' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <div
            style={{
              padding: '14px',
              borderRadius: 'var(--radius-md)',
              background: 'rgba(16, 185, 129, 0.06)',
              border: '1px solid rgba(16, 185, 129, 0.25)',
              display: 'flex',
              flexDirection: 'column',
              gap: '10px'
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '0.8125rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '6px', color: '#10b981' }}>
                <Globe size={15} /> Automated Watchman Network
              </span>
              <span className="badge badge-emerald" style={{ fontSize: '0.625rem' }}>4 Portals Active</span>
            </div>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', lineHeight: 1.45 }}>
              Monitors RBI, SEBI, IRDAI, and NPCI announcement feeds. Deduplicates circulars via SHA-256 and stages them for autonomous ingestion.
            </p>

            <button
              onClick={handleTriggerCrawl}
              disabled={isCrawling || isRunning || backendHealth === 'offline'}
              className="btn btn-secondary"
              style={{
                width: '100%',
                padding: '8px 12px',
                fontSize: '0.75rem',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '6px'
              }}
            >
              {isCrawling ? (
                <>
                  <RefreshCw size={13} style={{ animation: 'spin 1s linear infinite' }} />
                  Crawling Portals...
                </>
              ) : (
                <>
                  <Radio size={13} color="#10b981" />
                  Trigger Regulatory Scan Now
                </>
              )}
            </button>
          </div>

          {crawlSummary && (
            <div
              style={{
                padding: '12px',
                borderRadius: 'var(--radius-sm)',
                background: 'rgba(99, 102, 241, 0.08)',
                border: '1px solid rgba(99, 102, 241, 0.25)',
                fontSize: '0.75rem',
                display: 'flex',
                flexDirection: 'column',
                gap: '6px'
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: 600 }}>
                <span>Scan Completed</span>
                <span style={{ color: 'var(--accent-indigo-light)' }}>{new Date(crawlSummary.crawled_at).toLocaleTimeString()}</span>
              </div>
              <div style={{ color: 'var(--text-muted)' }}>
                • Ingested <strong>{crawlSummary.new_documents_count}</strong> new circular(s)<br />
                • Skipped <strong>{crawlSummary.duplicates_count}</strong> duplicate(s) by SHA-256<br />
                • Total catalog: <strong>{crawlSummary.total_catalog_size}</strong> documents
              </div>
            </div>
          )}

          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <span style={{ fontSize: '0.6875rem', color: 'var(--text-dim)', fontWeight: 600 }}>MONITORED REGULATORS</span>
            {[
              { name: 'Reserve Bank of India (RBI)', domain: 'rbi.org.in' },
              { name: 'Securities and Exchange Board of India (SEBI)', domain: 'sebi.gov.in' },
              { name: 'Insurance Regulatory & Development Authority (IRDAI)', domain: 'irdai.gov.in' },
              { name: 'National Payments Corporation of India (NPCI)', domain: 'npci.org.in' }
            ].map((reg, idx) => (
              <div
                key={idx}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '6px 10px',
                  borderRadius: 'var(--radius-sm)',
                  background: 'var(--bg-surface)',
                  fontSize: '0.75rem'
                }}
              >
                <span>{reg.name}</span>
                <span className="badge badge-indigo" style={{ fontSize: '0.5625rem' }}>{reg.domain}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Mode 3: Upload File View */}
      {mode === 'upload' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <div
            onClick={() => fileInputRef.current?.click()}
            style={{
              padding: '30px 20px',
              borderRadius: 'var(--radius-md)',
              border: '2px dashed var(--border-medium)',
              background: 'rgba(6, 182, 212, 0.04)',
              textAlign: 'center',
              cursor: 'pointer',
              transition: 'all 0.2s ease'
            }}
          >
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileUpload}
              accept=".pdf,.html,.htm,.txt"
              style={{ display: 'none' }}
              disabled={isUploading || isRunning}
            />
            <FileUp size={32} color="var(--accent-cyan)" style={{ margin: '0 auto 10px', opacity: 0.8 }} />
            <h4 style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-main)' }}>
              {isUploading ? 'Validating Magic Bytes & Parsing...' : 'Click to Upload Regulatory Circular'}
            </h4>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px' }}>
              Accepts .pdf, .html, or .txt files (with spoofing checks & SHA-256 deduplication)
            </p>
          </div>

          {uploadSuccess && (
            <div
              style={{
                padding: '10px 12px',
                borderRadius: 'var(--radius-sm)',
                background: 'rgba(16, 185, 129, 0.1)',
                border: '1px solid rgba(16, 185, 129, 0.3)',
                fontSize: '0.75rem',
                color: '#10b981',
                display: 'flex',
                alignItems: 'center',
                gap: '6px'
              }}
            >
              <CheckCircle2 size={14} />
              <span>{uploadSuccess}</span>
            </div>
          )}

          {uploadError && (
            <div
              style={{
                padding: '10px 12px',
                borderRadius: 'var(--radius-sm)',
                background: 'rgba(244, 63, 94, 0.1)',
                border: '1px solid rgba(244, 63, 94, 0.3)',
                fontSize: '0.75rem',
                color: '#f43f5e'
              }}
            >
              {uploadError}
            </div>
          )}
        </div>
      )}

      {/* Mode 4: Custom Text View */}
      {mode === 'custom' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div>
            <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>
              Document Title
            </label>
            <input
              id="custom-document-title-input"
              type="text"
              placeholder="e.g., Master Direction on Digital Payment Tokenisation"
              value={customTitle}
              onChange={(e) => setCustomTitle(e.target.value)}
              disabled={isRunning}
              style={{
                width: '100%',
                padding: '10px 12px',
                background: 'var(--bg-surface)',
                border: '1px solid var(--border-medium)',
                borderRadius: 'var(--radius-sm)',
                color: 'var(--text-main)',
                fontSize: '0.8125rem'
              }}
            />
          </div>
          <div>
            <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>
              Regulatory Content / Directives Text
            </label>
            <textarea
              id="custom-document-text-textarea"
              rows={7}
              placeholder="Paste circular directives, mandates, or test security exploits..."
              value={customText}
              onChange={(e) => setCustomText(e.target.value)}
              disabled={isRunning}
              style={{
                width: '100%',
                padding: '10px 12px',
                background: 'var(--bg-surface)',
                border: '1px solid var(--border-medium)',
                borderRadius: 'var(--radius-sm)',
                color: 'var(--text-main)',
                fontSize: '0.8125rem',
                fontFamily: 'var(--font-mono)',
                lineHeight: 1.5,
                resize: 'vertical'
              }}
            />
          </div>
        </div>
      )}

      {/* Run & Reset Action Buttons */}
      <div style={{ display: 'flex', gap: '10px', marginTop: '18px' }}>
        <button
          id="trigger-agent-run-btn"
          className="btn btn-primary"
          onClick={handleTriggerRun}
          disabled={isRunning || backendHealth === 'offline'}
          style={{ flex: 1, padding: '12px' }}
        >
          {isRunning ? (
            <>
              <RefreshCw size={16} className="dot-pulsing" style={{ animation: 'spin 1s linear infinite' }} />
              Streaming Agent...
            </>
          ) : (
            <>
              <Play size={16} fill="currentColor" />
              Trigger Agent Workflow
            </>
          )}
        </button>
        <button
          id="reset-agent-session-btn"
          className="btn btn-secondary"
          onClick={onReset}
          disabled={isRunning}
          title="Reset session"
        >
          <RotateCcw size={16} />
        </button>
      </div>
    </div>
  );
}
