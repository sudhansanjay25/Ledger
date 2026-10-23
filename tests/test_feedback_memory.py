import os
import sys
import pytest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENT_DIR = os.path.join(BASE_DIR, "agent")
for p in (BASE_DIR, AGENT_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from feedback_memory import FeedbackMemory


def test_feedback_memory_seed_exemplars():
    mem = FeedbackMemory()
    corrections = mem.get_all_corrections()
    assert len(corrections) >= 3
    topics = [c["topic"] for c in corrections]
    assert "cloud_key_management" in topics
    assert "algorithmic_surveillance" in topics


def test_feedback_memory_record_correction():
    mem = FeedbackMemory()
    initial_count = len(mem.get_all_corrections())
    
    entry = mem.record_correction(
        topic="climate_risk_reporting",
        keywords=["esg", "green deposit", "climate disclosure", "carbon footprint"],
        corrected_departments=["Sustainability", "Risk Management", "Board Secretariat"],
        corrected_priority="High",
        notes="Mandatory for tier-1 NBFCs."
    )
    assert entry["topic"] == "climate_risk_reporting"
    assert len(mem.get_all_corrections()) == initial_count + 1


def test_feedback_memory_find_relevant_exemplars():
    mem = FeedbackMemory()
    # Test matching default seed exemplar (upi lite / offline wallet)
    text = "Directions on offline payment limits for UPI Lite transactions and wallet sync balance."
    matches = mem.find_relevant_exemplars(text)
    assert len(matches) >= 1
    top_match = matches[0]
    assert top_match["topic"] == "offline_wallet_sync"
    assert "Operations" in top_match["corrected_departments"]


def test_feedback_memory_find_no_matches():
    mem = FeedbackMemory()
    text = "Agricultural crop loan interest subvention guidelines."
    matches = mem.find_relevant_exemplars(text)
    assert len(matches) == 0
