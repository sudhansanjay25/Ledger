import re
from typing import Dict, Any, List
from feedback_memory import FEEDBACK_STORE


REGULATORY_TAXONOMY = {
    "Cybersecurity & Digital Payments": {
        "keywords": ["payment", "multi-factor", "authentication", "mfa", "fraud monitoring", "cybersecurity", "ciso", "cloud", "encryption", "upi", "tokenisation", "tokenization"],
        "default_departments": ["IT", "Information Security", "Operations"],
        "weight": 1.2
    },
    "Compliance & KYC / AML": {
        "keywords": ["aml", "cft", "kyc", "money laundering", "identity", "pan", "aadhaar", "beneficial ownership", "politically exposed"],
        "default_departments": ["Compliance", "Legal", "KYC Operations"],
        "weight": 1.1
    },
    "Capital Adequacy & Risk Management": {
        "keywords": ["capital adequacy", "basel", "crar", "liquidity coverage", "lcr", "stress test", "solvency", "credit risk", "counterparty"],
        "default_departments": ["Risk Management", "Finance", "Treasury"],
        "weight": 1.0
    },
    "Algorithmic Trading & Market Surveillance": {
        "keywords": ["algo", "algorithmic", "order log", "circuit breaker", "surveillance", "stock broker", "depository", "volatility"],
        "default_departments": ["Trading Operations", "Risk Management", "Compliance"],
        "weight": 1.1
    },
    "Insurance Solvency & Underwriting": {
        "keywords": ["solvency margin", "actuarial", "policyholder", "underwriting", "reinsurance", "claim settlement"],
        "default_departments": ["Actuarial", "Underwriting", "Compliance"],
        "weight": 1.0
    }
}

PENAL_INDICATORS = [
    "penalty", "monetary fine", "prosecution", "imprisonment",
    "cancellation of license", "cease and desist", "penal action", "punitive"
]

URGENCY_INDICATORS = [
    "immediately", "forthwith", "without delay", "within 24 hours", "no later than"
]


class RegulatoryClassifier:
    """
    Intelligent regulatory classifier with multi-department routing,
    enforcement severity scoring, and few-shot memory integration.
    """

    def __init__(self, feedback_store=None):
        self.feedback_store = feedback_store or FEEDBACK_STORE

    def classify(self, text: str) -> Dict[str, Any]:
        """
        Classifies regulation category, affected departments, and priority.
        """
        if not text:
            return {
                "category": "General Banking Regulations",
                "departments": ["Operations"],
                "priority": "Medium",
                "language": "English",
                "confidence": 0.5,
                "exemplars_applied": 0
            }

        text_lower = text.lower()

        # 1. Category Classification via Taxonomy Scoring
        scores = {}
        for cat, config in REGULATORY_TAXONOMY.items():
            matches = sum(1 for kw in config["keywords"] if kw in text_lower)
            scores[cat] = matches * config["weight"]

        best_category = "General Banking Regulations"
        best_score = 0.0
        if scores:
            top_category = max(scores, key=scores.get)
            if scores[top_category] > 0:
                best_category = top_category
                best_score = scores[top_category]

        # 2. Department Routing with Few-Shot Correction Integration
        departments = list(REGULATORY_TAXONOMY.get(best_category, {}).get("default_departments", ["Operations"]))

        # Query human correction exemplars
        exemplars = self.feedback_store.find_relevant_exemplars(text)
        for ex in exemplars:
            for dept in ex.get("corrected_departments", []):
                if dept not in departments:
                    departments.append(dept)

        # 3. Dynamic Priority Assessment
        has_penal = any(p in text_lower for p in PENAL_INDICATORS)
        has_urgency = any(u in text_lower for u in URGENCY_INDICATORS)

        if has_penal:
            priority = "Critical"
        elif has_urgency:
            priority = "High"
        elif "should" in text_lower or "advisory" in text_lower or "encouraged" in text_lower:
            priority = "Low"
        else:
            priority = "Medium"

        # Apply priority overrides from exemplars if critical
        for ex in exemplars:
            if ex.get("corrected_priority") == "Critical":
                priority = "Critical"

        confidence = 0.85
        if best_score >= 3.0:
            confidence = 0.95
        elif best_score == 0:
            confidence = 0.60

        return {
            "category": best_category,
            "departments": departments,
            "priority": priority,
            "language": "English",
            "confidence": round(confidence, 2),
            "exemplars_applied": len(exemplars)
        }


# Global classifier instance
CLASSIFIER = RegulatoryClassifier()
