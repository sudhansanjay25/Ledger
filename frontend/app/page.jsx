'use client';

import React, { useState, useEffect, useRef } from 'react';
import {
  ShieldCheck,
  ShieldAlert,
  Cpu,
  Play,
  RotateCcw,
  Activity,
  FileText,
  CheckCircle2,
  AlertTriangle,
  Terminal,
  ChevronRight,
  Sparkles,
  Layers,
  Clock,
  Zap,
  ArrowRight,
  ExternalLink,
  Lock,
  AlertOctagon,
  RefreshCw,
  Sliders,
  Database,
  Hash,
  ListFilter
} from 'lucide-react';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000';

const PRESET_DOCUMENTS = [
  {
    id: 'rbi_2026_payment_sec_01',
    title: 'Master Direction – Security Measures for Digital Payment Transactions',
    badge: 'Standard Regulatory Ingestion',
    category: 'Cybersecurity & Payments',
    tagColor: 'badge-indigo',
    description: 'Enforces Multi-Factor Authentication (MFA), real-time fraud monitoring, and 7-year immutable audit trail rules.',
    expected: 'Full 7-point MAP extraction & compliance classification'
  },
  {
    id: 'malicious_spoof_01',
    title: 'Notification - Dynamic Guidelines on Regulatory Compliance',
    badge: 'Adversarial Injection Attack',
    category: 'Security Exploit Test',
    tagColor: 'badge-rose',
    description: 'Contains embedded [SYSTEM OVERRIDE DETECTED] commands attempting to hijack treasury funds.',
    expected: 'Security scan immediately halts pipeline & files Vault Complaint'
  },
  {
    id: 'rbi_2026_low_ocr_02',
    title: 'Notification - Update on AML / CFT Measures',
    badge: 'Degraded OCR Quality',
    category: 'Guardrail Test',
    tagColor: 'badge-amber',
    description: 'Severely corrupted OCR scan with degraded character recognition and failed page extraction.',
    expected: 'Reading quality score guardrail triggers manual review halt'
  }
];

