import os
import sys
import re
from typing import Dict, Any, List, Optional
from datetime import datetime

# Add agent directory to sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from typing_extensions import TypedDict
from langgraph.graph import StateGraph, END
from database import SessionLocal, MAPRecordModel, ProofRecordModel
from audit_trail import AUDIT_TRAIL
from jira_integration import JIRA


class ValidationState(TypedDict):
    action_id: str
    map_record: Dict[str, Any]
    proof_text: str
    filename: str
    uploaded_by_role: str
    uploaded_by_id: str
    jira_issue_key: Optional[str]
    jira_status: str
    jira_ok: bool
    semantic_score: float
    verification_status: str  # verified | incomplete
    feedback: str
    logs: List[str]


VERIFICATION_CONFIRMATION_TERMS = [
    "certified", "implemented", "completed", "audit passed", "verified",
    "fips 140", "soc 2", "deployed", "enforced", "signed off", "approved",
    "production release", "tested successfully", "configured"
]


def check_jira_node(state: ValidationState) -> Dict[str, Any]:
    """Inspects linked Jira task status."""
    logs = list(state.get("logs", []))
    action_id = state["action_id"]
    map_record = state.get("map_record", {})
    jira_key = map_record.get("jira_issue_key")

    jira_issue = None
    if jira_key:
        jira_issue = JIRA.get_issue(jira_key)
    if not jira_issue:
        jira_issue = JIRA.get_issue_by_action_id(action_id)

    if jira_issue:
        status = jira_issue.get("status", "To Do")
        jira_key_actual = jira_issue.get("key")
        # In enterprise workflow, Jira must be In Progress or Done
        jira_ok = status in ["In Progress", "Done", "Closed", "Resolved"]
        logs.append(f"Checked Jira [{jira_key_actual}]: status '{status}' (Valid: {jira_ok})")
        return {
            "jira_issue_key": jira_key_actual,
            "jira_status": status,
            "jira_ok": jira_ok,
            "logs": logs
        }
    else:
        logs.append(f"No active Jira task found for {action_id}. Flagged for review.")
        return {
            "jira_issue_key": None,
            "jira_status": "Missing",
            "jira_ok": False,
            "logs": logs
        }


def semantic_evidence_node(state: ValidationState) -> Dict[str, Any]:
    """Compares uploaded evidence against the mandate requirements semantically."""
    logs = list(state.get("logs", []))
    map_record = state.get("map_record", {})
    action_req = map_record.get("action", "").lower()
    proof_text = state.get("proof_text", "").lower()

    if not proof_text or len(proof_text.strip()) < 15:
        logs.append("Proof evidence text is empty or too short.")
        return {
            "semantic_score": 0.0,
            "logs": logs
        }

    # Extract actionable keywords from requirements
    req_tokens = set(re.findall(r'[a-zA-Z]{4,}', action_req))
    # Exclude common stopwords
    stopwords = {"must", "shall", "banks", "operators", "system", "these", "directions", "apply", "requirement"}
    meaningful_tokens = req_tokens - stopwords

    if not meaningful_tokens:
        meaningful_tokens = set(re.findall(r'[a-zA-Z]{3,}', action_req))

    proof_tokens = set(re.findall(r'[a-zA-Z]{3,}', proof_text))
    matched_req_tokens = meaningful_tokens.intersection(proof_tokens)

    overlap_ratio = len(matched_req_tokens) / len(meaningful_tokens) if meaningful_tokens else 0.5

    # Check for enterprise verification confirmations
    term_matches = sum(1 for term in VERIFICATION_CONFIRMATION_TERMS if term in proof_text)
    term_bonus = min(0.30, term_matches * 0.10)

    score = min(1.0, round(overlap_ratio * 0.70 + term_bonus, 2))
    logs.append(f"Semantic requirement match: {len(matched_req_tokens)}/{len(meaningful_tokens)} tokens matched. Confirmation terms found: {term_matches}. Score: {score}")

    return {
        "semantic_score": score,
        "logs": logs
    }


