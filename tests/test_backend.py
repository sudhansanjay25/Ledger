import os
import sys
import io
import json
import pytest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
AGENT_DIR = os.path.join(BASE_DIR, "agent")
for p in (BASE_DIR, BACKEND_DIR, AGENT_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_health_check(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "healthy"
    assert "Ledger Agent API" in data["service"]


def test_list_documents(client):
    res = client.get("/api/documents")
    assert res.status_code == 200
    data = res.get_json()
    assert "documents" in data
    doc_ids = [d["id"] for d in data["documents"]]
    assert "rbi_2026_payment_sec_01" in doc_ids
    assert "malicious_spoof_01" in doc_ids
    assert "rbi_2026_low_ocr_02" in doc_ids


def test_upload_txt_document(client):
    file_content = b"This is a formal regulatory circular. All banks must implement continuous fraud monitoring before December 31, 2026."
    data = {
        "title": "Uploaded Custom Test Circular",
        "file": (io.BytesIO(file_content), "test_circular.txt")
    }
    res = client.post("/api/documents/upload", data=data, content_type="multipart/form-data")
    assert res.status_code == 200
    result = res.get_json()
    assert "upload" in result["document_id"]
    assert result["is_readable"] is True
    assert result["total_words"] > 5


def test_agent_run_start_and_status(client):
    payload = {"document_id": "rbi_2026_payment_sec_01"}
    res = client.post("/api/agent/run", json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert "session_id" in data
    assert data["status"] == "started"

    # Verify status endpoint works
    status_res = client.get(f"/api/agent/status/{data['session_id']}")
    assert status_res.status_code == 200
    status_data = status_res.get_json()
    assert status_data["session_id"] == data["session_id"]
    assert status_data["status"] in ["running", "completed"]


def test_crawler_endpoints(client):
    # Test crawler status
    status_res = client.get("/api/crawler/status")
    assert status_res.status_code == 200
    status_data = status_res.get_json()
    assert "interval_hours" in status_data
    assert "catalog_document_count" in status_data

    # Test crawler trigger
    trigger_res = client.post("/api/crawler/trigger")
    assert trigger_res.status_code == 200
    trigger_data = trigger_res.get_json()
    assert trigger_data["status"] == "success"
    assert "summary" in trigger_data


def test_upload_html_document(client):
    html_content = b"<!DOCTYPE html><html><head><title>NPCI Operational Circular</title></head><body><p>PSOs must implement real-time token validation immediately.</p></body></html>"
    data = {
        "title": "Uploaded HTML Directive",
        "file": (io.BytesIO(html_content), "directive.html")
    }
    res = client.post("/api/documents/upload", data=data, content_type="multipart/form-data")
    assert res.status_code == 200
    res_data = res.get_json()
    assert res_data["status"] == "success"
    assert res_data["format"] == "html"
    assert "sha256" in res_data


def test_upload_spoofed_extension_blocked(client):
    # File named fake.pdf containing shell script
    script_bytes = b"#!/bin/bash\nrm -rf /tmp/data\n"
    data = {
        "title": "Spoofed Attack",
        "file": (io.BytesIO(script_bytes), "fake.pdf")
    }
    res = client.post("/api/documents/upload", data=data, content_type="multipart/form-data")
    assert res.status_code == 400
    err_data = res.get_json()
    assert "error" in err_data
    assert "Spoofing" in err_data["error"] or "safety" in err_data["error"].lower()

