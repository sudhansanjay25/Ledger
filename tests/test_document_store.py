import os
import sys
import pytest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENT_DIR = os.path.join(BASE_DIR, "agent")
for p in (BASE_DIR, AGENT_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from document_store import DocumentStore


def test_document_store_registration():
    store = DocumentStore()
    text = "Regulated entities must implement transaction monitoring before December 31, 2026."
    doc = store.register_document(
        raw_text=text,
        title="Payment Security Rules",
        regulator="RBI",
        source_url="https://rbi.org.in/notice-1.pdf"
    )
    assert doc["id"].startswith("cir_rbi_")
    assert doc["is_duplicate"] is False
    assert len(doc["sha256"]) == 64
    assert store.count() == 1


def test_document_store_sha256_deduplication():
    store = DocumentStore()
    text = "Regulated entities must implement transaction monitoring before December 31, 2026."

    doc1 = store.register_document(
        raw_text=text,
        title="Payment Security Rules",
        regulator="RBI"
    )
    assert doc1["is_duplicate"] is False

    # Second registration with identical content should be flagged as duplicate
    doc2 = store.register_document(
        raw_text=text,
        title="Payment Security Rules Copy",
        regulator="RBI"
    )
    assert doc2["is_duplicate"] is True
    assert doc2["id"] == doc1["id"]
    assert store.count() == 1


def test_document_store_lookup():
    store = DocumentStore()
    doc = store.register_document(
        raw_text="Unique circular content 12345.",
        title="Unique Notice",
        custom_id="test_custom_doc_01"
    )
    retrieved = store.get_document("test_custom_doc_01")
    assert retrieved is not None
    assert retrieved["title"] == "Unique Notice"

    by_hash = store.find_by_hash(doc["sha256"])
    assert by_hash is not None
    assert by_hash["id"] == "test_custom_doc_01"
