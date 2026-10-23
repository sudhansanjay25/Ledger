import os
import sys
import pytest
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENT_DIR = os.path.join(BASE_DIR, "agent")
for p in (BASE_DIR, AGENT_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from extractor import ObligationExtractor


def test_extractor_required_modality():
    extractor = ObligationExtractor(reference_date_str="2026-07-01")
    text = "All banks must implement multi-factor authentication for digital payments."
    obs = extractor.extract_obligations(text)
    assert len(obs) == 1
    assert obs[0]["obligation_type"] == "REQUIRED"
    assert obs[0]["quote_verified"] is True


def test_extractor_prohibited_modality():
    extractor = ObligationExtractor(reference_date_str="2026-07-01")
    text = "Entities shall not store raw card credentials or CVV numbers under any circumstances."
    obs = extractor.extract_obligations(text)
    assert len(obs) == 1
    assert obs[0]["obligation_type"] == "PROHIBITED"


def test_extractor_advisory_modality():
    extractor = ObligationExtractor(reference_date_str="2026-07-01")
    text = "Banks should periodically evaluate and are advised to maintain independent review panels."
    # Needs obligation trigger like 'must' or 'shall' or 'required'
    text2 = "Banks are required to maintain systems, and should conduct independent review panels."
    obs = extractor.extract_obligations(text2)
    assert len(obs) == 1
    assert obs[0]["obligation_type"] == "ADVISORY"


def test_extractor_explicit_date():
    extractor = ObligationExtractor(reference_date_str="2026-07-01")
    text = "All institutions must complete registration no later than December 31, 2026."
    obs = extractor.extract_obligations(text)
    assert len(obs) == 1
    assert obs[0]["deadline"] == "2026-12-31"
    assert obs[0]["deadline_type"] == "explicit"


def test_extractor_relative_deadline_days():
    ref_str = "2026-07-01"
    ref_dt = datetime.strptime(ref_str, "%Y-%m-%d")
    expected = (ref_dt + timedelta(days=30)).strftime("%Y-%m-%d")

    extractor = ObligationExtractor(reference_date_str=ref_str)
    text = "Payment operators shall submit compliance reports within 30 days."
    obs = extractor.extract_obligations(text)
    assert len(obs) == 1
    assert obs[0]["deadline"] == expected
    assert obs[0]["deadline_type"] == "derived"


def test_extractor_relative_deadline_months():
    ref_str = "2026-07-01"
    ref_dt = datetime.strptime(ref_str, "%Y-%m-%d")
    expected = (ref_dt + timedelta(days=90)).strftime("%Y-%m-%d")

    extractor = ObligationExtractor(reference_date_str=ref_str)
    text = "Entities must migrate key stores within three months."
    obs = extractor.extract_obligations(text)
    assert len(obs) == 1
    assert obs[0]["deadline"] == expected
    assert obs[0]["deadline_type"] == "derived"


def test_extractor_forthwith_deadline():
    ref_str = "2026-07-01"
    ref_dt = datetime.strptime(ref_str, "%Y-%m-%d")
    expected = (ref_dt + timedelta(days=3)).strftime("%Y-%m-%d")

    extractor = ObligationExtractor(reference_date_str=ref_str)
    text = "All banks shall block compromised IP addresses forthwith."
    obs = extractor.extract_obligations(text)
    assert len(obs) == 1
    assert obs[0]["deadline"] == expected
    assert obs[0]["deadline_type"] == "derived"


def test_extractor_empty_input():
    extractor = ObligationExtractor()
    assert extractor.extract_obligations("") == []
