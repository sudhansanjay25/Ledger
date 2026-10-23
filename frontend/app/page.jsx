'use client';

import React, { useState, useEffect, useRef } from 'react';
import Header from './components/Header';
import Launchpad from './components/Launchpad';
import DAGVisualizer from './components/DAGVisualizer';
import TerminalFeed from './components/TerminalFeed';
import Inspector from './components/Inspector';
import ErrorBanner from './components/ErrorBanner';
import ExecutiveDashboard from './components/ExecutiveDashboard';
import { Cpu, LayoutDashboard } from 'lucide-react';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000';

const DEFAULT_DOCUMENTS = [
  {
    id: 'rbi_2026_payment_sec_01',
    title: 'Master Direction – Security Measures for Digital Payment Transactions',
    type: 'Standard Regulatory Ingestion',
    category: 'Cybersecurity & Payments',
    description: 'Enforces Multi-Factor Authentication (MFA), real-time fraud monitoring, and 7-year immutable audit trail rules.',
    expected_outcome: 'Full 7-point MAP extraction & compliance classification'
  },
  {
    id: 'malicious_spoof_01',
    title: 'Notification - Dynamic Guidelines on Regulatory Compliance',
    type: 'Adversarial Injection Attack',
    category: 'Security Exploit Test',
    description: 'Contains embedded [SYSTEM OVERRIDE DETECTED] commands attempting to hijack treasury funds.',
    expected_outcome: 'Security scan immediately halts pipeline & files Vault Complaint'
  },
  {
    id: 'rbi_2026_low_ocr_02',
    title: 'Notification - Update on AML / CFT Measures',
    type: 'Degraded OCR Quality',
    category: 'Guardrail Test',
    description: 'Severely corrupted OCR scan with degraded character recognition and failed page extraction.',
    expected_outcome: 'Reading quality score guardrail triggers manual review halt'
  }
];

