import os
import sys
import pytest
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENT_DIR = os.path.join(BASE_DIR, "agent")
for p in (BASE_DIR, AGENT_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base, UserModel, MAPRecordModel, AuditLogModel, init_db, compute_audit_hash


@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    init_db(target_engine=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_seed_users(test_db):
    users = test_db.query(UserModel).all()
    assert len(users) >= 4
    roles = {u.role for u in users}
    assert "admin" in roles
    assert "compliance_head" in roles
    assert "department_head" in roles
    assert "auditor" in roles


def test_map_record_lifecycle(test_db):
    rec = MAPRecordModel(
        action_id="MAP-TEST-01",
        circular_id="circ_test",
        action="Implement TLS 1.3 encryption across all communication endpoints.",
        department=["IT", "InfoSec"],
        deadline="2026-12-31",
        deadline_type="explicit",
        priority="Critical",
        obligation_type="REQUIRED",
        source_sentence="All endpoints must enforce TLS 1.3 by December 31, 2026.",
        confidence=0.92,
        status="auto_assigned",
        assigned_department="IT"
    )
    test_db.add(rec)
    test_db.commit()

    queried = test_db.query(MAPRecordModel).filter_by(action_id="MAP-TEST-01").first()
    assert queried is not None
    d = queried.to_dict()
    assert d["action_id"] == "MAP-TEST-01"
    assert d["assigned_department"] == "IT"
    assert "InfoSec" in d["department"]
    assert d["confidence"] == 0.92


def test_audit_hash_integrity():
    h1 = compute_audit_hash("MAP-01", "CREATED", "agent_1", "2026-07-15T10:00:00", '{"status": "new"}')
    h2 = compute_audit_hash("MAP-01", "CREATED", "agent_1", "2026-07-15T10:00:00", '{"status": "new"}')
    h_tampered = compute_audit_hash("MAP-01", "CREATED", "agent_1", "2026-07-15T10:00:00", '{"status": "tampered"}')
    
    assert h1 == h2
    assert h1 != h_tampered
