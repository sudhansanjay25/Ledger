import os
import sys
import pytest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENT_DIR = os.path.join(BASE_DIR, "agent")
for p in (BASE_DIR, AGENT_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from classifier import RegulatoryClassifier, REGULATORY_TAXONOMY
from feedback_memory import FeedbackMemory


def test_classifier_cybersecurity_category():
    clf = RegulatoryClassifier()
    text = "All banks must implement robust multi-factor authentication (mfa) and cloud encryption for UPI transactions."
    res = clf.classify(text)
    assert res["category"] == "Cybersecurity & Digital Payments"
    assert "IT" in res["departments"]
    assert "Information Security" in res["departments"]
    assert res["confidence"] >= 0.85


def test_classifier_kyc_aml_category():
    clf = RegulatoryClassifier()
    text = "Entities shall verify customer identity using Aadhaar, PAN and report suspicious money laundering transactions."
    res = clf.classify(text)
    assert res["category"] == "Compliance & KYC / AML"
    assert "Compliance" in res["departments"]
    assert "Legal" in res["departments"]


def test_classifier_penal_priority_critical():
    clf = RegulatoryClassifier()
    text = "Failure to comply will attract monetary fine and prosecution under penal action."
    res = clf.classify(text)
    assert res["priority"] == "Critical"


def test_classifier_urgency_priority_high():
    clf = RegulatoryClassifier()
    text = "Entities are instructed to implement this forthwith without delay."
    res = clf.classify(text)
    assert res["priority"] == "High"


def test_classifier_advisory_priority_low():
    clf = RegulatoryClassifier()
    text = "Banks are encouraged and should consider evaluating customer sentiment quarterly."
    res = clf.classify(text)
    assert res["priority"] == "Low"


def test_classifier_feedback_exemplar_integration():
    mem = FeedbackMemory()
    mem.record_correction(
        topic="cloud_key_management",
        keywords=["hsm", "hardware security module"],
        corrected_departments=["Treasury", "SpecialOps"],
        corrected_priority="Critical",
        notes="Audit requirement"
    )
    clf = RegulatoryClassifier(feedback_store=mem)
    text = "Banks must install a hardware security module (hsm) for encryption."
    res = clf.classify(text)
    assert "SpecialOps" in res["departments"]
    assert "Treasury" in res["departments"]
    assert res["priority"] == "Critical"
    assert res["exemplars_applied"] >= 1


def test_classifier_empty_text():
    clf = RegulatoryClassifier()
    res = clf.classify("")
    assert res["category"] == "General Banking Regulations"
    assert res["departments"] == ["Operations"]
    assert res["priority"] == "Medium"
