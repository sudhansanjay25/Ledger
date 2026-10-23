from typing import Dict, Any, List, Optional


class ConfidenceRouter:
    """
    3-Tier Confidence Routing Engine for compliance action points.
    Enforces risk-calibrated automation:
      - Score > 0.90: Auto-assign directly to department
      - Score 0.70–0.90: Assign with 'Pending Approval' flag
      - Score < 0.70: Route to Human Review Queue
    """

    AUTO_ASSIGN_THRESHOLD = 0.90
    PENDING_APPROVAL_THRESHOLD = 0.70

    @classmethod
    def evaluate_routing(cls, map_item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluates a MAP object's confidence score, hallucination status, and priority
        to determine the workflow state and department assignment.
        """
        confidence = float(map_item.get("confidence", 0.5))
        priority = map_item.get("priority", "Medium")
        departments = map_item.get("department", ["Operations"])
        primary_dept = departments[0] if departments else "Operations"
        
        quote_verified = map_item.get("quote_verified", True)
        if map_item.get("confidence", 1.0) < 0.5:
            quote_verified = False

        # Guard 1: Hallucination risk forces immediate human review
        if not quote_verified:
            return {
                "status": "in_review_queue",
                "assigned_department": primary_dept,
                "routing_tier": "tier_3_human_review",
                "requires_human_review": True,
                "reason": "Unverified source text or hallucination penalty"
            }

        # Guard 2: High stakes (Critical priority) cannot be fully auto-assigned without near-certainty
        if priority == "Critical" and confidence < 0.95:
            tier = "tier_2_pending_approval" if confidence >= cls.PENDING_APPROVAL_THRESHOLD else "tier_3_human_review"
            status = "pending_approval" if confidence >= cls.PENDING_APPROVAL_THRESHOLD else "in_review_queue"
            return {
                "status": status,
                "assigned_department": primary_dept,
                "routing_tier": tier,
                "requires_human_review": True,
                "reason": f"Critical enforcement mandate requires human compliance sign-off (confidence {confidence:.2f})"
            }

        # Standard 3-Tier Evaluation
        if confidence > cls.AUTO_ASSIGN_THRESHOLD:
            return {
                "status": "auto_assigned",
                "assigned_department": primary_dept,
                "routing_tier": "tier_1_auto_assign",
                "requires_human_review": False,
                "reason": f"High AI confidence ({confidence:.2f} > {cls.AUTO_ASSIGN_THRESHOLD})"
            }
        elif confidence >= cls.PENDING_APPROVAL_THRESHOLD:
            return {
                "status": "pending_approval",
                "assigned_department": primary_dept,
                "routing_tier": "tier_2_pending_approval",
                "requires_human_review": True,
                "reason": f"Moderate confidence ({confidence:.2f}) within pending approval window [{cls.PENDING_APPROVAL_THRESHOLD}, {cls.AUTO_ASSIGN_THRESHOLD}]"
            }
        else:
            return {
                "status": "in_review_queue",
                "assigned_department": primary_dept,
                "routing_tier": "tier_3_human_review",
                "requires_human_review": True,
                "reason": f"Low confidence ({confidence:.2f} < {cls.PENDING_APPROVAL_THRESHOLD}) requires triage by Compliance Officer"
            }


# Global confidence router instance
ROUTER = ConfidenceRouter()
