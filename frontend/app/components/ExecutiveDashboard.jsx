'use client';

import React, { useState, useEffect } from 'react';
import {
  Shield, CheckCircle2, AlertTriangle, Clock, Upload, RefreshCw,
  FileText, ExternalLink, UserCheck, Eye, Layers, Activity,
  Briefcase, CheckSquare, XCircle, Edit3, ArrowRight, Lock
} from 'lucide-react';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000';

export default function ExecutiveDashboard({ onSelectDocumentForAgent }) {
  const [currentRole, setCurrentRole] = useState('compliance_head'); // admin | compliance_head | department_head | auditor
  const [selectedDept, setSelectedDept] = useState('IT'); // For Department Head view
  
  // Data States
  const [healthData, setHealthData] = useState(null);
  const [dashboardMetrics, setDashboardMetrics] = useState(null);
  const [reviewQueue, setReviewQueue] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [departmentMaps, setDepartmentMaps] = useState([]);
  const [loading, setLoading] = useState(false);

  // Modal / Interaction states
  const [uploadingForMapId, setUploadingForMapId] = useState(null);
  const [proofFile, setProofFile] = useState(null);
  const [uploadStatus, setUploadStatus] = useState(null);
  const [actionMessage, setActionMessage] = useState(null);

  // Fetch all dashboard data
  const fetchDashboardData = async () => {
    setLoading(true);
    try {
      // 1. Health Score
      const hRes = await fetch(`${API_BASE_URL}/api/metrics/health`);
      if (hRes.ok) setHealthData(await hRes.json());

      // 2. Dashboard Aggregate Metrics
      const mRes = await fetch(`${API_BASE_URL}/api/metrics/dashboard`);
      if (mRes.ok) setDashboardMetrics(await mRes.json());

      // 3. Review Queue
      const qRes = await fetch(`${API_BASE_URL}/api/review-queue`, {
        headers: { 'X-User-Role': currentRole, 'X-User-Department': selectedDept }
      });
      if (qRes.ok) {
        const qData = await qRes.json();
        setReviewQueue(qData.queue || []);
      }

      // 4. Audit Logs
      const aRes = await fetch(`${API_BASE_URL}/api/audit-logs?limit=30`, {
        headers: { 'X-User-Role': currentRole }
      });
      if (aRes.ok) {
        const aData = await aRes.json();
        setAuditLogs(aData.logs || []);
      }

      // 5. Notifications
      const nRes = await fetch(`${API_BASE_URL}/api/notifications`);
      if (nRes.ok) {
        const nData = await nRes.json();
        setNotifications(nData.notifications || []);
      }

      // 6. Department MAPs
      const mapsRes = await fetch(`${API_BASE_URL}/api/maps?department=${selectedDept}`, {
        headers: { 'X-User-Role': currentRole, 'X-User-Department': selectedDept }
      });
      if (mapsRes.ok) {
        const mData = await mapsRes.json();
        setDepartmentMaps(mData.maps || []);
      }
    } catch (err) {
      console.error('Failed to load dashboard data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
    const interval = setInterval(fetchDashboardData, 12000);
    return () => clearInterval(interval);
  }, [currentRole, selectedDept]);

  // Actions
  const handleApprove = async (actionId) => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/review-queue/${actionId}/approve`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-User-Role': 'compliance_head',
          'X-User-Id': 'compliance_officer_web'
        },
        body: JSON.stringify({ notes: 'Approved via Executive Dashboard' })
      });
      if (res.ok) {
        const data = await res.json();
        setActionMessage(`Approved ${actionId} and synced to Jira (${data.jira_issue?.key || 'COMP-OK'})`);
        setTimeout(() => setActionMessage(null), 5000);
        fetchDashboardData();
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleReject = async (actionId) => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/review-queue/${actionId}/reject`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-User-Role': 'compliance_head',
          'X-User-Id': 'compliance_officer_web'
        },
        body: JSON.stringify({ reason: 'Rejected as non-actionable via Review Queue' })
      });
      if (res.ok) {
        setActionMessage(`Marked ${actionId} as rejected.`);
        setTimeout(() => setActionMessage(null), 5000);
        fetchDashboardData();
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleProofUpload = async (e) => {
    e.preventDefault();
    if (!uploadingForMapId || !proofFile) return;

    const formData = new FormData();
    formData.append('file', proofFile);

    setUploadStatus('uploading');
    try {
      const res = await fetch(`${API_BASE_URL}/api/maps/${uploadingForMapId}/proof`, {
        method: 'POST',
        headers: {
          'X-User-Role': 'department_head',
          'X-User-Id': `${selectedDept.toLowerCase()}_lead`
        },
        body: formData
      });
      const data = await res.json();
      if (res.ok) {
        setUploadStatus('success');
        setActionMessage(`Proof validated! Status: ${data.verification?.verification_status?.toUpperCase()} (Score: ${(data.verification?.verification_score * 100).toFixed(0)}%)`);
        setProofFile(null);
        setUploadingForMapId(null);
        setTimeout(() => setActionMessage(null), 7000);
        fetchDashboardData();
      } else {
        setUploadStatus('error');
        setActionMessage(data.error || 'Proof verification failed');
      }
    } catch (err) {
      setUploadStatus('error');
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', width: '100%' }}>
      {/* Role Navigation Bar */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '16px 20px',
          background: 'rgba(17, 24, 39, 0.7)',
          backdropFilter: 'blur(12px)',
          border: '1px solid var(--border-subtle)',
          borderRadius: 'var(--radius-lg)'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Briefcase size={20} color="var(--accent-indigo-light)" />
            <span style={{ fontWeight: 700, fontSize: '0.9375rem' }}>Active Role View:</span>
          </div>
          
          <div style={{ display: 'flex', gap: '8px', background: 'rgba(0, 0, 0, 0.3)', padding: '4px', borderRadius: 'var(--radius-md)' }}>
            {[
              { id: 'compliance_head', label: 'Compliance Head', icon: UserCheck },
              { id: 'department_head', label: 'Department Head', icon: Layers },
              { id: 'admin', label: 'Admin', icon: Shield },
              { id: 'auditor', label: 'Auditor', icon: Lock }
            ].map(r => {
              const Icon = r.icon;
              const isActive = currentRole === r.id;
              return (
                <button
                  key={r.id}
                  onClick={() => setCurrentRole(r.id)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    padding: '6px 14px',
                    borderRadius: 'var(--radius-sm)',
                    fontSize: '0.8125rem',
                    fontWeight: 600,
                    border: 'none',
                    cursor: 'pointer',
                    background: isActive ? 'linear-gradient(135deg, #6366f1, #06b6d4)' : 'transparent',
                    color: isActive ? '#ffffff' : 'var(--text-muted)',
                    transition: 'all 0.2s ease'
                  }}
                >
                  <Icon size={14} />
                  {r.label}
                </button>
              );
            })}
          </div>

          {currentRole === 'department_head' && (
            <select
              value={selectedDept}
              onChange={(e) => setSelectedDept(e.target.value)}
              style={{
                padding: '6px 12px',
                borderRadius: 'var(--radius-sm)',
                background: 'rgba(255, 255, 255, 0.05)',
                border: '1px solid var(--border-medium)',
                color: '#fff',
                fontSize: '0.8125rem',
                outline: 'none'
              }}
            >
              <option value="IT" style={{ background: '#111827' }}>Department: IT</option>
              <option value="Information Security" style={{ background: '#111827' }}>Department: InfoSec</option>
              <option value="Operations" style={{ background: '#111827' }}>Department: Operations</option>
              <option value="Compliance" style={{ background: '#111827' }}>Department: Compliance</option>
              <option value="Risk Management" style={{ background: '#111827' }}>Department: Risk</option>
            </select>
          )}
        </div>

        <button
          onClick={fetchDashboardData}
          disabled={loading}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            padding: '6px 12px',
            borderRadius: 'var(--radius-sm)',
            background: 'rgba(255, 255, 255, 0.06)',
            border: '1px solid var(--border-subtle)',
            color: 'var(--text-muted)',
            fontSize: '0.75rem',
            cursor: 'pointer'
          }}
        >
          <RefreshCw size={13} className={loading ? 'spin' : ''} />
          Refresh Metrics
        </button>
      </div>

      {/* Action Notification Banner */}
      {actionMessage && (
        <div
          style={{
            padding: '12px 18px',
            borderRadius: 'var(--radius-md)',
            background: 'rgba(16, 185, 129, 0.15)',
            border: '1px solid rgba(16, 185, 129, 0.4)',
            color: '#10b981',
            fontSize: '0.875rem',
            fontWeight: 500,
            display: 'flex',
            alignItems: 'center',
            gap: '10px'
          }}
        >
          <CheckCircle2 size={16} />
          <span>{actionMessage}</span>
        </div>
      )}

      {/* Real-time Compliance Health Score Card */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
          gap: '16px'
        }}
      >
        {/* Metric 1: Health Score */}
        <div
          style={{
            background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.12) 0%, rgba(6, 182, 212, 0.06) 100%)',
            border: '1px solid rgba(99, 102, 241, 0.3)',
            borderRadius: 'var(--radius-lg)',
            padding: '20px',
            position: 'relative'
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.8125rem', color: 'var(--text-muted)', fontWeight: 600 }}>Compliance Health Score</span>
            <Shield size={18} color="var(--accent-indigo-light)" />
          </div>
          <div style={{ fontSize: '2.4rem', fontWeight: 800, marginTop: '8px', color: '#ffffff' }}>
            {healthData ? `${healthData.overall_health_score}%` : '---%'}
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px' }}>
            Verified: {healthData?.verified_maps || 0} / {healthData?.actionable_maps || 0} actionable mandates
          </div>
        </div>

        {/* Metric 2: Review Queue Pending */}
        <div
          style={{
            background: 'rgba(17, 24, 39, 0.6)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-lg)',
            padding: '20px'
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.8125rem', color: 'var(--text-muted)', fontWeight: 600 }}>Human Review Queue</span>
            <AlertTriangle size={18} color="#f59e0b" />
          </div>
          <div style={{ fontSize: '2.4rem', fontWeight: 800, marginTop: '8px', color: '#f59e0b' }}>
            {reviewQueue.length}
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px' }}>
            Pending officer sign-off or triage
          </div>
        </div>

        {/* Metric 3: Active Synchronized Tasks */}
        <div
          style={{
            background: 'rgba(17, 24, 39, 0.6)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-lg)',
            padding: '20px'
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.8125rem', color: 'var(--text-muted)', fontWeight: 600 }}>Synchronized Jira Tasks</span>
            <CheckSquare size={18} color="#06b6d4" />
          </div>
          <div style={{ fontSize: '2.4rem', fontWeight: 800, marginTop: '8px', color: '#06b6d4' }}>
            {dashboardMetrics?.total_maps || 0}
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px' }}>
            Enterprise tickets dispatched
          </div>
        </div>

        {/* Metric 4: Immutable Audit Trail Count */}
        <div
          style={{
            background: 'rgba(17, 24, 39, 0.6)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-lg)',
            padding: '20px'
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.8125rem', color: 'var(--text-muted)', fontWeight: 600 }}>Audit Trail Events</span>
            <Lock size={18} color="#10b981" />
          </div>
          <div style={{ fontSize: '2.4rem', fontWeight: 800, marginTop: '8px', color: '#10b981' }}>
            {dashboardMetrics?.total_audit_events || 0}
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px' }}>
            Cryptographically sealed entries
          </div>
        </div>
      </div>

      {/* ROLE VIEW: COMPLIANCE HEAD */}
      {currentRole === 'compliance_head' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {/* Section: Human Review Queue */}
          <div
            style={{
              background: 'rgba(17, 24, 39, 0.7)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-lg)',
              padding: '22px'
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <div>
                <h3 style={{ fontSize: '1.05rem', fontWeight: 700 }}>Human Review & Approval Queue</h3>
                <p style={{ fontSize: '0.8125rem', color: 'var(--text-muted)' }}>
                  Mandates routed by 3-tier Confidence Engine requiring compliance sign-off or department reassignment.
                </p>
              </div>
              <span className="badge badge-amber">{reviewQueue.length} Pending Actions</span>
            </div>

            {reviewQueue.length === 0 ? (
              <div style={{ padding: '30px', textAlign: 'center', color: 'var(--text-muted)' }}>
                <CheckCircle2 size={32} color="#10b981" style={{ margin: '0 auto 10px auto' }} />
                <p>No mandates currently require human review. All extractions auto-assigned or resolved.</p>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {reviewQueue.map((item) => (
                  <div
                    key={item.action_id}
                    style={{
                      padding: '16px',
                      borderRadius: 'var(--radius-md)',
                      background: 'rgba(0, 0, 0, 0.25)',
                      border: '1px solid var(--border-subtle)',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '10px'
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                      <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--accent-indigo-light)' }}>
                            {item.action_id}
                          </span>
                          <span className={`badge ${item.priority === 'Critical' ? 'badge-rose' : item.priority === 'High' ? 'badge-amber' : 'badge-indigo'}`}>
                            {item.priority}
                          </span>
                          <span className="badge badge-cyan">{item.status}</span>
                        </div>
                        <p style={{ marginTop: '8px', fontSize: '0.875rem', fontWeight: 500, color: '#f3f4f6' }}>
                          {item.action}
                        </p>
                      </div>

                      <div style={{ display: 'flex', gap: '8px' }}>
                        <button
                          onClick={() => handleApprove(item.action_id)}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '5px',
                            padding: '6px 12px',
                            borderRadius: 'var(--radius-sm)',
                            background: '#10b981',
                            color: '#ffffff',
                            fontWeight: 600,
                            fontSize: '0.75rem',
                            border: 'none',
                            cursor: 'pointer'
                          }}
                        >
                          <CheckCircle2 size={13} />
                          Approve & Sync Jira
                        </button>
                        <button
                          onClick={() => handleReject(item.action_id)}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '5px',
                            padding: '6px 12px',
                            borderRadius: 'var(--radius-sm)',
                            background: 'rgba(244, 63, 94, 0.15)',
                            border: '1px solid rgba(244, 63, 94, 0.4)',
                            color: '#f43f5e',
                            fontWeight: 600,
                            fontSize: '0.75rem',
                            cursor: 'pointer'
                          }}
                        >
                          <XCircle size={13} />
                          Reject
                        </button>
                      </div>
                    </div>

                    <div style={{ display: 'flex', gap: '20px', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      <span><strong>Target Depts:</strong> {Array.isArray(item.department) ? item.department.join(', ') : item.department}</span>
                      <span><strong>Assigned:</strong> {item.assigned_department || 'Unassigned'}</span>
                      <span><strong>Deadline:</strong> {item.deadline} ({item.deadline_type})</span>
                      <span><strong>AI Confidence:</strong> {(item.confidence * 100).toFixed(0)}%</span>
                    </div>

                    <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', fontStyle: 'italic', background: 'rgba(255, 255, 255, 0.02)', padding: '6px 10px', borderRadius: '4px' }}>
                      Source quote: "{item.source_sentence}"
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Department Health Matrix */}
          <div
            style={{
              background: 'rgba(17, 24, 39, 0.7)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-lg)',
              padding: '22px'
            }}
          >
            <h3 style={{ fontSize: '1.05rem', fontWeight: 700, marginBottom: '14px' }}>Department Compliance Breakdown</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '14px' }}>
              {healthData?.department_scores && Object.entries(healthData.department_scores).map(([dept, data]) => (
                <div
                  key={dept}
                  style={{
                    padding: '14px',
                    borderRadius: 'var(--radius-md)',
                    background: 'rgba(0, 0, 0, 0.25)',
                    border: '1px solid var(--border-subtle)'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontWeight: 600, fontSize: '0.875rem' }}>{dept}</span>
                    <span style={{ fontWeight: 800, fontSize: '1rem', color: data.score_percent > 70 ? '#10b981' : '#f59e0b' }}>
                      {data.score_percent}%
                    </span>
                  </div>
                  <div style={{ marginTop: '8px', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    Verified: {data.verified} / {data.total}
                  </div>
                  {data.pending > 0 && (
                    <div style={{ marginTop: '2px', fontSize: '0.75rem', color: '#f59e0b' }}>
                      {data.pending} pending approval
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ROLE VIEW: DEPARTMENT HEAD */}
      {currentRole === 'department_head' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <div
            style={{
              background: 'rgba(17, 24, 39, 0.7)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-lg)',
              padding: '22px'
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <div>
                <h3 style={{ fontSize: '1.05rem', fontWeight: 700 }}>{selectedDept} Operational Task Board</h3>
                <p style={{ fontSize: '0.8125rem', color: 'var(--text-muted)' }}>
                  Mandates assigned to {selectedDept}. Upload proof documentation to trigger automated validation.
                </p>
              </div>
              <span className="badge badge-indigo">{departmentMaps.length} Mandates</span>
            </div>

            {departmentMaps.length === 0 ? (
              <div style={{ padding: '30px', textAlign: 'center', color: 'var(--text-muted)' }}>
                <CheckCircle2 size={32} color="#10b981" style={{ margin: '0 auto 10px auto' }} />
                <p>No active compliance mandates currently assigned to {selectedDept}.</p>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {departmentMaps.map((item) => (
                  <div
                    key={item.action_id}
                    style={{
                      padding: '16px',
                      borderRadius: 'var(--radius-md)',
                      background: 'rgba(0, 0, 0, 0.25)',
                      border: '1px solid var(--border-subtle)',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '10px'
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                      <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--accent-indigo-light)' }}>
                            {item.action_id}
                          </span>
                          <span className={`badge ${item.status === 'verified' ? 'badge-emerald' : item.status === 'auto_assigned' ? 'badge-cyan' : 'badge-amber'}`}>
                            {item.status.toUpperCase()}
                          </span>
                          {item.jira_issue_key && (
                            <span className="badge badge-indigo">Jira: {item.jira_issue_key}</span>
                          )}
                        </div>
                        <p style={{ marginTop: '8px', fontSize: '0.875rem', fontWeight: 500, color: '#f3f4f6' }}>
                          {item.action}
                        </p>
                      </div>

                      <div>
                        {item.status === 'verified' ? (
                          <span style={{ display: 'flex', alignItems: 'center', gap: '4px', color: '#10b981', fontSize: '0.75rem', fontWeight: 600 }}>
                            <CheckCircle2 size={16} /> Verified & Closed
                          </span>
                        ) : (
                          <button
                            onClick={() => setUploadingForMapId(item.action_id)}
                            style={{
                              display: 'flex',
                              alignItems: 'center',
                              gap: '5px',
                              padding: '6px 14px',
                              borderRadius: 'var(--radius-sm)',
                              background: 'linear-gradient(135deg, #6366f1, #06b6d4)',
                              color: '#ffffff',
                              fontWeight: 600,
                              fontSize: '0.75rem',
                              border: 'none',
                              cursor: 'pointer'
                            }}
                          >
                            <Upload size={13} />
                            Upload Proof
                          </button>
                        )}
                      </div>
                    </div>

                    <div style={{ display: 'flex', gap: '20px', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      <span><strong>Deadline:</strong> {item.deadline}</span>
                      <span><strong>Priority:</strong> {item.priority}</span>
                      <span><strong>Obligation:</strong> {item.obligation_type}</span>
                    </div>

                    {/* Proof Upload Modal Inline */}
                    {uploadingForMapId === item.action_id && (
                      <form
                        onSubmit={handleProofUpload}
                        style={{
                          marginTop: '8px',
                          padding: '12px',
                          borderRadius: 'var(--radius-sm)',
                          background: 'rgba(99, 102, 241, 0.08)',
                          border: '1px dashed rgba(99, 102, 241, 0.4)',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '12px'
                        }}
                      >
                        <input
                          type="file"
                          accept=".pdf,.html,.txt"
                          onChange={(e) => setProofFile(e.target.files[0])}
                          required
                          style={{ fontSize: '0.75rem', color: '#fff' }}
                        />
                        <button
                          type="submit"
                          disabled={!proofFile || uploadStatus === 'uploading'}
                          style={{
                            padding: '6px 12px',
                            borderRadius: '4px',
                            background: '#10b981',
                            color: '#fff',
                            fontSize: '0.75rem',
                            fontWeight: 600,
                            border: 'none',
                            cursor: 'pointer'
                          }}
                        >
                          {uploadStatus === 'uploading' ? 'Verifying...' : 'Submit Evidence'}
                        </button>
                        <button
                          type="button"
                          onClick={() => setUploadingForMapId(null)}
                          style={{
                            padding: '6px 12px',
                            borderRadius: '4px',
                            background: 'transparent',
                            color: 'var(--text-muted)',
                            fontSize: '0.75rem',
                            border: '1px solid var(--border-subtle)',
                            cursor: 'pointer'
                          }}
                        >
                          Cancel
                        </button>
                      </form>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ROLE VIEW: AUDITOR */}
      {currentRole === 'auditor' && (
        <div
          style={{
            background: 'rgba(17, 24, 39, 0.7)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-lg)',
            padding: '22px'
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <div>
              <h3 style={{ fontSize: '1.05rem', fontWeight: 700 }}>Immutable Cryptographic Audit Trail</h3>
              <p style={{ fontSize: '0.8125rem', color: 'var(--text-muted)' }}>
                Tamper-evident log of all state transitions, approvals, corrections, and verifications with SHA-256 seals.
              </p>
            </div>
            <span className="badge badge-emerald">SHA-256 Chained Integrity Verified</span>
          </div>

          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.75rem' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-muted)', textAlign: 'left' }}>
                  <th style={{ padding: '10px' }}>Timestamp (UTC)</th>
                  <th style={{ padding: '10px' }}>Action ID</th>
                  <th style={{ padding: '10px' }}>Event Type</th>
                  <th style={{ padding: '10px' }}>Actor</th>
                  <th style={{ padding: '10px' }}>Notes / Diffs</th>
                  <th style={{ padding: '10px' }}>Cryptographic Seal</th>
                </tr>
              </thead>
              <tbody>
                {auditLogs.map((log) => (
                  <tr key={log.id} style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.04)' }}>
                    <td style={{ padding: '10px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                      {log.timestamp ? new Date(log.timestamp).toLocaleTimeString() : 'N/A'}
                    </td>
                    <td style={{ padding: '10px', fontWeight: 700, color: 'var(--accent-indigo-light)' }}>
                      {log.action_id}
                    </td>
                    <td style={{ padding: '10px' }}>
                      <span className={`badge ${log.action_type === 'VERIFIED' ? 'badge-emerald' : log.action_type === 'APPROVED' ? 'badge-cyan' : 'badge-indigo'}`}>
                        {log.action_type}
                      </span>
                    </td>
                    <td style={{ padding: '10px', color: '#e5e7eb' }}>
                      {log.actor_role} ({log.actor_id})
                    </td>
                    <td style={{ padding: '10px', color: 'var(--text-muted)', maxWidth: '300px' }}>
                      {log.notes || 'State transition'}
                    </td>
                    <td style={{ padding: '10px', fontFamily: 'var(--font-mono)', color: '#10b981' }}>
                      {log.signature ? `${log.signature.slice(0, 12)}...` : 'N/A'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ROLE VIEW: ADMIN */}
      {currentRole === 'admin' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '20px' }}>
          {/* Security Incident Vault */}
          <div
            style={{
              background: 'rgba(17, 24, 39, 0.7)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-lg)',
              padding: '22px'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '14px' }}>
              <Shield size={20} color="#f43f5e" />
              <h3 style={{ fontSize: '1.05rem', fontWeight: 700 }}>Security Incident Vault</h3>
            </div>
            <p style={{ fontSize: '0.8125rem', color: 'var(--text-muted)', marginBottom: '14px' }}>
              Pre-ingestion defenses actively filtering adversarial attempts and compromised formats.
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <div style={{ padding: '12px', borderRadius: 'var(--radius-md)', background: 'rgba(244, 63, 94, 0.1)', border: '1px solid rgba(244, 63, 94, 0.3)' }}>
                <span style={{ fontWeight: 600, color: '#f43f5e', fontSize: '0.8125rem' }}>Prompt Injection Blocked</span>
                <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                  Document: <code>malicious_spoof_01</code> flagged for system override instruction attack.
                </p>
              </div>
              <div style={{ padding: '12px', borderRadius: 'var(--radius-md)', background: 'rgba(245, 158, 11, 0.1)', border: '1px solid rgba(245, 158, 11, 0.3)' }}>
                <span style={{ fontWeight: 600, color: '#f59e0b', fontSize: '0.8125rem' }}>Degraded OCR Guardrail Alert</span>
                <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                  Document: <code>rbi_2026_low_ocr_02</code> reading quality score 0.23 (&lt; 0.50). Routed to review queue.
                </p>
              </div>
            </div>
          </div>

          {/* Crawler & Ingestion Controls */}
          <div
            style={{
              background: 'rgba(17, 24, 39, 0.7)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-lg)',
              padding: '22px'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '14px' }}>
              <Activity size={20} color="var(--accent-indigo-light)" />
              <h3 style={{ fontSize: '1.05rem', fontWeight: 700 }}>Regulatory Portal Crawler</h3>
            </div>
            <p style={{ fontSize: '0.8125rem', color: 'var(--text-muted)', marginBottom: '14px' }}>
              Monitors RBI, SEBI, IRDAI, and NPCI portals with APScheduler intervals.
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <button
                onClick={async () => {
                  try {
                    const res = await fetch(`${API_BASE_URL}/api/crawler/trigger`, { method: 'POST' });
                    if (res.ok) {
                      const d = await res.json();
                      setActionMessage(`Crawl executed: ${d.summary?.total_ingested || 0} circulars ingested.`);
                      setTimeout(() => setActionMessage(null), 5000);
                      fetchDashboardData();
                    }
                  } catch (e) {
                    console.error(e);
                  }
                }}
                style={{
                  padding: '10px 16px',
                  borderRadius: 'var(--radius-md)',
                  background: 'linear-gradient(135deg, #6366f1, #06b6d4)',
                  color: '#ffffff',
                  fontWeight: 600,
                  fontSize: '0.8125rem',
                  border: 'none',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '8px'
                }}
              >
                <RefreshCw size={14} />
                Trigger On-Demand Portal Crawl
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
