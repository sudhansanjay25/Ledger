import os
import sys
import io
import pytest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
AGENT_DIR = os.path.join(BASE_DIR, "agent")
for p in (BASE_DIR, BACKEND_DIR, AGENT_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from app import app
from database import SessionLocal, MAPRecordModel
from jira_integration import JIRA


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture(autouse=True)
def setup_metrics_test_map():
    db = SessionLocal()
    db.query(MAPRecordModel).filter(MAPRecordModel.action_id == "MAP-PROOF-01").delete()
    
    m = MAPRecordModel(
        action_id="MAP-PROOF-01",
        circular_id="circ_proof",
        action="Deploy real-time fraud monitoring transaction surveillance.",
        department=["IT", "Operations"],
        deadline="2026-11-30",
        deadline_type="explicit",
        priority="High",
        obligation_type="REQUIRED",
        source_sentence="Establish real-time fraud monitoring system.",
        status="auto_assigned",
        assigned_department="IT",
        jira_issue_key="COMP-3001"
    )
    db.add(m)
    db.commit()
    db.close()

    JIRA._issues["COMP-3001"] = {
        "key": "COMP-3001",
        "action_id": "MAP-PROOF-01",
        "summary": "Deploy fraud monitoring",
        "status": "Done",
        "department": "IT",
        "priority": "High"
    }


def test_upload_proof_endpoint(client):
    proof_content = (
        b"Enterprise IT Architecture Report: Certified deployment of real-time fraud monitoring "
        b"and transaction surveillance system successfully tested and verified in production."
    )
    data = {
        "file": (io.BytesIO(proof_content), "fraud_monitoring_proof.txt")
    }

    res = client.post(
        "/api/maps/MAP-PROOF-01/proof",
        data=data,
        content_type="multipart/form-data",
        headers={"X-User-Role": "department_head", "X-User-Department": "IT"}
    )
    assert res.status_code == 200
    res_data = res.get_json()
    assert "verification" in res_data
    assert res_data["verification"]["verification_status"] == "verified"
    assert res_data["verification"]["jira_ok"] is True


def test_compliance_health_endpoint(client):
    res = client.get("/api/metrics/health")
    assert res.status_code == 200
    data = res.get_json()
    assert "overall_health_score" in data
    assert "department_scores" in data
    assert "total_maps" in data
    assert data["total_maps"] >= 1


def test_dashboard_metrics_endpoint(client):
    res = client.get("/api/metrics/dashboard")
    assert res.status_code == 200
    data = res.get_json()
    assert "total_maps" in data
    assert "security_vault" in data
    assert data["security_vault"]["threats_blocked"] >= 1


def test_notifications_endpoints(client):
    # Check trigger
    check_res = client.post("/api/notifications/check", json={"reference_date": "2026-07-15"})
    assert check_res.status_code == 200

    # List notifications
    list_res = client.get("/api/notifications")
    assert list_res.status_code == 200
    data = list_res.get_json()
    assert "notifications" in data
