import os
import sys
import pytest

# Add project root and agent directory to sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENT_DIR = os.path.join(BASE_DIR, "agent")
for p in (BASE_DIR, AGENT_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from pdf_extractor import validate_pdf_bytes, compute_text_quality, extract_text_from_pdf


def test_validate_pdf_bytes_valid():
    valid_pdf_header = b"%PDF-1.7\n1 0 obj\n<<>>\nendobj"
    assert validate_pdf_bytes(valid_pdf_header) is True


def test_validate_pdf_bytes_invalid():
    invalid_bytes = b"NOT_A_PDF_FILE"
    assert validate_pdf_bytes(invalid_bytes) is False


def test_compute_text_quality_high():
    text = "The Reserve Bank of India hereby issues guidelines for digital banking authentication."
    res = compute_text_quality(text)
    assert res["is_readable"] is True
    assert res["quality_score"] > 0.8
    assert res["total_words"] == 12


def test_compute_text_quality_low_gibberish():
    gibberish = "00010101 11110000 00000000 !@#$%^ &*()_+ 12345"
    res = compute_text_quality(gibberish)
    assert res["is_readable"] is False
    assert res["quality_score"] < 0.5


def test_extract_text_from_ledger_pdf():
    pdf_path = os.path.join(BASE_DIR, "Ledger.pdf")
    if not os.path.exists(pdf_path):
        pytest.skip("Ledger.pdf not found in workspace root")

    res = extract_text_from_pdf(pdf_path)
    assert res["success"] is True
    assert res["page_count"] > 0
    assert len(res["text"]) > 100
    assert res["is_readable"] is True
    assert res["quality_score"] >= 0.5
