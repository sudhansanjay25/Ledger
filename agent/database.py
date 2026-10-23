import os
import json
import hashlib
from datetime import datetime
from typing import Generator, Optional, List, Dict, Any

from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Boolean, Text, DateTime, JSON
)
from sqlalchemy.orm import declarative_base, sessionmaker, Session

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///ledger.db")

# SQLite needs check_same_thread=False for multi-threaded Flask apps
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class UserModel(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False)
    role = Column(String(30), nullable=False, default="department_head")  # admin, compliance_head, department_head, auditor
    department = Column(String(50), nullable=True)  # e.g., "IT", "Operations", "Compliance"
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "role": self.role,
            "department": self.department,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class MAPRecordModel(Base):
    __tablename__ = "map_records"

    id = Column(Integer, primary_key=True, index=True)
    action_id = Column(String(50), unique=True, nullable=False, index=True)
    circular_id = Column(String(50), nullable=False, index=True)
    action = Column(Text, nullable=False)
    department = Column(JSON, nullable=False)  # List of target departments
    deadline = Column(String(30), default="None")
    deadline_type = Column(String(20), default="implicit")  # explicit, derived, implicit
    priority = Column(String(20), default="Medium")  # Critical, High, Medium, Low
    obligation_type = Column(String(20), default="REQUIRED")  # REQUIRED, PROHIBITED, ADVISORY
    source_sentence = Column(Text, nullable=False)
    confidence = Column(Float, default=0.85)
    
    # Phase 4 Workflow State
    status = Column(String(30), default="in_review_queue", index=True)
    # Status values: auto_assigned, pending_approval, in_review_queue, approved, rejected
    
    assigned_department = Column(String(50), nullable=True)
    assigned_to_user_id = Column(Integer, nullable=True)
    is_superseded = Column(Boolean, default=False)
    superseded_by = Column(String(50), nullable=True)
    jira_issue_key = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "action_id": self.action_id,
            "circular_id": self.circular_id,
            "action": self.action,
            "department": self.department if isinstance(self.department, list) else json.loads(self.department or "[]"),
            "deadline": self.deadline,
            "deadline_type": self.deadline_type,
            "priority": self.priority,
            "obligation_type": self.obligation_type,
            "source_sentence": self.source_sentence,
            "confidence": round(self.confidence, 2) if self.confidence else 0.85,
            "status": self.status,
            "assigned_department": self.assigned_department,
            "assigned_to_user_id": self.assigned_to_user_id,
            "is_superseded": self.is_superseded,
            "superseded_by": self.superseded_by,
            "jira_issue_key": self.jira_issue_key,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class AuditLogModel(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    action_id = Column(String(50), nullable=False, index=True)
    action_type = Column(String(30), nullable=False)  # CREATED, STATUS_CHANGE, APPROVED, EDITED, REJECTED, JIRA_SYNCED
    actor_role = Column(String(30), nullable=False)
    actor_id = Column(String(50), nullable=False)
    previous_state = Column(JSON, nullable=True)
    new_state = Column(JSON, nullable=True)
    notes = Column(Text, nullable=True)
    signature = Column(String(64), nullable=False)  # Cryptographic SHA-256 seal
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "action_id": self.action_id,
            "action_type": self.action_type,
            "actor_role": self.actor_role,
            "actor_id": self.actor_id,
            "previous_state": self.previous_state,
            "new_state": self.new_state,
            "notes": self.notes,
            "signature": self.signature,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }


class ProofRecordModel(Base):
    __tablename__ = "proof_records"

    id = Column(Integer, primary_key=True, index=True)
    action_id = Column(String(50), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    file_format = Column(String(30), default="digital_pdf")
    sha256 = Column(String(64), nullable=False)
    extracted_text = Column(Text, nullable=False)
    uploaded_by_role = Column(String(30), default="department_head")
    uploaded_by_id = Column(String(50), default="dept_user")
    verification_status = Column(String(30), default="pending", index=True)  # pending, verified, incomplete, rejected
    verification_score = Column(Float, default=0.0)
    verification_feedback = Column(Text, nullable=True)
    jira_status_verified = Column(Boolean, default=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "action_id": self.action_id,
            "filename": self.filename,
            "file_format": self.file_format,
            "sha256": self.sha256,
            "extracted_text_preview": self.extracted_text[:200] + "..." if len(self.extracted_text) > 200 else self.extracted_text,
            "uploaded_by_role": self.uploaded_by_role,
            "uploaded_by_id": self.uploaded_by_id,
            "verification_status": self.verification_status,
            "verification_score": round(self.verification_score, 2),
            "verification_feedback": self.verification_feedback,
            "jira_status_verified": self.jira_status_verified,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }


def compute_audit_hash(action_id: str, action_type: str, actor_id: str, timestamp_str: str, new_state_json: str) -> str:
    """Computes a tamper-evident SHA-256 seal for the audit record."""
    payload = f"{action_id}:{action_type}:{actor_id}:{timestamp_str}:{new_state_json}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def init_db(target_engine=None):
    """Initializes tables and seeds default baseline users."""
    eng = target_engine or engine
    Base.metadata.create_all(bind=eng)

    # Seed baseline users if empty
    session = sessionmaker(bind=eng)()
    try:
        if session.query(UserModel).count() == 0:
            seed_users = [
                UserModel(username="admin_user", email="admin@ledger.internal", role="admin"),
                UserModel(username="compliance_lead", email="compliance@ledger.internal", role="compliance_head"),
                UserModel(username="it_lead", email="it@ledger.internal", role="department_head", department="IT"),
                UserModel(username="ops_lead", email="ops@ledger.internal", role="department_head", department="Operations"),
                UserModel(username="auditor_lead", email="auditor@ledger.internal", role="auditor"),
            ]
            session.add_all(seed_users)
            session.commit()
    finally:
        session.close()


def get_db_session() -> Generator[Session, None, None]:
    """Dependency helper yielding a DB session."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


# Initialize database automatically on module load
init_db()