def assess_completion_node(state: ValidationState) -> Dict[str, Any]:
    """Combines Jira state and evidence score to render the final compliance verdict."""
    logs = list(state.get("logs", []))
    jira_ok = state.get("jira_ok", False)
    jira_status = state.get("jira_status", "Unknown")
    score = state.get("semantic_score", 0.0)

    # Threshold for validation
    if score >= 0.65 and jira_ok:
        status = "verified"
        feedback = f"Mandate successfully verified. Evidence alignment score: {score:.0%}. Jira ticket status: '{jira_status}'."
    elif score >= 0.65 and not jira_ok:
        status = "incomplete"
        feedback = f"Evidence content satisfies technical requirements ({score:.0%}), but linked Jira ticket is not marked Done/In Progress (current: '{jira_status}')."
    elif score < 0.65 and jira_ok:
        status = "incomplete"
        feedback = f"Jira ticket is '{jira_status}', but uploaded evidence does not sufficiently demonstrate mandate fulfillment (score: {score:.0%})."
    else:
        status = "incomplete"
        feedback = f"Validation incomplete: Evidence alignment is low ({score:.0%}) and Jira status is '{jira_status}'."

    logs.append(f"Verdict: {status.upper()} - {feedback}")
    return {
        "verification_status": status,
        "feedback": feedback,
        "logs": logs
    }


def commit_verification_node(state: ValidationState) -> Dict[str, Any]:
    """Persists verification verdict to database and logs immutable audit event."""
    action_id = state["action_id"]
    status = state["verification_status"]
    score = state["semantic_score"]
    feedback = state["feedback"]
    jira_ok = state["jira_ok"]

    db = SessionLocal()
    try:
        # 1. Update MAP record
        map_rec = db.query(MAPRecordModel).filter(MAPRecordModel.action_id == action_id).first()
        prev_state = map_rec.to_dict() if map_rec else {}
        if map_rec:
            map_rec.status = status
            db.commit()
            db.refresh(map_rec)
        new_state = map_rec.to_dict() if map_rec else {}

        # 2. Update Proof record
        proof_rec = (
            db.query(ProofRecordModel)
            .filter(ProofRecordModel.action_id == action_id)
            .order_by(ProofRecordModel.timestamp.desc())
            .first()
        )
        if proof_rec:
            proof_rec.verification_status = status
            proof_rec.verification_score = score
            proof_rec.verification_feedback = feedback
            proof_rec.jira_status_verified = jira_ok
            db.commit()

        # 3. Record Audit Trail
        action_type = "VERIFIED" if status == "verified" else "VERIFICATION_FAILED"
        AUDIT_TRAIL.record_event(
            action_id=action_id,
            action_type=action_type,
            actor_role=state.get("uploaded_by_role", "department_head"),
            actor_id=state.get("uploaded_by_id", "dept_user"),
            previous_state=prev_state,
            new_state=new_state,
            notes=feedback
        )
    finally:
        db.close()

    return {}


def build_validation_agent():
    """Compiles the LangGraph Validation Sub-Agent workflow."""
    builder = StateGraph(ValidationState)
    builder.add_node("check_jira", check_jira_node)
    builder.add_node("verify_evidence", semantic_evidence_node)
    builder.add_node("assess_completion", assess_completion_node)
    builder.add_node("commit_verification", commit_verification_node)

    builder.set_entry_point("check_jira")
    builder.add_edge("check_jira", "verify_evidence")
    builder.add_edge("verify_evidence", "assess_completion")
    builder.add_edge("assess_completion", "commit_verification")
    builder.add_edge("commit_verification", END)

    return builder.compile()


# Global validation sub-agent instance
VALIDATION_AGENT = build_validation_agent()


def verify_compliance_proof(
    action_id: str,
    proof_text: str,
    filename: str = "proof.pdf",
    uploaded_by_role: str = "department_head",
    uploaded_by_id: str = "dept_user"
) -> Dict[str, Any]:
    """
    Public entry point to verify an uploaded proof document for an action ID.
    Executes the LangGraph validation sub-agent.
    """
    db = SessionLocal()
    try:
        map_rec = db.query(MAPRecordModel).filter(MAPRecordModel.action_id == action_id).first()
        map_dict = map_rec.to_dict() if map_rec else {}
    finally:
        db.close()

    initial_state: ValidationState = {
        "action_id": action_id,
        "map_record": map_dict,
        "proof_text": proof_text,
        "filename": filename,
        "uploaded_by_role": uploaded_by_role,
        "uploaded_by_id": uploaded_by_id,
        "jira_issue_key": map_dict.get("jira_issue_key"),
        "jira_status": "Unknown",
        "jira_ok": False,
        "semantic_score": 0.0,
        "verification_status": "incomplete",
        "feedback": "",
        "logs": []
    }

    result = VALIDATION_AGENT.invoke(initial_state)
    return {
        "action_id": action_id,
        "verification_status": result["verification_status"],
        "verification_score": result["semantic_score"],
        "feedback": result["feedback"],
        "jira_status": result["jira_status"],
        "jira_ok": result["jira_ok"],
        "logs": result["logs"]
    }
