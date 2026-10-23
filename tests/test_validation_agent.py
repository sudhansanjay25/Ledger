import os
import sys
import pytest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENT_DIR = os.path.join(BASE_DIR, "agent")
for p in (BASE_DIR, AGENT_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from database import SessionLocal, MAPRecordModel, ProofRecordModel
from jira_integration import JIRA
from validation_agent import verify_compliance_proof, VALIDATION_AGENT


@pytest.fixture(autouse=True)
def setup_validation_test_data():
    db = SessionLocal()
    # Clean previous records
    db.query(ProofRecordModel).filter(ProofRecordModel.action_id == "MAP-VAL-01").delete()
    db.query(MAPRecordModel).filter(MAPRecordModel.action_id == "MAP-VAL-01").delete()

    rec = MAPRecordModel(
        action_id="MAP-VAL-01",
        circular_id="circ_val_01",
        action="Implement robust Multi-Factor Authentication (MFA) for digital transactions.",
        department=["IT", "InfoSec"],
        deadline="2026-12-31",
        deadline_type="explicit",
        priority="Critical",
        obligation_type="REQUIRED",
        source_sentence="All banks must implement robust Multi-Factor Authentication by December 31, 2026.",
        confidence=0.95,
        status="auto_assigned",
        assigned_department="IT",
        jira_issue_key="COMP-2001"
    )
    db.add(rec)
    db.commit()
    db.close()

    # Create matching Jira issue in Done status
    JIRA._issues["COMP-2001"] = {
        "key": "COMP-2001",
        "action_id": "MAP-VAL-01",
        "summary": "Implement robust MFA",
        "status": "Done",
        "department": "IT",
        "priority": "Highest"
    }


def test_validation_subagent_success_verified():
    proof_text = (
        "Enterprise Architecture & Security Audit Sign-off: "
        "We have completed and certified the deployment of robust Multi-Factor Authentication (MFA) "
        "across all digital transaction channels with independent verification and audit passed."
    )

    result = verify_compliance_proof(
        action_id="MAP-VAL-01",
        proof_text=proof_text,
        filename="mfa_audit_cert.pdf"
    )

    assert result["verification_status"] == "verified"
    assert result["verification_score"] >= 0.65
    assert result["jira_ok"] is True
    assert "successfully verified" in result["feedback"].lower()

    # Verify DB status updated
    db = SessionLocal()
    map_rec = db.query(MAPRecordModel).filter_by(action_id="MAP-VAL-01").first()
    assert map_rec.status == "verified"
    db.close()


def test_validation_subagent_incomplete_when_jira_not_done():
    # Set Jira issue to To Do
    JIRA._issues["COMP-2001"]["status"] = "To Do"

    proof_text = (
        "Enterprise Architecture & Security Audit Sign-off: "
        "We have completed and certified the deployment of robust Multi-Factor Authentication (MFA) "
        "across all digital transaction channels with independent verification and audit passed."
    )

    result = verify_compliance_proof(
        action_id="MAP-VAL-01",
        proof_text=proof_text,
        filename="mfa_report.pdf"
    )

    assert result["verification_status"] == "incomplete"
    assert result["jira_ok"] is False
    assert "jira ticket is not marked done" in result["feedback"].lower()


def test_validation_subagent_incomplete_when_proof_irrelevant():
    # Jira is Done, but proof text is about cafeteria menu
    JIRA._issues["COMP-2001"]["status"] = "Done"

    proof_text = "Weekly cafeteria luncheon schedule including vegetarian options."

    result = verify_compliance_proof(
        action_id="MAP-VAL-01",
        proof_text=proof_text,
        filename="cafeteria.pdf"
    )

    assert result["verification_status"] == "incomplete"
    assert result["verification_score"] < 0.65
    assert "does not sufficiently demonstrate" in result["feedback"].lower()
