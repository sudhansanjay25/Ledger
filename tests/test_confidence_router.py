import os
import sys
import pytest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENT_DIR = os.path.join(BASE_DIR, "agent")
for p in (BASE_DIR, AGENT_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from confidence_router import ConfidenceRouter


def test_router_tier_1_auto_assign():
    map_item = {
        "action_id": "MAP-01",
        "action": "Ensure backup systems are synchronized across data centers.",
        "department": ["IT", "Operations"],
        "confidence": 0.94,
        "priority": "Medium",
        "quote_verified": True
    }
    decision = ConfidenceRouter.evaluate_routing(map_item)
    assert decision["status"] == "auto_assigned"
    assert decision["routing_tier"] == "tier_1_auto_assign"
    assert decision["requires_human_review"] is False
    assert decision["assigned_department"] == "IT"


def test_router_tier_2_pending_approval():
    map_item = {
        "action_id": "MAP-02",
        "action": "Reconcile failed transaction logs within three business days.",
        "department": ["Operations"],
        "confidence": 0.82,
        "priority": "Medium",
        "quote_verified": True
    }
    decision = ConfidenceRouter.evaluate_routing(map_item)
    assert decision["status"] == "pending_approval"
    assert decision["routing_tier"] == "tier_2_pending_approval"
    assert decision["requires_human_review"] is True


def test_router_tier_3_human_review():
    map_item = {
        "action_id": "MAP-03",
        "action": "Perform periodic risk assessment on third party vendors.",
        "department": ["Compliance"],
        "confidence": 0.62,
        "priority": "Low",
        "quote_verified": True
    }
    decision = ConfidenceRouter.evaluate_routing(map_item)
    assert decision["status"] == "in_review_queue"
    assert decision["routing_tier"] == "tier_3_human_review"
    assert decision["requires_human_review"] is True


def test_router_critical_priority_safety_guard():
    # Confidence is 0.92 (> 0.90), but priority is Critical so it must NOT auto-assign without 0.95+
    map_item = {
        "action_id": "MAP-04",
        "action": "Report data breach incidents immediately to regulatory authorities.",
        "department": ["Compliance", "IT"],
        "confidence": 0.92,
        "priority": "Critical",
        "quote_verified": True
    }
    decision = ConfidenceRouter.evaluate_routing(map_item)
    assert decision["status"] == "pending_approval"
    assert decision["requires_human_review"] is True


def test_router_hallucination_guard():
    # High confidence, but quote verification failed
    map_item = {
        "action_id": "MAP-05",
        "action": "Install physical biometrics at branch vault entries.",
        "department": ["Operations"],
        "confidence": 0.95,
        "priority": "Medium",
        "quote_verified": False
    }
    decision = ConfidenceRouter.evaluate_routing(map_item)
    assert decision["status"] == "in_review_queue"
    assert decision["requires_human_review"] is True
    assert "hallucination" in decision["reason"].lower() or "unverified" in decision["reason"].lower()
