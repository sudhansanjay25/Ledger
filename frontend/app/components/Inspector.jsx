'use client';

import React, { useState } from 'react';
import { ListFilter, Lock, FileText, Cpu } from 'lucide-react';
import MapsTab from './tabs/MapsTab';
import SecurityShieldTab from './tabs/SecurityShieldTab';
import DocumentContextTab from './tabs/DocumentContextTab';
import ReasoningTab from './tabs/ReasoningTab';

export default function Inspector({ agentState, selectedDocId, finalOutcome }) {
  const [activeTab, setActiveTab] = useState('maps');

  const tabs = [
    {
      id: 'maps',
      label: 'Measurable Action Points (MAPs)',
      count: agentState.extracted_maps?.length || 0,
      icon: <ListFilter size={15} />
    },
    {
      id: 'security',
      label: 'Security Shield & Guardrails',
      alert: agentState.security_scan?.is_safe === false,
      icon: <Lock size={15} />
    },
    {
      id: 'document',
      label: 'Document Context & OCR',
      icon: <FileText size={15} />
    },
    {
      id: 'reasoning',
      label: 'Agent Reasoning & Summary',
      icon: <Cpu size={15} />
    }
  ];

  return (
    <div className="glass-panel" style={{ padding: '24px', flex: 1 }}>
      {/* Tab Navigation */}
      <div
        style={{
          display: 'flex',
          gap: '8px',
          borderBottom: '1px solid var(--border-subtle)',
          paddingBottom: '14px',
          marginBottom: '20px',
          overflowX: 'auto'
        }}
      >
        {tabs.map((tab) => {
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
                transition: 'all 0.2s ease',
                whiteSpace: 'nowrap'
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

      {/* Tab Contents */}
      {activeTab === 'maps' && (
        <MapsTab extractedMaps={agentState.extracted_maps} finalOutcome={finalOutcome} />
      )}
      {activeTab === 'security' && (
        <SecurityShieldTab securityScan={agentState.security_scan} />
      )}
      {activeTab === 'document' && (
        <DocumentContextTab document={agentState.document} selectedDocId={selectedDocId} />
      )}
      {activeTab === 'reasoning' && (
        <ReasoningTab messages={agentState.messages} />
      )}
    </div>
  );
}
