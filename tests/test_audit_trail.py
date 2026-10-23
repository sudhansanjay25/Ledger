import os
import sys
import pytest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENT_DIR = os.path.join(BASE_DIR, "agent")
for p in (BASE_DIR, AGENT_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import init_db
from audit_trail import AuditTrail


@pytest.fixture
def audit_session():
    engine = create_engine("sqlite:///:memory:")
    init_db(target_engine=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_audit_event_recording_and_history(audit_session):
    # Record CREATED event
    e1 = AuditTrail.record_event(
        action_id="MAP-AUDIT-01",
        action_type="CREATED",
        actor_role="system_agent",
        actor_id="langgraph_planner",
        previous_state=None,
        new_state={"status": "in_review_queue", "department": "IT"},
        notes="Generated from circular",
        session=audit_session
    )
    assert e1["action_id"] == "MAP-AUDIT-01"
    assert e1["action_type"] == "CREATED"
    assert e1["signature"] is not None

    # Record APPROVED event
    e2 = AuditTrail.record_event(
        action_id="MAP-AUDIT-01",
        action_type="APPROVED",
        actor_role="compliance_head",
        actor_id="compliance_officer_1",
        previous_state={"status": "in_review_queue"},
        new_state={"status": "approved", "jira_key": "COMP-101"},
        notes="Sign-off granted",
        session=audit_session
    )

    history = AuditTrail.get_history("MAP-AUDIT-01", session=audit_session)
    assert len(history) == 2
    assert history[0]["action_type"] == "CREATED"
    assert history[1]["action_type"] == "APPROVED"


def test_audit_integrity_verification(audit_session):
    event = AuditTrail.record_event(
        action_id="MAP-SEAL-01",
        action_type="STATUS_CHANGE",
        actor_role="compliance_head",
        actor_id="officer_2",
        previous_state={"status": "pending_approval"},
        new_state={"status": "approved"},
        session=audit_session
    )

    # Valid check
    assert AuditTrail.verify_entry_integrity(event) is True

    # Tampered state check
    tampered_event = dict(event)
    tampered_event["new_state"] = {"status": "rejected_illegitimately"}
    assert AuditTrail.verify_entry_integrity(tampered_event) is False
