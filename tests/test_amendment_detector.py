import os
import sys
import pytest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENT_DIR = os.path.join(BASE_DIR, "agent")
for p in (BASE_DIR, AGENT_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from amendment_detector import AmendmentDetector


def test_amendment_detector_explicit_supersession():
    detector = AmendmentDetector(collection_name="test_supersession_collection")
    text = (
        "In supersession of circular RBI/2024-25/102, the Reserve Bank hereby directs "
        "that all digital payment transactions shall follow updated limits."
    )
    result = detector.detect_supersession(text, new_circular_id="rbi_2026_new")
    assert result["has_supersession"] is True
    assert any("RBI/2024-25/102" in ref for ref in result["explicit_references"])


def test_amendment_detector_partially_amends():
    detector = AmendmentDetector(collection_name="test_amends_collection")
    text = (
        "This circular partially amends circular SEBI/HO/MIRSD/2023/45 regarding "
        "algorithmic trade surveillance and margin requirements."
    )
    result = detector.detect_supersession(text, new_circular_id="sebi_2026_01")
    assert result["has_supersession"] is True
    assert any("SEBI/HO/MIRSD/2023/45" in ref for ref in result["explicit_references"])


def test_amendment_detector_indexing_and_vector_retrieval():
    detector = AmendmentDetector(collection_name="test_vector_collection")
    
    # Index an earlier circular
    past_text = "Master Directions on cybersecurity framework for banks including multi-factor authentication and tokenization."
    detector.index_circular(
        circular_id="past_cybersec_01",
        text=past_text,
        metadata={"category": "Cybersecurity", "year": "2024"}
    )

    # Ingest a new circular on the exact same topic without explicit clause
    new_text = "Updated cybersecurity directive mandating additional tokenization and multi-factor authentication controls."
    result = detector.detect_supersession(new_text, new_circular_id="new_cybersec_02")
    
    # Should detect historical match via ChromaDB vector search
    assert len(result["historical_matches"]) >= 1
    assert result["historical_matches"][0]["id"] == "past_cybersec_01"


def test_amendment_detector_empty_text():
    detector = AmendmentDetector(collection_name="test_empty_collection")
    res = detector.detect_supersession("", "empty_doc")
    assert res["has_supersession"] is False
    assert res["explicit_references"] == []
