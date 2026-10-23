import os
import sys
import json
import pytest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
AGENT_DIR = os.path.join(BASE_DIR, "agent")
for p in (BASE_DIR, BACKEND_DIR, AGENT_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from app import app
from database import SessionLocal, MAPRecordModel


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture(autouse=True)
def setup_test_map():
    db = SessionLocal()
    # Clean up any existing test map
    db.query(MAPRecordModel).filter(MAPRecordModel.action_id.in_(["MAP-API-01", "MAP-API-02"])).delete()
    
    m1 = MAPRecordModel(
        action_id="MAP-API-01",
        circular_id="circ_test_api",
        action="Deploy hardware security module (HSM) across data centers.",
        department=["IT", "InfoSec"],
        deadline="2026-10-15",
        deadline_type="explicit",
        priority="High",
        obligation_type="REQUIRED",
        source_sentence="Banks must deploy hardware security modules.",
        confidence=0.82,
        status="pending_approval",
        assigned_department="IT"
    )
    db.add(m1)
    db.commit()
    db.close()


def test_get_review_queue(client):
    res = client.get("/api/review-queue", headers={"X-User-Role": "compliance_head"})
    assert res.status_code == 200
    data = res.get_json()
    assert data["count"] >= 1
    ids = [item["action_id"] for item in data["queue"]]
    assert "MAP-API-01" in ids


def test_approve_map_success_and_jira_dispatch(client):
    res = client.post(
        "/api/review-queue/MAP-API-01/approve",
        headers={"X-User-Role": "compliance_head", "X-User-Id": "compliance_officer_test"},
        json={
            "assigned_department": "Treasury",
            "notes": "Re-assigned to Treasury after risk review"
        }
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "approved"
    assert "jira_issue" in data
    assert data["jira_issue"]["key"].startswith("COMP-")
    assert data["map"]["assigned_department"] == "Treasury"


def test_reject_map_success(client):
    res = client.post(
        "/api/review-queue/MAP-API-01/reject",
        headers={"X-User-Role": "compliance_head", "X-User-Id": "compliance_officer_test"},
        json={"reason": "Redundant obligation already covered under master policy"}
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "rejected"
    assert data["map"]["status"] == "rejected"


def test_edit_map_success(client):
    res = client.put(
        "/api/review-queue/MAP-API-01/edit",
        headers={"X-User-Role": "compliance_head", "X-User-Id": "compliance_officer_test"},
        json={
            "action": "Updated action: deploy HSM modules with FIPS 140-3 certification.",
            "priority": "Critical"
        }
    )
    assert res.status_code == 200
    data = res.get_json()
    assert "FIPS 140-3" in data["map"]["action"]
    assert data["map"]["priority"] == "Critical"


def test_rbac_forbidden_for_auditor_approval(client):
    # Auditor role is read-only and must be forbidden from approving
    res = client.post(
        "/api/review-queue/MAP-API-01/approve",
        headers={"X-User-Role": "auditor", "X-User-Id": "auditor_guest"},
        json={}
    )
    assert res.status_code == 403
    data = res.get_json()
    assert "Forbidden" in data["error"]


def test_audit_logs_endpoint(client):
    res = client.get(
        "/api/audit-logs",
        headers={"X-User-Role": "auditor"}
    )
    assert res.status_code == 200
    data = res.get_json()
    assert "logs" in data
    assert data["count"] >= 1
    # Check integrity verification flag
    assert data["logs"][0]["integrity_verified"] is True


def test_jira_issues_endpoint(client):
    res = client.get("/api/jira/issues")
    assert res.status_code == 200
    data = res.get_json()
    assert "issues" in data
