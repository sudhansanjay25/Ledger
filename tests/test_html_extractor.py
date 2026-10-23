import os
import sys
import pytest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENT_DIR = os.path.join(BASE_DIR, "agent")
for p in (BASE_DIR, AGENT_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from html_extractor import extract_text_from_html


def test_extract_text_from_valid_html():
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>RBI Master Direction on Cybersecurity</title>
        <script>alert("malicious script");</script>
        <style>body { color: red; }</style>
    </head>
    <body>
        <h1>Reserve Bank of India Directives</h1>
        <p>All scheduled commercial banks must enforce real-time multi-factor authentication for high value transfers.</p>
        <p>This direction applies forthwith across all digital branches.</p>
    </body>
    </html>
    """
    res = extract_text_from_html(html)
    assert res["success"] is True
    assert res["is_readable"] is True
    assert res["title"] == "RBI Master Direction on Cybersecurity"
    assert "alert" not in res["text"]
    assert "multi-factor authentication" in res["text"]
    assert res["quality_score"] > 0.7


def test_extract_text_from_empty_html():
    res = extract_text_from_html("")
    assert res["success"] is False
    assert res["total_words"] == 0


def test_extract_text_from_html_bytes():
    html_bytes = b"<html><body><p>Financial institutions must maintain audit logs for seven years.</p></body></html>"
    res = extract_text_from_html(html_bytes)
    assert res["success"] is True
    assert "seven years" in res["text"]
