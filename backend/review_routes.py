import os
import sys
from typing import Dict, Any, List
from flask import Blueprint, request, jsonify

# Add agent directory to sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENT_DIR = os.path.join(BASE_DIR, "agent")
for p in (BASE_DIR, AGENT_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from database import SessionLocal, MAPRecordModel, AuditLogModel
from rbac import (
    UserRole, Permission, require_permission, get_current_user_context, can_access_map
)
from audit_trail import AUDIT_TRAIL
from jira_integration import JIRA
from feedback_memory import FEEDBACK_STORE

review_bp = Blueprint("review_bp", __name__)


@review_bp.route("/api/review-queue", methods=["GET"])
def get_review_queue():
    """
    Returns MAPs requiring human compliance attention (status in_review_queue or pending_approval).
    Supports filtering by status, department, and priority.
    """
    user = get_current_user_context()
    status_filter = request.args.get("status")
    dept_filter = request.args.get("department")
    priority_filter = request.args.get("priority")

    db = SessionLocal()
    try:
        query = db.query(MAPRecordModel).filter(
            MAPRecordModel.status.in_(["in_review_queue", "pending_approval"])
        )
        if status_filter:
            query = query.filter(MAPRecordModel.status == status_filter)
        if priority_filter:
            query = query.filter(MAPRecordModel.priority == priority_filter)

        items = query.order_by(MAPRecordModel.created_at.desc()).all()
        result = []
        for it in items:
            it_dict = it.to_dict()
            if can_access_map(user["role"], user["department"], it_dict):
                if not dept_filter or it_dict.get("assigned_department") == dept_filter or dept_filter in it_dict.get("department", []):
                    result.append(it_dict)

        return jsonify({
            "count": len(result),
            "user_role": user["role"],
            "queue": result
        }), 200
    finally:
        db.close()


@review_bp.route("/api/review-queue/<action_id>/approve", methods=["POST"])
@require_permission(Permission.APPROVE_MAP)
def approve_map(action_id: str):
    """
    Approves a MAP, optionally updating department or deadline.
    Dispatches a Jira issue and logs to the immutable audit trail.
    If departments were corrected, registers exemplar with FeedbackMemory.
    """
    user = get_current_user_context()
    data = request.get_json(silent=True) or {}
    override_dept = data.get("assigned_department")
    override_deadline = data.get("deadline")
    notes = data.get("notes", "Approved by compliance officer")

    db = SessionLocal()
    try:
        map_record = db.query(MAPRecordModel).filter(MAPRecordModel.action_id == action_id).first()
        if not map_record:
            return jsonify({"error": f"MAP with action_id '{action_id}' not found."}), 404

        prev_state = map_record.to_dict()

        # Check if human officer corrected department
        old_depts = prev_state.get("department", [])
        if override_dept and override_dept not in old_depts:
            FEEDBACK_STORE.record_correction(
                topic=f"correction_{action_id}",
                keywords=map_record.action.split()[:8],
                corrected_departments=[override_dept],
                corrected_priority=map_record.priority,
                notes=f"Officer override during approval of {action_id}"
            )

        # Update record
        map_record.status = "approved"
        if override_dept:
            map_record.assigned_department = override_dept
        if override_deadline:
            map_record.deadline = override_deadline

        # Create Jira task
        jira_issue = JIRA.create_issue(
            action_id=action_id,
            summary=map_record.action,
            description=f"Regulatory Obligation from Circular {map_record.circular_id}.\nSource: {map_record.source_sentence}",
            department=map_record.assigned_department or "Operations",
            priority=map_record.priority,
            due_date=map_record.deadline
        )
        map_record.jira_issue_key = jira_issue["key"]

        db.commit()
        db.refresh(map_record)

        new_state = map_record.to_dict()

        # Audit log event
        AUDIT_TRAIL.record_event(
            action_id=action_id,
            action_type="APPROVED",
            actor_role=user["role"],
            actor_id=user["user_id"],
            previous_state=prev_state,
            new_state=new_state,
            notes=f"{notes}. Created Jira {jira_issue['key']}"
        )

        return jsonify({
            "message": f"MAP '{action_id}' successfully approved.",
            "status": "approved",
            "jira_issue": jira_issue,
            "map": new_state
        }), 200
    finally:
        db.close()


@review_bp.route("/api/review-queue/<action_id>/reject", methods=["POST"])
@require_permission(Permission.REJECT_MAP)
def reject_map(action_id: str):
    """Rejects a MAP, documenting the rationale in the immutable audit trail."""
    user = get_current_user_context()
    data = request.get_json(silent=True) or {}
    reason = data.get("reason", "Rejected as non-actionable or invalid by compliance officer")

    db = SessionLocal()
    try:
        map_record = db.query(MAPRecordModel).filter(MAPRecordModel.action_id == action_id).first()
        if not map_record:
            return jsonify({"error": f"MAP with action_id '{action_id}' not found."}), 404

        prev_state = map_record.to_dict()
        map_record.status = "rejected"
        db.commit()
        db.refresh(map_record)

        new_state = map_record.to_dict()

        AUDIT_TRAIL.record_event(
            action_id=action_id,
            action_type="REJECTED",
            actor_role=user["role"],
            actor_id=user["user_id"],
            previous_state=prev_state,
            new_state=new_state,
            notes=reason
        )

        return jsonify({
            "message": f"MAP '{action_id}' marked as rejected.",
            "status": "rejected",
            "map": new_state
        }), 200
    finally:
        db.close()


@review_bp.route("/api/review-queue/<action_id>/edit", methods=["PUT"])
@require_permission(Permission.EDIT_MAP)
def edit_map(action_id: str):
    """Edits action text, target departments, deadline, or priority."""
    user = get_current_user_context()
    data = request.get_json(silent=True) or {}

    db = SessionLocal()
    try:
        map_record = db.query(MAPRecordModel).filter(MAPRecordModel.action_id == action_id).first()
        if not map_record:
            return jsonify({"error": f"MAP with action_id '{action_id}' not found."}), 404

        prev_state = map_record.to_dict()

        if "action" in data:
            map_record.action = data["action"]
        if "department" in data:
            map_record.department = data["department"]
        if "assigned_department" in data:
            map_record.assigned_department = data["assigned_department"]
        if "deadline" in data:
            map_record.deadline = data["deadline"]
            map_record.deadline_type = "explicit"
        if "priority" in data:
            map_record.priority = data["priority"]

        db.commit()
        db.refresh(map_record)
        new_state = map_record.to_dict()

        AUDIT_TRAIL.record_event(
            action_id=action_id,
            action_type="EDITED",
            actor_role=user["role"],
            actor_id=user["user_id"],
            previous_state=prev_state,
            new_state=new_state,
            notes="Compliance officer edited MAP attributes."
        )

        return jsonify({
            "message": f"MAP '{action_id}' successfully updated.",
            "map": new_state
        }), 200
    finally:
        db.close()


@review_bp.route("/api/maps", methods=["GET"])
def list_maps():
    """Lists all stored MAPs with filtering, adhering to multi-tenant department access."""
    user = get_current_user_context()
    status_filter = request.args.get("status")
    circular_filter = request.args.get("circular_id")
    dept_filter = request.args.get("department")

    db = SessionLocal()
    try:
        query = db.query(MAPRecordModel)
        if status_filter:
            query = query.filter(MAPRecordModel.status == status_filter)
        if circular_filter:
            query = query.filter(MAPRecordModel.circular_id == circular_filter)

        items = query.order_by(MAPRecordModel.created_at.desc()).all()
        filtered = []
        for it in items:
            d = it.to_dict()
            if can_access_map(user["role"], user["department"], d):
                if not dept_filter or d.get("assigned_department") == dept_filter or dept_filter in d.get("department", []):
                    filtered.append(d)

        return jsonify({
            "count": len(filtered),
            "user_role": user["role"],
            "maps": filtered
        }), 200
    finally:
        db.close()


@review_bp.route("/api/audit-logs", methods=["GET"])
@require_permission(Permission.VIEW_AUDIT_LOGS)
def get_audit_logs():
    """Returns paginated, immutable audit trail records."""
    action_type = request.args.get("action_type")
    actor_role = request.args.get("actor_role")
    action_id = request.args.get("action_id")
    limit = int(request.args.get("limit", 50))
    offset = int(request.args.get("offset", 0))

    if action_id:
        logs = AUDIT_TRAIL.get_history(action_id)
    else:
        logs = AUDIT_TRAIL.get_all_logs(limit=limit, offset=offset, action_type=action_type, actor_role=actor_role)

    # Check integrity of each log entry
    for l in logs:
        l["integrity_verified"] = AUDIT_TRAIL.verify_entry_integrity(l)

    return jsonify({
        "count": len(logs),
        "limit": limit,
        "offset": offset,
        "logs": logs
    }), 200


@review_bp.route("/api/jira/issues", methods=["GET"])
def get_jira_issues():
    """Lists synchronized Jira tasks."""
    dept = request.args.get("department")
    status = request.args.get("status")
    issues = JIRA.list_issues(department=dept, status=status)
    return jsonify({
        "count": len(issues),
        "issues": issues
    }), 200
