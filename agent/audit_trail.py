import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from database import SessionLocal, AuditLogModel, compute_audit_hash


class AuditTrail:
    """
    Immutable, tamper-evident audit logging service for compliance state mutations.
    Every event generates a cryptographic SHA-256 seal.
    """

    @classmethod
    def record_event(
        cls,
        action_id: str,
        action_type: str,
        actor_role: str,
        actor_id: str,
        previous_state: Optional[Dict[str, Any]] = None,
        new_state: Optional[Dict[str, Any]] = None,
        notes: str = "",
        session=None
    ) -> Dict[str, Any]:
        """
        Records an immutable audit event in the database.
        """
        owns_session = session is None
        db = session or SessionLocal()
        try:
            now_dt = datetime.utcnow()
            now_iso = now_dt.isoformat()
            
            new_state_clean = new_state or {}
            prev_state_clean = previous_state or {}
            new_state_json = json.dumps(new_state_clean, sort_keys=True)

            signature = compute_audit_hash(
                action_id=action_id,
                action_type=action_type,
                actor_id=actor_id,
                timestamp_str=now_iso,
                new_state_json=new_state_json
            )

            log_entry = AuditLogModel(
                action_id=action_id,
                action_type=action_type,
                actor_role=actor_role,
                actor_id=actor_id,
                previous_state=prev_state_clean,
                new_state=new_state_clean,
                notes=notes,
                signature=signature,
                timestamp=now_dt
            )
            db.add(log_entry)
            if owns_session:
                db.commit()
                db.refresh(log_entry)
            else:
                db.flush()

            return log_entry.to_dict()
        finally:
            if owns_session:
                db.close()

    @classmethod
    def get_history(cls, action_id: str, session=None) -> List[Dict[str, Any]]:
        """Retrieves chronological state changes for a specific action ID."""
        owns_session = session is None
        db = session or SessionLocal()
        try:
            logs = (
                db.query(AuditLogModel)
                .filter(AuditLogModel.action_id == action_id)
                .order_by(AuditLogModel.timestamp.asc())
                .all()
            )
            return [l.to_dict() for l in logs]
        finally:
            if owns_session:
                db.close()

    @classmethod
    def get_all_logs(
        cls,
        limit: int = 100,
        offset: int = 0,
        action_type: Optional[str] = None,
        actor_role: Optional[str] = None,
        session=None
    ) -> List[Dict[str, Any]]:
        """Queries audit log records with pagination and filters."""
        owns_session = session is None
        db = session or SessionLocal()
        try:
            query = db.query(AuditLogModel)
            if action_type:
                query = query.filter(AuditLogModel.action_type == action_type)
            if actor_role:
                query = query.filter(AuditLogModel.actor_role == actor_role)
            
            records = (
                query.order_by(AuditLogModel.timestamp.desc())
                .offset(offset)
                .limit(limit)
                .all()
            )
            return [r.to_dict() for r in records]
        finally:
            if owns_session:
                db.close()

    @classmethod
    def verify_entry_integrity(cls, log_dict: Dict[str, Any]) -> bool:
        """Verifies the SHA-256 signature of an audit log entry."""
        if not log_dict or "signature" not in log_dict:
            return False

        action_id = log_dict.get("action_id", "")
        action_type = log_dict.get("action_type", "")
        actor_id = log_dict.get("actor_id", "")
        timestamp = log_dict.get("timestamp", "")
        new_state = log_dict.get("new_state") or {}
        new_state_json = json.dumps(new_state, sort_keys=True)

        expected_sig = compute_audit_hash(action_id, action_type, actor_id, timestamp, new_state_json)
        return expected_sig == log_dict.get("signature")


# Global audit trail instance
AUDIT_TRAIL = AuditTrail()