export default function AgentDashboard() {
  const [documents, setDocuments] = useState(DEFAULT_DOCUMENTS);
  const [selectedDocId, setSelectedDocId] = useState('rbi_2026_payment_sec_01');
  const [viewMode, setViewMode] = useState('pipeline'); // 'pipeline' | 'dashboard'

  // Agent Execution State
  const [isRunning, setIsRunning] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [activeNode, setActiveNode] = useState(null);
  const [currentNodeActivity, setCurrentNodeActivity] = useState('');
  const [backendHealth, setBackendHealth] = useState('checking');
  const [errorMessage, setErrorMessage] = useState(null);

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
  const [executionTime, setExecutionTime] = useState(0);
  const [stepCount, setStepCount] = useState(0);
  const [finalOutcome, setFinalOutcome] = useState(null);

  const eventSourceRef = useRef(null);
  const terminalEndRef = useRef(null);
  const timerRef = useRef(null);

  // Check Backend Health & Fetch dynamic documents
  const fetchBackendData = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/health`, { cache: 'no-store' });
      if (res.ok) {
        setBackendHealth('healthy');
        setErrorMessage(null);
        // Fetch dynamic documents
        const docsRes = await fetch(`${API_BASE_URL}/api/documents`);
        if (docsRes.ok) {
          const docsData = await docsRes.json();
          if (docsData.documents && docsData.documents.length > 0) {
            setDocuments(docsData.documents);
          }
        }
      } else {
        setBackendHealth('offline');
      }
    } catch (err) {
      setBackendHealth('offline');
    }
  };

  useEffect(() => {
    fetchBackendData();
    const interval = setInterval(fetchBackendData, 10000);
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
    setErrorMessage(null);
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

  const handleDocumentUploaded = (docData) => {
    setDocuments((prev) => [
      {
        id: docData.document_id,
        title: docData.title,
        type: `Uploaded ${docData.format?.replace('_', ' ').toUpperCase() || 'Document'}`,
        category: 'User Uploaded File',
        description: `Uploaded file with ${docData.total_words} words across ${docData.page_count} page(s). Quality score: ${docData.quality_score}.`,
        expected_outcome: 'Pipeline ingestion and MAP structuring'
      },
      ...prev
    ]);
  };

  const handleRunAgent = async ({ isCustom, customTitle, customText } = {}) => {
    if (isRunning) return;

    handleReset();
    setIsRunning(true);
    setExecutionTime(0);
    setStepCount(0);
    setFinalOutcome(null);
    setErrorMessage(null);

    const payload = isCustom
      ? {
          document_id: `custom_${Date.now()}`,
          custom_title: customTitle || 'Custom Regulatory Directive',
          custom_text: customText || 'No text provided.'
        }
      : {
          document_id: selectedDocId
        };

    try {
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

      // Connect to SSE stream
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
            setErrorMessage(event.error || 'Agent encountered an execution error');
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
        setFinalOutcome('ERROR');
        setErrorMessage('Lost connection to SSE stream from Flask backend.');
        sse.close();
      };
    } catch (err) {
      console.error('Run agent error:', err);
      setIsRunning(false);
      setFinalOutcome('ERROR');
      setErrorMessage(err.message || 'Failed to trigger agent workflow');
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

  return (
    <main style={{ minHeight: '100vh', padding: '24px 32px 60px' }}>
      <Header
        backendHealth={backendHealth}
        isRunning={isRunning}
        finalOutcome={finalOutcome}
        executionTime={executionTime}
        stepCount={stepCount}
      />

      {backendHealth === 'offline' && (
        <ErrorBanner
          error="Flask Backend is currently offline. Start the backend with: uv run python backend/app.py"
          onRetry={fetchBackendData}
        />
      )}

      {errorMessage && (
        <ErrorBanner
          error={errorMessage}
          onDismiss={() => setErrorMessage(null)}
          onRetry={() => handleRunAgent()}
        />
      )}

      {/* Primary View Mode Switcher */}
      <div style={{ display: 'flex', gap: '8px', marginBottom: '24px' }}>
        <button
          onClick={() => setViewMode('pipeline')}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '10px 20px',
            borderRadius: 'var(--radius-md)',
            fontWeight: 700,
            fontSize: '0.875rem',
            border: 'none',
            cursor: 'pointer',
            background: viewMode === 'pipeline' ? 'linear-gradient(135deg, #6366f1, #06b6d4)' : 'rgba(255, 255, 255, 0.05)',
            color: viewMode === 'pipeline' ? '#ffffff' : 'var(--text-muted)',
            boxShadow: viewMode === 'pipeline' ? '0 0 15px rgba(99, 102, 241, 0.3)' : 'none',
            transition: 'all 0.2s ease'
          }}
        >
          <Cpu size={16} />
          Agent Pipeline Cockpit
        </button>

        <button
          onClick={() => setViewMode('dashboard')}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '10px 20px',
            borderRadius: 'var(--radius-md)',
            fontWeight: 700,
            fontSize: '0.875rem',
            border: 'none',
            cursor: 'pointer',
            background: viewMode === 'dashboard' ? 'linear-gradient(135deg, #6366f1, #06b6d4)' : 'rgba(255, 255, 255, 0.05)',
            color: viewMode === 'dashboard' ? '#ffffff' : 'var(--text-muted)',
            boxShadow: viewMode === 'dashboard' ? '0 0 15px rgba(99, 102, 241, 0.3)' : 'none',
            transition: 'all 0.2s ease'
          }}
        >
          <LayoutDashboard size={16} />
          Multi-Role Executive Dashboard
        </button>
      </div>

      {viewMode === 'dashboard' ? (
        <ExecutiveDashboard
          onSelectDocumentForAgent={(docId) => {
            setSelectedDocId(docId);
            setViewMode('pipeline');
          }}
        />
      ) : (
        /* Main Cockpit Grid */
        <div style={{ display: 'grid', gridTemplateColumns: '380px 1fr', gap: '24px' }}>
          {/* Left Column: Launchpad & Terminal */}
          <section style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <Launchpad
              documents={documents}
              selectedDocId={selectedDocId}
              setSelectedDocId={setSelectedDocId}
              isRunning={isRunning}
              backendHealth={backendHealth}
              onRun={handleRunAgent}
              onReset={handleReset}
              apiBaseUrl={API_BASE_URL}
              onDocumentUploaded={handleDocumentUploaded}
              onRefreshDocuments={fetchBackendData}
            />

            <TerminalFeed
              eventsFeed={eventsFeed}
              terminalEndRef={terminalEndRef}
            />
          </section>

          {/* Right Column: DAG Visualizer & State Inspector */}
          <section style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <DAGVisualizer
              activeNode={activeNode}
              currentNodeActivity={currentNodeActivity}
              agentState={agentState}
              finalOutcome={finalOutcome}
            />

            <Inspector
              agentState={agentState}
              selectedDocId={selectedDocId}
              finalOutcome={finalOutcome}
            />
          </section>
        </div>
      )}
    </main>
  );
}
