import re
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from models import HallucinationValidator


IMPLICIT_DEADLINE_MAP = {
    "forthwith": 3,
    "immediately": 7,
    "without delay": 7,
    "promptly": 14,
    "at the earliest": 7,
    "as soon as possible": 14,
    "within 24 hours": 1,
    "within 48 hours": 2
}

MONTH_NAMES = [
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december"
]


class ObligationExtractor:
    """
    NLP extraction engine for legal directives, deontic obligation types,
    and contextual deadline resolution.
    """

    def __init__(self, reference_date_str: str = "2026-07-15"):
        self.default_reference_date = reference_date_str

    def _parse_explicit_date(self, text: str) -> Optional[str]:
        """Extracts and standardizes explicit date strings to YYYY-MM-DD."""
        # Pattern 1: "December 31, 2026" or "31 December 2026"
        month_regex = r"(?:January|February|March|April|May|June|July|August|September|October|November|December)"
        match1 = re.search(
            rf'(?:no later than|before|by|with effect from|effective)\s+({month_regex}\s+\d{{1,2}},?\s*\d{{4}}|\d{{1,2}}\s+{month_regex},?\s*\d{{4}})',
            text,
            re.IGNORECASE
        )
        if match1:
            date_raw = match1.group(1).replace(",", "").strip()
            for fmt in ("%B %d %Y", "%d %B %Y"):
                try:
                    dt = datetime.strptime(date_raw, fmt)
                    return dt.strftime("%Y-%m-%d")
                except ValueError:
                    continue

        # Pattern 2: ISO dates YYYY-MM-DD
        iso_match = re.search(r'\b(20\d{2}-\d{2}-\d{2})\b', text)
        if iso_match:
            return iso_match.group(1)

        return None

    def _resolve_relative_deadline(self, text_lower: str, ref_date: datetime) -> tuple:
        """
        Calculates relative deadlines (e.g. 'within 30 days', 'forthwith').
        Returns: (deadline_str, deadline_type)
        """
        # 1. Regex for "within X days"
        days_match = re.search(r'within\s+(\d+)\s+days', text_lower)
        if days_match:
            days = int(days_match.group(1))
            calc_dt = ref_date + timedelta(days=days)
            return calc_dt.strftime("%Y-%m-%d"), "derived"

        # 2. Regex for "within X months"
        months_match = re.search(r'within\s+(\d+|one|two|three|six)\s+months', text_lower)
        if months_match:
            m_str = months_match.group(1)
            num_map = {"one": 1, "two": 2, "three": 3, "six": 6}
            num_months = num_map.get(m_str, int(m_str) if m_str.isdigit() else 3)
            calc_dt = ref_date + timedelta(days=num_months * 30)
            return calc_dt.strftime("%Y-%m-%d"), "derived"

        # 3. Standard phrase mapping
        for phrase, days in IMPLICIT_DEADLINE_MAP.items():
            if phrase in text_lower:
                calc_dt = ref_date + timedelta(days=days)
                return calc_dt.strftime("%Y-%m-%d"), "derived"

        return "None", "implicit"

    def extract_obligations(
        self,
        text: str,
        reference_date_str: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Splits text into sentences, identifies compliance obligations,
        determines deontic types, and resolves deadlines.
        """
        if not text:
            return []

        ref_str = reference_date_str or self.default_reference_date
        try:
            ref_date = datetime.strptime(ref_str, "%Y-%m-%d")
        except Exception:
            ref_date = datetime(2026, 7, 15)

        # Sentence tokenizer splitting on periods, exclamations, question marks
        sentences = re.split(r'(?<=[.!?])\s+', text)
        obligations = []

        for sentence in sentences:
            sentence_clean = sentence.strip()
            if len(sentence_clean) < 15:
                continue

            sentence_lower = sentence_clean.lower()

            # Check for obligation markers
            has_obligation = any(
                m in sentence_lower
                for m in [
                    "must", "shall", "required", "mandated", "hereby directs",
                    "shall ensure", "all banks shall", "psos shall", "establishes"
                ]
            )
            if not has_obligation:
                continue

            # Classify deontic modality
            if any(p in sentence_lower for p in ["shall not", "must not", "prohibited", "forbidden", "refrain from"]):
                obligation_type = "PROHIBITED"
            elif any(a in sentence_lower for a in ["should", "advisable", "advisory", "recommended", "encouraged"]):
                obligation_type = "ADVISORY"
            else:
                obligation_type = "REQUIRED"

            # Clean action statement: strip leading clause numbering like (a), 1., 2.1
            action = re.sub(r'^(?:(?:\([a-zA-Z0-9]+\)|\d+[\.\)]|[a-zA-Z][\.\)])\s*)+', '', sentence_clean).strip()
            if not action:
                action = sentence_clean

            # Determine deadline
            explicit_date = self._parse_explicit_date(sentence_clean)
            if explicit_date:
                deadline = explicit_date
                deadline_type = "explicit"
            else:
                deadline, deadline_type = self._resolve_relative_deadline(sentence_lower, ref_date)

            # Hallucination check: ensure source quote actually exists in original text
            quote_check = HallucinationValidator.verify_source_quote(sentence_clean, text)

            obligations.append({
                "action": action,
                "deadline": deadline,
                "deadline_type": deadline_type,
                "obligation_type": obligation_type,
                "source_sentence": sentence_clean,
                "quote_verified": quote_check["verified"],
                "quote_score": quote_check["score"]
            })

        return obligations


# Global obligation extractor instance
EXTRACTOR = ObligationExtractor()