export default function AgentDashboard() {
  const [selectedDocId, setSelectedDocId] = useState('rbi_2026_payment_sec_01');
  const [isCustomMode, setIsCustomMode] = useState(false);
  const [customTitle, setCustomTitle] = useState('');
  const [customText, setCustomText] = useState('');

  // Agent Execution State
  const [isRunning, setIsRunning] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [activeNode, setActiveNode] = useState(null); // 'planner' | 'tools' | null
  const [currentNodeActivity, setCurrentNodeActivity] = useState('');
  const [backendHealth, setBackendHealth] = useState('checking'); // 'healthy' | 'offline'

  // SSE Streamed Aggregated State
  const [agentState, setAgentState] = useState({
    document: {},
    security_scan: {},
    classification: {},
    extracted_maps: [],
    execution_logs: [],
    terminate: false,
    messages: []
  });

  const [eventsFeed, setEventsFeed] = useState([]);
  const [activeTab, setActiveTab] = useState('maps'); // 'maps' | 'security' | 'document' | 'reasoning'
  const [executionTime, setExecutionTime] = useState(0);
  const [stepCount, setStepCount] = useState(0);
  const [finalOutcome, setFinalOutcome] = useState(null);

  const eventSourceRef = useRef(null);
  const terminalEndRef = useRef(null);
  const timerRef = useRef(null);

  // Check Backend Health on mount
  useEffect(() => {
    async function checkHealth() {
      try {
        const res = await fetch(`${API_BASE_URL}/api/health`, { cache: 'no-store' });
        if (res.ok) {
          setBackendHealth('healthy');
        } else {
          setBackendHealth('offline');
        }
      } catch (err) {
        setBackendHealth('offline');
      }
    }
    checkHealth();
    const interval = setInterval(checkHealth, 10000);
    return () => clearInterval(interval);
  }, []);

  // Execution Timer
  useEffect(() => {
    if (isRunning) {
      const startTime = Date.now() - executionTime * 1000;
      timerRef.current = setInterval(() => {
        setExecutionTime(((Date.now() - startTime) / 1000).toFixed(1));
      }, 100);
    } else {
      if (timerRef.current) clearInterval(timerRef.current);
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [isRunning]);

  // Auto-scroll terminal logs
  useEffect(() => {
    if (terminalEndRef.current) {
      terminalEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [eventsFeed]);

  // Clean up SSE connection on unmount
  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, []);

  const handleReset = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    setIsRunning(false);
    setSessionId(null);
    setActiveNode(null);
    setCurrentNodeActivity('');
    setExecutionTime(0);
    setStepCount(0);
    setFinalOutcome(null);
    setEventsFeed([]);
    setAgentState({
      document: {},
      security_scan: {},
      classification: {},
      extracted_maps: [],
      execution_logs: [],
      terminate: false,
      messages: []
    });
  };

  const handleRunAgent = async () => {
    if (isRunning) return;

    handleReset();
    setIsRunning(true);
    setExecutionTime(0);
    setStepCount(0);
    setFinalOutcome(null);

    const payload = isCustomMode
      ? {
          document_id: `custom_${Date.now()}`,
          custom_title: customTitle || 'Custom Regulatory Directive',
          custom_text: customText || 'No text provided.'
        }
      : {
          document_id: selectedDocId
        };

    try {
      // 1. Trigger agent run via POST
      const res = await fetch(`${API_BASE_URL}/api/agent/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        throw new Error(`Failed to start agent: ${res.statusText}`);
      }

      const data = await res.json();
      const newSessionId = data.session_id;
      setSessionId(newSessionId);

      // 2. Connect to SSE stream
      const sseUrl = `${API_BASE_URL}/api/agent/stream/${newSessionId}`;
      const sse = new EventSource(sseUrl);
      eventSourceRef.current = sse;

      sse.onmessage = (e) => {
        try {
          const event = JSON.parse(e.data);

          if (event.type === 'agent_start') {
            setActiveNode('planner');
            setCurrentNodeActivity(event.message);
            setEventsFeed((prev) => [...prev, { ...event, id: `evt-${Date.now()}-${Math.random()}` }]);
          } else if (event.type === 'step_update') {
            setStepCount(event.step);
            setActiveNode(event.node);
            setCurrentNodeActivity(event.activity);
            if (event.state) {
              setAgentState(event.state);
            }
            setEventsFeed((prev) => [...prev, { ...event, id: `evt-${Date.now()}-${Math.random()}` }]);
          } else if (event.type === 'agent_complete') {
            setIsRunning(false);
            setActiveNode(null);
            setFinalOutcome(event.outcome);
            if (event.final_state) {
              setAgentState(event.final_state);
            }
            setEventsFeed((prev) => [...prev, { ...event, id: `evt-${Date.now()}-${Math.random()}` }]);
            sse.close();
          } else if (event.type === 'agent_error') {
            setIsRunning(false);
            setActiveNode(null);
            setFinalOutcome('ERROR');
            setEventsFeed((prev) => [...prev, { ...event, id: `evt-${Date.now()}-${Math.random()}` }]);
            sse.close();
          } else if (event.type === 'stream_end') {
            setIsRunning(false);
            sse.close();
          }
        } catch (parseErr) {
          console.error('Error parsing SSE event data:', parseErr);
        }
      };

      sse.onerror = (err) => {
        console.error('SSE Stream error:', err);
        setIsRunning(false);
        sse.close();
      };
    } catch (err) {
      console.error('Run agent error:', err);
      setIsRunning(false);
      setEventsFeed((prev) => [
        ...prev,
        {
          type: 'agent_error',
          error: err.message,
          timestamp: new Date().toISOString(),
          id: `err-${Date.now()}`
        }
      ]);
    }
  };

  const selectedPreset = PRESET_DOCUMENTS.find((d) => d.id === selectedDocId);

  // Derive latest LLM reasoning
  const finalAiMessage = agentState.messages
    ?.filter((m) => m.role === 'assistant' && m.content)
    ?.slice(-1)[0]?.content;

  return (
    <main style={{ minHeight: '100vh', padding: '24px 32px 60px' }}>
      {/* --- Top Navigation & Header --- */}
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
              isRunning ? 'badge-cyan dot-pulsing' : finalOutcome === 'THREAT_BLOCKED' ? 'badge-rose' : 'badge-indigo'
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

      {/* --- Main Cockpit Grid --- */}
      <div style={{ display: 'grid', gridTemplateColumns: '380px 1fr', gap: '24px' }}>
        {/* === Left Column: Launchpad & Controls === */}
        <section style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {/* Preset Selector Card */}
          <div className="glass-panel" style={{ padding: '20px' }}>
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
                Select Ingestion Target
              </h2>
              <button
                id="toggle-custom-input-btn"
                onClick={() => setIsCustomMode(!isCustomMode)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: isCustomMode ? 'var(--accent-cyan)' : 'var(--text-dim)',
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px'
                }}
              >
                <Sliders size={13} />
                {isCustomMode ? 'Presets' : 'Custom Input'}
              </button>
            </div>

            {!isCustomMode ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {PRESET_DOCUMENTS.map((preset) => {
                  const isSelected = selectedDocId === preset.id;
                  return (
                    <div
                      key={preset.id}
                      id={`preset-card-${preset.id}`}
                      onClick={() => !isRunning && setSelectedDocId(preset.id)}
                      style={{
                        padding: '14px',
                        borderRadius: 'var(--radius-md)',
                        background: isSelected ? 'rgba(99, 102, 241, 0.12)' : 'rgba(255, 255, 255, 0.02)',
                        border: isSelected ? '1px solid rgba(99, 102, 241, 0.5)' : '1px solid var(--border-subtle)',
                        cursor: isRunning ? 'not-allowed' : 'pointer',
                        transition: 'all 0.2s ease',
                        boxShadow: isSelected ? '0 4px 14px rgba(99, 102, 241, 0.2)' : 'none'
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '6px' }}>
                        <span className={`badge ${preset.tagColor}`} style={{ fontSize: '0.6875rem' }}>
                          {preset.badge}
                        </span>
                        {isSelected && <CheckCircle2 size={16} color="var(--accent-indigo-light)" />}
                      </div>
                      <h3 style={{ fontSize: '0.875rem', fontWeight: 600, marginBottom: '6px', lineHeight: 1.35 }}>
                        {preset.title}
                      </h3>
                      <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', lineHeight: 1.45, marginBottom: '8px' }}>
                        {preset.description}
                      </p>
                      <div
                        style={{
                          fontSize: '0.6875rem',
                          color: 'var(--accent-cyan)',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '5px'
                        }}
                      >
                        <Zap size={12} /> {preset.expected}
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <div>
                  <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>
                    Document Title
                  </label>
                  <input
                    id="custom-document-title-input"
                    type="text"
                    placeholder="e.g., Circular on Cloud Outsourcing Risks"
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
                    Regulatory Content / Plain Text
                  </label>
                  <textarea
                    id="custom-document-text-textarea"
                    rows={7}
                    placeholder="Paste regulation text with compliance directives or test attacks..."
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
                onClick={handleRunAgent}
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
                onClick={handleReset}
                disabled={isRunning}
                title="Reset session"
              >
                <RotateCcw size={16} />
              </button>
            </div>
          </div>

          {/* Live Execution Logs & SSE Event Stream */}
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
        </section>

        {/* === Right Column: Interactive State Graph & Artifacts === */}
        <section style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {/* --- Interactive State Graph Diagram --- */}
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

              {/* Node 2: Planner (Groq LLM) */}
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
                  {activeNode === 'planner' ? 'Reasoning / Deciding...' : 'Groq LLM Decision'}
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
                      : 'var(--bg-surface)',
                  border:
                    finalOutcome === 'THREAT_BLOCKED'
                      ? '1px solid rgba(244, 63, 94, 0.6)'
                      : finalOutcome === 'SUCCESS'
                      ? '1px solid rgba(16, 185, 129, 0.6)'
                      : '1px solid var(--border-subtle)',
                  textAlign: 'center',
                  transition: 'all 0.3s ease'
                }}
              >
                <div style={{ display: 'inline-flex', padding: '8px', borderRadius: '50%', background: 'rgba(255, 255, 255, 0.05)', marginBottom: '8px' }}>
                  {finalOutcome === 'THREAT_BLOCKED' ? (
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
                    : 'Awaiting Run'}
                </div>
              </div>
            </div>
          </div>

          {/* --- Multi-Tab State Inspector --- */}
          <div className="glass-panel" style={{ padding: '24px', flex: 1 }}>
            {/* Tab Navigation */}
            <div
              style={{
                display: 'flex',
                gap: '8px',
                borderBottom: '1px solid var(--border-subtle)',
                paddingBottom: '14px',
                marginBottom: '20px'
              }}
            >
              {[
                { id: 'maps', label: 'Measurable Action Points (MAPs)', count: agentState.extracted_maps?.length || 0, icon: <ListFilter size={15} /> },
                { id: 'security', label: 'Security Shield & Guardrails', alert: agentState.security_scan?.is_safe === false, icon: <Lock size={15} /> },
                { id: 'document', label: 'Document Context & OCR', icon: <FileText size={15} /> },
                { id: 'reasoning', label: 'Agent Reasoning & Summary', icon: <Cpu size={15} /> }
              ].map((tab) => {
                const isActive = activeTab === tab.id;
                return (
                  <button
                    key={tab.id}
                    id={`tab-btn-${tab.id}`}
                    onClick={() => setActiveTab(tab.id)}
                    style={{
                      background: isActive ? 'rgba(99, 102, 241, 0.15)' : 'none',
                      border: isActive ? '1px solid rgba(99, 102, 241, 0.35)' : '1px solid transparent',
                      color: isActive ? 'var(--text-main)' : 'var(--text-muted)',
                      padding: '8px 16px',
                      borderRadius: 'var(--radius-md)',
                      fontSize: '0.8125rem',
                      fontWeight: 600,
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px',
                      transition: 'all 0.2s ease'
                    }}
                  >
                    {tab.icon}
                    <span>{tab.label}</span>
                    {tab.count !== undefined && tab.count > 0 && (
                      <span className="badge badge-indigo" style={{ padding: '1px 6px', fontSize: '0.625rem' }}>
                        {tab.count}
                      </span>
                    )}
                    {tab.alert && (
                      <span className="badge badge-rose" style={{ padding: '1px 6px', fontSize: '0.625rem' }}>
                        Alert
                      </span>
                    )}
                  </button>
                );
              })}
            </div>

            {/* --- TAB 1: Measurable Action Points (MAPs) --- */}
            {activeTab === 'maps' && (
              <div>
                {agentState.extracted_maps && agentState.extracted_maps.length > 0 ? (
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
                          {agentState.extracted_maps.length} Action Points Extracted
                        </span>
                        <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                          Each action point contains structured departmental routing, deadline parsing, and confidence scoring.
                        </p>
                      </div>
                      <div style={{ display: 'flex', gap: '8px' }}>
                        <span className="badge badge-rose">
                          {agentState.extracted_maps.filter((m) => m.priority === 'Critical').length} Critical
                        </span>
                        <span className="badge badge-indigo">
                          {agentState.extracted_maps.filter((m) => m.obligation_type === 'REQUIRED').length} Required
                        </span>
                      </div>
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                      {agentState.extracted_maps.map((mapItem, idx) => (
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
                              <span
                                className={`badge ${
                                  mapItem.priority === 'Critical' ? 'badge-rose' : 'badge-amber'
                                }`}
                              >
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
                ) : (
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
                )}
              </div>
            )}

            {/* --- TAB 2: Security Shield & Guardrails --- */}
            {activeTab === 'security' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                {/* Security Verdict Banner */}
                <div
                  id="security-verdict-banner"
                  style={{
                    padding: '18px',
                    borderRadius: 'var(--radius-md)',
                    background:
                      agentState.security_scan?.is_safe === false
                        ? 'rgba(244, 63, 94, 0.12)'
                        : agentState.security_scan?.is_safe === true
                        ? 'rgba(16, 185, 129, 0.12)'
                        : 'rgba(255, 255, 255, 0.03)',
                    border:
                      agentState.security_scan?.is_safe === false
                        ? '1px solid rgba(244, 63, 94, 0.4)'
                        : agentState.security_scan?.is_safe === true
                        ? '1px solid rgba(16, 185, 129, 0.4)'
                        : '1px solid var(--border-subtle)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '14px'
                  }}
                >
                  {agentState.security_scan?.is_safe === false ? (
                    <AlertOctagon size={32} color="#f43f5e" />
                  ) : agentState.security_scan?.is_safe === true ? (
                    <ShieldCheck size={32} color="#10b981" />
                  ) : (
                    <Lock size={32} color="var(--text-dim)" />
                  )}
                  <div>
                    <h3 style={{ fontSize: '0.95rem', fontWeight: 700 }}>
                      {agentState.security_scan?.is_safe === false
                        ? `Security Threat Blocked: ${agentState.security_scan?.threat_detected}`
                        : agentState.security_scan?.is_safe === true
                        ? 'All Security Guardrails Passed'
                        : 'Security Scan Pending'}
                    </h3>
                    <p style={{ fontSize: '0.8125rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                      {agentState.security_scan?.details ||
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
                      passed: agentState.security_scan?.is_safe !== undefined
                    },
                    {
                      name: 'Unicode Homoglyph Detection',
                      desc: 'Scans for spoofed Cyrillic / visually identical characters disguised as English letters.',
                      passed: agentState.security_scan?.is_safe !== undefined
                    },
                    {
                      name: 'Directional RTL Character Scan',
                      desc: 'Detects hidden right-to-left directional override markers (\u202E) used to distort instructions.',
                      passed: agentState.security_scan?.is_safe !== undefined
                    },
                    {
                      name: 'Prompt Injection Defense',
                      desc: 'Flags regex and semantic instruction-override triggers (e.g., "[SYSTEM OVERRIDE DETECTED]").',
                      passed: agentState.security_scan?.is_safe === true,
                      failed: agentState.security_scan?.threat_detected === 'Prompt Injection Attempt'
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
                {agentState.security_scan?.logs && agentState.security_scan.logs.length > 0 && (
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
                      {agentState.security_scan.logs.map((log, idx) => (
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
            )}

            {/* --- TAB 3: Document Context & OCR --- */}
            {activeTab === 'document' && (
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
                      {agentState.document?.id || selectedDocId}
                    </div>
                  </div>

                  <div style={{ padding: '14px', borderRadius: 'var(--radius-md)', background: 'var(--bg-surface-elevated)', border: '1px solid var(--border-subtle)' }}>
                    <span style={{ fontSize: '0.6875rem', color: 'var(--text-dim)', fontWeight: 600 }}>FORMAT & ENCODING</span>
                    <div style={{ fontSize: '0.875rem', fontWeight: 600, marginTop: '4px' }}>
                      {agentState.document?.format || 'Digital PDF'}
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
                            width: `${(agentState.document?.quality_score ?? 1.0) * 100}%`,
                            height: '100%',
                            backgroundColor: (agentState.document?.quality_score ?? 1.0) < 0.5 ? '#f43f5e' : '#10b981'
                          }}
                        />
                      </div>
                      <span style={{ fontSize: '0.8125rem', fontFamily: 'var(--font-mono)', fontWeight: 700 }}>
                        {((agentState.document?.quality_score ?? 1.0) * 100).toFixed(0)}%
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
                    {agentState.document?.cleaned_text || agentState.document?.raw_text || 'No document text ingested yet.'}
                  </div>
                </div>
              </div>
            )}

            {/* --- TAB 4: Agent Reasoning & Summary --- */}
            {activeTab === 'reasoning' && (
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
                      Once the agent workflow executes, the LLM planner synthesizes circular observations,
                      deadlines, and findings here.
                    </p>
                  </div>
                )}
              </div>
            )}
          </div>
        </section>
      </div>
    </main>
  );
}
