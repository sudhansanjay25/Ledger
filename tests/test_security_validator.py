import os
import sys
import pytest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENT_DIR = os.path.join(BASE_DIR, "agent")
for p in (BASE_DIR, AGENT_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from security_validator import calculate_sha256, detect_file_type, validate_document_safety


def test_calculate_sha256():
    sample_bytes = b"Reserve Bank of India Master Direction 2026"
    h1 = calculate_sha256(sample_bytes)
    h2 = calculate_sha256(sample_bytes)
    assert h1 == h2
    assert len(h1) == 64


def test_detect_pdf_magic_bytes():
    pdf_bytes = b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n"
    fmt, is_valid, err = detect_file_type(pdf_bytes, "circular.pdf")
    assert fmt == "pdf"
    assert is_valid is True
    assert err == ""


def test_detect_html_magic_bytes():
    html_bytes = b"<!DOCTYPE html><html><head><title>Circular</title></head><body>Notice</body></html>"
    fmt, is_valid, err = detect_file_type(html_bytes, "circular.html")
    assert fmt == "html"
    assert is_valid is True
    assert err == ""


def test_extension_spoofing_blocked():
    # A shell script or binary disguised as a .pdf
    fake_pdf = b"#!/bin/bash\nrm -rf /tmp/data\n"
    safety = validate_document_safety(fake_pdf, "malicious.pdf")
    assert safety["is_safe_format"] is False
    assert safety["extension_mismatch"] is True


def test_binary_executable_blocked():
    exe_bytes = b"MZ\x90\x00\x03\x00\x00\x00"
    safety = validate_document_safety(exe_bytes, "circular.pdf")
    assert safety["is_safe_format"] is False
    assert "binary_executable" in safety["error"] or "binary or executable" in safety["error"]
