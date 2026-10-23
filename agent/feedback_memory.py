import os
import json
from typing import Dict, Any, List, Optional
from datetime import datetime


class FeedbackMemory:
    """
    Stores compliance officer corrections and provides few-shot exemplars
    to prevent recurring classification and routing errors.
    """

    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = storage_path
        self._corrections: List[Dict[str, Any]] = []
        self._load_seed_exemplars()

    def _load_seed_exemplars(self):
        """Loads domain-specific baseline human correction exemplars."""
        self._corrections = [
            {
                "topic": "cloud_key_management",
                "keywords": ["hsm", "hardware security module", "encryption key", "cloud key"],
                "corrected_departments": ["IT", "Information Security", "Treasury"],
                "corrected_priority": "Critical",
                "notes": "Encryption key custody always involves InfoSec and Treasury sign-off."
            },
            {
                "topic": "offline_wallet_sync",
                "keywords": ["upi lite", "offline balance", "wallet sync", "offline payment"],
                "corrected_departments": ["Operations", "IT", "Product"],
                "corrected_priority": "High",
                "notes": "Offline wallet reconciliation requires Operations and Product teams."
            },
            {
                "topic": "algorithmic_surveillance",
                "keywords": ["algo", "circuit breaker", "volatility", "stock broker", "trade order"],
                "corrected_departments": ["Compliance", "Risk Management", "Trading Operations"],
                "corrected_priority": "Critical",
                "notes": "Algorithmic trading surveillance mandates Compliance and Risk sign-off."
            }
        ]

    def record_correction(
        self,
        topic: str,
        keywords: List[str],
        corrected_departments: List[str],
        corrected_priority: Optional[str] = None,
        notes: str = ""
    ) -> Dict[str, Any]:
        """Records a human correction into the feedback memory."""
        entry = {
            "topic": topic,
            "keywords": [k.lower() for k in keywords],
            "corrected_departments": corrected_departments,
            "corrected_priority": corrected_priority or "Medium",
            "notes": notes,
            "created_at": datetime.now().isoformat()
        }
        self._corrections.append(entry)
        return entry

    def find_relevant_exemplars(self, text: str, max_results: int = 2) -> List[Dict[str, Any]]:
        """
        Retrieves historical human corrections matching terms in the circular text.
        """
        text_lower = text.lower()
        scored_matches = []

        for item in self._corrections:
            matches = sum(1 for kw in item["keywords"] if kw in text_lower)
            if matches > 0:
                scored_matches.append((matches, item))

        scored_matches.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored_matches[:max_results]]

    def get_all_corrections(self) -> List[Dict[str, Any]]:
        """Returns all registered corrections."""
        return list(self._corrections)


# Global feedback memory instance
FEEDBACK_STORE = FeedbackMemory()
