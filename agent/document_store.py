import os
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
from security_validator import calculate_sha256


class DocumentStore:
    """
    Centralized regulatory document catalog with SHA-256 content deduplication,
    metadata indexing, and integration with LangGraph agent tools.
    """

    def __init__(self):
        # Maps doc_id -> Document dict
        self._documents: Dict[str, Dict[str, Any]] = {}
        # Maps sha256_hash -> doc_id (for fast deduplication)
        self._hash_index: Dict[str, str] = {}

    def register_document(
        self,
        raw_text: str,
        title: str,
        source_url: str = "https://rbi.org.in/circulars",
        format_type: str = "digital_pdf",
        regulator: str = "RBI",
        published_date: Optional[str] = None,
        custom_id: Optional[str] = None,
        quality_score: float = 1.0,
        is_readable: bool = True,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Registers a document in the catalog.
        If a document with the exact same SHA-256 hash already exists,
        returns the existing document and sets 'is_duplicate': True.
        """
        text_bytes = raw_text.encode("utf-8")
        sha256_hash = calculate_sha256(text_bytes)

        # Deduplication check
        if sha256_hash in self._hash_index:
            existing_id = self._hash_index[sha256_hash]
            existing_doc = dict(self._documents[existing_id])
            existing_doc["is_duplicate"] = True
            existing_doc["message"] = f"Document already indexed as '{existing_id}'."
            return existing_doc

        # Generate unique circular ID
        if custom_id:
            doc_id = custom_id
        else:
            authority_prefix = regulator.lower().replace(" ", "_")
            doc_id = f"cir_{authority_prefix}_{sha256_hash[:8]}"

        doc_entry = {
            "id": doc_id,
            "title": title,
            "regulator": regulator,
            "source_url": source_url,
            "format": format_type,
            "sha256": sha256_hash,
            "raw_text": raw_text,
            "quality_score": quality_score,
            "is_readable": is_readable,
            "published_date": published_date or datetime.now().strftime("%Y-%m-%d"),
            "ingested_at": datetime.now().isoformat(),
            "status": "INGESTED",
            "metadata": metadata or {},
            "is_duplicate": False
        }

        self._documents[doc_id] = doc_entry
        self._hash_index[sha256_hash] = doc_id

        # Also register in tools.MOCK_DOCUMENTS if tools module is imported
        try:
            from tools import MOCK_DOCUMENTS
            MOCK_DOCUMENTS[doc_id] = doc_entry
        except Exception:
            pass

        return doc_entry

    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a document by its ID."""
        return self._documents.get(doc_id)

    def find_by_hash(self, sha256_hash: str) -> Optional[Dict[str, Any]]:
        """Retrieves a document by its SHA-256 hash."""
        doc_id = self._hash_index.get(sha256_hash)
        return self._documents.get(doc_id) if doc_id else None

    def list_documents(self) -> List[Dict[str, Any]]:
        """Returns all registered documents."""
        return list(self._documents.values())

    def count(self) -> int:
        """Returns total number of unique documents indexed."""
        return len(self._documents)


# Global catalog singleton instance
CATALOG = DocumentStore()


def initialize_catalog_defaults():
    """Seeds the catalog with preset benchmark documents."""
    try:
        from sample_data import BENIGN_RBI_CIRCULAR, MALICIOUS_INJECTION_CIRCULAR, LOW_QUALITY_OCR_CIRCULAR

        CATALOG.register_document(
            raw_text=BENIGN_RBI_CIRCULAR["raw_text"],
            title=BENIGN_RBI_CIRCULAR["title"],
            source_url=BENIGN_RBI_CIRCULAR["source_url"],
            format_type=BENIGN_RBI_CIRCULAR["format"],
            regulator="RBI",
            custom_id="rbi_2026_payment_sec_01",
            quality_score=0.83
        )

        CATALOG.register_document(
            raw_text=MALICIOUS_INJECTION_CIRCULAR["raw_text"],
            title=MALICIOUS_INJECTION_CIRCULAR["title"],
            source_url=MALICIOUS_INJECTION_CIRCULAR["source_url"],
            format_type=MALICIOUS_INJECTION_CIRCULAR["format"],
            regulator="RBI",
            custom_id="malicious_spoof_01",
            quality_score=0.88
        )

        CATALOG.register_document(
            raw_text=LOW_QUALITY_OCR_CIRCULAR["raw_text"],
            title=LOW_QUALITY_OCR_CIRCULAR["title"],
            source_url=LOW_QUALITY_OCR_CIRCULAR["source_url"],
            format_type=LOW_QUALITY_OCR_CIRCULAR["format"],
            regulator="RBI",
            custom_id="rbi_2026_low_ocr_02",
            quality_score=0.23,
            is_readable=False
        )
    except Exception:
        pass


initialize_catalog_defaults()
