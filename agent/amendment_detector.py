import re
from typing import Dict, Any, List, Optional
import chromadb


class AmendmentDetector:
    """
    RAG-powered amendment and supersession engine using ChromaDB.
    Detects when new circulars amend, supersede, or invalidate past obligations.
    """

    def __init__(self, collection_name: str = "ledger_circular_history"):
        self.client = chromadb.Client()
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"description": "Regulatory circular vector index for amendment tracking"}
        )

    def index_circular(self, circular_id: str, text: str, metadata: Optional[Dict[str, Any]] = None):
        """Indexes a regulatory circular text and metadata in ChromaDB."""
        meta = metadata or {}
        # Ensure metadata values are str, int, float, bool
        clean_meta = {k: str(v) for k, v in meta.items()}
        clean_meta["circular_id"] = circular_id

        # Use first 2000 chars for embedding representation
        doc_snippet = text[:2000] if text else "Empty Document"

        # Check if already exists in collection
        existing = self.collection.get(ids=[circular_id])
        if existing and existing["ids"]:
            self.collection.update(
                ids=[circular_id],
                documents=[doc_snippet],
                metadatas=[clean_meta]
            )
        else:
            self.collection.add(
                ids=[circular_id],
                documents=[doc_snippet],
                metadatas=[clean_meta]
            )

    def detect_supersession(self, new_text: str, new_circular_id: str) -> Dict[str, Any]:
        """
        Analyzes a new circular for explicit supersession clauses and
        semantically related historical circulars in ChromaDB.
        """
        if not new_text:
            return {
                "has_supersession": False,
                "explicit_references": [],
                "historical_matches": [],
                "details": "Empty document text provided."
            }

        # 1. Regex scanning for explicit supersession patterns
        supersession_patterns = [
            r"(?i)in\s+supersession\s+of\s+(?:circular\s+)?([A-Za-z0-9\.\-\/_]+)",
            r"(?i)supersedes\s+(?:circular\s+)?([A-Za-z0-9\.\-\/_]+)",
            r"(?i)partially\s+amends\s+(?:circular\s+)?([A-Za-z0-9\.\-\/_]+)",
            r"(?i)modifies\s+(?:paragraph\s+\d+\s+of\s+)?(?:circular\s+)?([A-Za-z0-9\.\-\/_]+)"
        ]

        explicit_superseded_refs = []
        for pat in supersession_patterns:
            matches = re.findall(pat, new_text)
            for m in matches:
                clean_ref = m.strip().rstrip(".,")
                if len(clean_ref) > 3 and clean_ref not in explicit_superseded_refs:
                    explicit_superseded_refs.append(clean_ref)

        # 2. Vector search in ChromaDB for semantically similar past circulars
        historical_matches = []
        if self.collection.count() > 0:
            query_snippet = new_text[:1000]
            try:
                results = self.collection.query(
                    query_texts=[query_snippet],
                    n_results=min(3, self.collection.count())
                )
                if results and results["ids"] and results["ids"][0]:
                    for idx, matched_id in enumerate(results["ids"][0]):
                        if matched_id != new_circular_id:
                            dist = results["distances"][0][idx] if results.get("distances") else 0.5
                            historical_matches.append({
                                "id": matched_id,
                                "similarity_distance": round(float(dist), 3),
                                "metadata": results["metadatas"][0][idx] if results.get("metadatas") else {}
                            })
            except Exception:
                pass

        has_supersession = len(explicit_superseded_refs) > 0 or len(historical_matches) > 0

        return {
            "has_supersession": has_supersession,
            "explicit_references": explicit_superseded_refs,
            "historical_matches": historical_matches,
            "details": f"Found {len(explicit_superseded_refs)} explicit supersession clauses and {len(historical_matches)} related circulars."
        }


# Global detector instance
AMENDMENT_TRACKER = AmendmentDetector()
