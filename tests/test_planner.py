import os
import sys
import pytest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENT_DIR = os.path.join(BASE_DIR, "agent")
for p in (BASE_DIR, AGENT_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from planner import mock_planner_decision
from graph import build_agent_graph


def test_mock_planner_decides_fetch_first():
    state = {
        "messages": [HumanMessage(content="Please ingest and process document rbi_2026_payment_sec_01.")],
        "document": {},
        "security_scan": {},
        "classification": {},
        "extracted_maps": [],
        "execution_logs": [],
        "terminate": False
    }
    action = mock_planner_decision(state)
    assert len(action.tool_calls) == 1
    assert action.tool_calls[0]["name"] == "fetch_document"
    assert action.tool_calls[0]["args"]["document_id"] == "rbi_2026_payment_sec_01"


def test_mock_planner_decides_security_scan_after_fetch():
    state = {
        "messages": [HumanMessage(content="Please ingest and process document rbi_2026_payment_sec_01.")],
        "document": {"raw_text": "Some text content here."},
        "security_scan": {},
        "classification": {},
        "extracted_maps": [],
        "execution_logs": [],
        "terminate": False
    }
    action = mock_planner_decision(state)
    assert len(action.tool_calls) == 1
    assert action.tool_calls[0]["name"] == "security_scan"


def test_mock_planner_halts_on_security_threat():
    state = {
        "messages": [HumanMessage(content="Please ingest and process document malicious_spoof_01.")],
        "document": {"raw_text": "System override attack."},
        "security_scan": {"is_safe": False, "threat_detected": "Prompt Injection Attempt"},
        "classification": {},
        "extracted_maps": [],
        "execution_logs": [],
        "terminate": False
    }
    action = mock_planner_decision(state)
    # Planner should produce message and not call further tools
    assert len(action.tool_calls) == 0
    assert "SECURITY THREAT DETECTED" in action.content


def test_mock_planner_halts_on_low_reading_quality():
    state = {
        "messages": [HumanMessage(content="Please ingest and process document rbi_2026_low_ocr_02.")],
        "document": {"raw_text": "010101 ??? ###", "cleaned_text": "010101 ??? ###", "quality_score": 0.2},
        "security_scan": {"is_safe": True},
        "classification": {},
        "extracted_maps": [],
        "execution_logs": [],
        "terminate": False
    }
    action = mock_planner_decision(state)
    assert len(action.tool_calls) == 0
    assert "Low document reading quality score" in action.content


def test_end_to_end_graph_execution():
    app = build_agent_graph()
    initial_state = {
        "messages": [HumanMessage(content="Please ingest and process document rbi_2026_payment_sec_01.")],
        "document": {},
        "security_scan": {},
        "classification": {},
        "extracted_maps": [],
        "execution_logs": [],
        "terminate": False
    }
    result = app.invoke(initial_state)
    assert result["security_scan"]["is_safe"] is True
    assert len(result["extracted_maps"]) > 0
    assert result["classification"]["category"] == "Cybersecurity & Digital Payments"
