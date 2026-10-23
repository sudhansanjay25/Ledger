import os
import sys
import pytest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENT_DIR = os.path.join(BASE_DIR, "agent")
for p in (BASE_DIR, AGENT_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

import tools
from tools import (
    fetch_document,
    security_scan,
    extract_text,
    classify_document,
    extract_obligations,
    generate_map_objects,
    ACTIVE_DOCUMENT
)


def test_fetch_document_success():
    res = fetch_document.invoke({"document_id": "rbi_2026_payment_sec_01"})
    assert "error" not in res
    assert res["id"] == "rbi_2026_payment_sec_01"
    assert tools.ACTIVE_DOCUMENT["id"] == "rbi_2026_payment_sec_01"


def test_fetch_document_not_found():
    res = fetch_document.invoke({"document_id": "non_existent_doc_id_999"})
    assert "error" in res


def test_security_scan_passes_for_benign():
    fetch_document.invoke({"document_id": "rbi_2026_payment_sec_01"})
    res = security_scan.invoke({})
    assert res["is_safe"] is True
    assert res["threat_detected"] is None


def test_security_scan_flags_injection():
    fetch_document.invoke({"document_id": "malicious_spoof_01"})
    res = security_scan.invoke({})
    assert res["is_safe"] is False
    assert res["threat_detected"] == "Prompt Injection Attempt"


def test_security_scan_untrusted_domain():
    tools.ACTIVE_DOCUMENT = {
        "raw_text": "This is legitimate circular content.",
        "source_url": "https://untrusted-hacker-site.xyz/doc.pdf"
    }
    res = security_scan.invoke({})
    assert res["is_safe"] is False
    assert res["threat_detected"] == "Untrusted Source Domain"


def test_security_scan_homoglyph():
    tools.ACTIVE_DOCUMENT = {
        "raw_text": "All b\u0430nks must comply immediately.",  # \u0430 is Cyrillic small letter a
        "source_url": "https://rbi.org.in/circular.pdf"
    }
    res = security_scan.invoke({})
    assert res["is_safe"] is False
    assert res["threat_detected"] == "Unicode Homoglyph Attack"


def test_security_scan_rtl_override():
    tools.ACTIVE_DOCUMENT = {
        "raw_text": "Compliance \u202Ereversed instruction\u202C check.",
        "source_url": "https://rbi.org.in/circular.pdf"
    }
    res = security_scan.invoke({})
    assert res["is_safe"] is False
    assert res["threat_detected"] == "BiDi/RTL Text Override Attack"


def test_extract_text_and_quality():
    fetch_document.invoke({"document_id": "rbi_2026_payment_sec_01"})
    res = extract_text.invoke({})
    assert res["is_readable"] is True
    assert res["quality_score"] > 0.5


def test_classify_document():
    fetch_document.invoke({"document_id": "rbi_2026_payment_sec_01"})
    extract_text.invoke({})
    res = classify_document.invoke({})
    assert res["category"] == "Cybersecurity & Digital Payments"
    assert "IT" in res["departments"]
    assert res["priority"] in ["Critical", "High", "Medium", "Low"]


def test_extract_obligations_explicit_and_implicit():
    fetch_document.invoke({"document_id": "rbi_2026_payment_sec_01"})
    extract_text.invoke({})
    res = extract_obligations.invoke({"reference_date_str": "2026-07-15"})
    obs = res["obligations"]
    assert len(obs) > 0
    # Check that at least one obligation has explicit deadline
    has_explicit = any(o["deadline_type"] == "explicit" for o in obs)
    assert has_explicit is True


def test_generate_map_objects():
    fetch_document.invoke({"document_id": "rbi_2026_payment_sec_01"})
    extract_text.invoke({})
    classify_document.invoke({})
    extract_obligations.invoke({"reference_date_str": "2026-07-15"})
    maps = generate_map_objects.invoke({})
    assert isinstance(maps, list)
    assert len(maps) > 0
    first = maps[0]
    assert "action_id" in first
    assert "action" in first
    assert "department" in first
    assert "confidence" in first
    assert 0.0 <= first["confidence"] <= 1.0
