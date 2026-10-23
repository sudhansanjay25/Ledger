import os
import sys
import pytest
from pydantic import ValidationError

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENT_DIR = os.path.join(BASE_DIR, "agent")
for p in (BASE_DIR, AGENT_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from models import MAPObject, HallucinationValidator, re_tokenize


def test_map_object_valid():
    map_item = MAPObject(
        action_id="MAP-RBI-01",
        action="Implement robust Multi-Factor Authentication for all digital payments",
        department=["IT", "Information Security"],
        deadline="2026-12-31",
        deadline_type="explicit",
        priority="Critical",
        obligation_type="REQUIRED",
        source_sentence="All banks must implement robust Multi-Factor Authentication by December 31, 2026.",
        confidence=0.954,
        circular_id="rbi_2026_01"
    )
    dumped = map_item.model_dump()
    assert dumped["action_id"] == "MAP-RBI-01"
    assert dumped["confidence"] == 0.95  # Rounded to 2 decimals
    assert "IT" in dumped["department"]
    assert dumped["obligation_type"] == "REQUIRED"
    assert dumped["is_superseded"] is False


def test_map_object_validation_errors():
    # Short action should fail
    with pytest.raises(ValidationError):
        MAPObject(
            action_id="MAP-01",
            action="Too short",
            department=["IT"],
            source_sentence="Valid source sentence long enough",
            circular_id="circ_01"
        )

    # Empty department list should fail
    with pytest.raises(ValidationError):
        MAPObject(
            action_id="MAP-01",
            action="Valid action statement with sufficient length",
            department=[],
            source_sentence="Valid source sentence long enough",
            circular_id="circ_01"
        )

    # Invalid priority literal
    with pytest.raises(ValidationError):
        MAPObject(
            action_id="MAP-01",
            action="Valid action statement with sufficient length",
            department=["IT"],
            priority="UrgentNonStandard",
            source_sentence="Valid source sentence long enough",
            circular_id="circ_01"
        )


def test_hallucination_validator_exact_match():
    doc = "All banks must implement robust Multi-Factor Authentication by December 31, 2026 without delay."
    quote = "All banks must implement robust Multi-Factor Authentication"
    result = HallucinationValidator.verify_source_quote(quote, doc)
    assert result["verified"] is True
    assert result["score"] == 1.0


def test_hallucination_validator_token_overlap():
    doc = "Banks must implement robust Multi-Factor Authentication (MFA) by Dec 31, 2026."
    # Minor OCR variation / missing punctuation
    quote = "banks must implement robust multi factor authentication mfa by dec 31"
    result = HallucinationValidator.verify_source_quote(quote, doc)
    assert result["verified"] is True
    assert result["score"] >= 0.85


def test_hallucination_validator_hallucination_flag():
    doc = "Banks must implement Multi-Factor Authentication for payments."
    # Completely made-up quote
    fake_quote = "Every branch manager must physically inspect vault locks each morning."
    result = HallucinationValidator.verify_source_quote(fake_quote, doc)
    assert result["verified"] is False
    assert result["score"] < 0.5
    assert "Hallucination Warning" in result["reason"]


def test_hallucination_validator_empty_inputs():
    res1 = HallucinationValidator.verify_source_quote("", "Some text")
    assert res1["verified"] is False
    res2 = HallucinationValidator.verify_source_quote("Some quote", "")
    assert res2["verified"] is False


def test_re_tokenize():
    tokens = re_tokenize("Hello, World! 123 testing.")
    assert "hello" in tokens
    assert "world" in tokens
    assert "123" in tokens
    assert "testing" in tokens
