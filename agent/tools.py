import re
import unicodedata
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple
from langchain_core.tools import tool

from sample_data import BENIGN_RBI_CIRCULAR, MALICIOUS_INJECTION_CIRCULAR, LOW_QUALITY_OCR_CIRCULAR

# Helper dictionary for document lookup
MOCK_DOCUMENTS = {
    "rbi_2026_payment_sec_01": BENIGN_RBI_CIRCULAR,
    "malicious_spoof_01": MALICIOUS_INJECTION_CIRCULAR,
    "rbi_2026_low_ocr_02": LOW_QUALITY_OCR_CIRCULAR
}

# Module-level state to store the currently active document
ACTIVE_DOCUMENT: Dict[str, Any] = {}

@tool
def fetch_document(document_id: str) -> Dict[str, Any]:
    """
    Fetches a regulatory document's raw data and metadata by its document ID for testing.
    Caches it internally so downstream tools do not require passing the full text.
    """
    global ACTIVE_DOCUMENT
    doc = MOCK_DOCUMENTS.get(document_id)
    if not doc:
        return {"error": f"Document ID '{document_id}' not found. Available IDs: {list(MOCK_DOCUMENTS.keys())}"}
    
    # Store in the global active document cache
    ACTIVE_DOCUMENT = {
        "id": doc.get("id"),
        "title": doc.get("title"),
        "source_url": doc.get("source_url"),
        "format": doc.get("format"),
        "raw_text": doc.get("raw_text"),
        "cleaned_text": "",
        "quality_score": 1.0,
        "classification": {},
        "obligations": []
    }
    return doc

@tool
def security_scan(source_url: str = "", format_type: str = "") -> Dict[str, Any]:
    """
    Runs multi-layered security checks on the currently active document content.
    Checks for trusted domains, unicode homoglyph attacks, RTL overrides, and prompt injections.
    """
    global ACTIVE_DOCUMENT
    raw_text = ACTIVE_DOCUMENT.get("raw_text", "")
    doc_url = source_url or ACTIVE_DOCUMENT.get("source_url", "")
    
    logs = []
    
    if not raw_text:
        return {"is_safe": False, "threat_detected": "No Document", "details": "No document is currently active.", "logs": ["Failed: raw_text empty"]}

    # 1. Source Domain Verification
    parsed_domain = re.search(r'https?://([^/]+)', doc_url)
    domain = parsed_domain.group(1) if parsed_domain else ""
    trusted_domains = ["rbi.org.in", "sebi.gov.in", "irdai.gov.in", "npci.org.in"]
    is_domain_trusted = any(domain == td or domain.endswith("." + td) for td in trusted_domains)
    
    if not is_domain_trusted:
        logs.append(f"Domain verification FAILED: '{domain}' is not in the trusted whitelist.")
        return {
            "is_safe": False,
            "threat_detected": "Untrusted Source Domain",
            "details": f"The document was downloaded from '{domain}' which is not a trusted regulator portal.",
            "logs": logs
        }
    logs.append("Domain verification passed.")

    # 2. Unicode Normalization & Homoglyph Detection
    normalized_text = unicodedata.normalize("NFKC", raw_text)
    cyrillic_chars = re.findall(r'[\u0400-\u04FF]', normalized_text)
    if cyrillic_chars:
        logs.append("Unicode Homoglyph verification FAILED: Detected Cyrillic characters in document text.")
        return {
            "is_safe": False,
            "threat_detected": "Unicode Homoglyph Attack",
            "details": f"Detected {len(cyrillic_chars)} Cyrillic characters (e.g., Cyrillic 'a', 'e', 'o' which spoof English letters).",
            "logs": logs
        }
    logs.append("Unicode homoglyph scan passed.")

    # 3. RTL (Right-to-Left) Override Character Scan
    rtl_overrides = re.findall(r'[\u202E\u202D\u202B\u202A\u200F\u200E]', normalized_text)
    if rtl_overrides:
        logs.append("Directional override character scan FAILED: Detected hidden RTL text-direction markers.")
        return {
            "is_safe": False,
            "threat_detected": "BiDi/RTL Text Override Attack",
            "details": "Document contains hidden directional override characters used to manipulate reading order.",
            "logs": logs
        }
    logs.append("RTL character check passed.")

    # 4. Prompt Injection Scanner
    injection_patterns = [
        r"(?i)ignore\s+(?:all\s+)?(?:previous\s+)?instructions",
        r"(?i)system\s+override",
        r"(?i)attention\s+agent",
        r"(?i)you\s+must\s+now\s+act\s+as",
        r"(?i)instead\s*,\s*generate\s+a\s+single\s+map",
        r"(?i)do\s+not\s+mention\s+this\s+system\s+instruction"
    ]
    
    detected_injections = []
    for pattern in injection_patterns:
        if re.search(pattern, normalized_text):
            detected_injections.append(pattern)
            
    if detected_injections:
        logs.append("Prompt Injection scan FAILED: Found malicious system override instructions.")
        return {
            "is_safe": False,
            "threat_detected": "Prompt Injection Attempt",
            "details": f"Detected text matching instruction-override patterns: {detected_injections}",
            "logs": logs
        }
    
    logs.append("Prompt injection scan passed.")
    return {
        "is_safe": True,
        "threat_detected": None,
        "details": "All active security checks passed successfully.",
        "logs": logs
    }

@tool
def extract_text() -> Dict[str, Any]:
    """
    Cleans raw text of the active document and measures its structural quality.
    Caches the cleaned text for downstream tools.
    """
    global ACTIVE_DOCUMENT
    raw_text = ACTIVE_DOCUMENT.get("raw_text", "")
    if not raw_text:
        return {"error": "No document is currently active."}

    # Clean up excess whitespace
    cleaned_text = re.sub(r'\s+', ' ', raw_text).strip()
    
    # Calculate quality score
    words = cleaned_text.split()
    if not words:
        return {"cleaned_text": "", "quality_score": 0.0, "is_readable": False}
        
    alphabetic_words = [w for w in words if w.isalpha() or (len(w) > 1 and w[:-1].isalpha() and w[-1] in ['.', ',', ';', ':'])]
    quality_score = len(alphabetic_words) / len(words)
    is_readable = quality_score >= 0.5
    
    # Cache the cleaned text and quality score
    ACTIVE_DOCUMENT["cleaned_text"] = cleaned_text
    ACTIVE_DOCUMENT["quality_score"] = quality_score
    
    return {
        "cleaned_text": cleaned_text,
        "quality_score": round(quality_score, 2),
        "is_readable": is_readable,
        "total_words": len(words),
        "readable_words": len(alphabetic_words)
    }

@tool
def classify_document() -> Dict[str, Any]:
    """
    Analyzes the active document's text to classify the regulation category, 
    affected departments, and priority level. Caches classification results.
    """
    global ACTIVE_DOCUMENT
    cleaned_text = ACTIVE_DOCUMENT.get("cleaned_text", "") or ACTIVE_DOCUMENT.get("raw_text", "")
    if not cleaned_text:
        return {"error": "No document content is currently available."}

    text_lower = cleaned_text.lower()
    
    # 1. Regulation Category
    category = "General Banking Regulations"
    if any(k in text_lower for k in ["payment", "online transaction", "multi-factor", "authentication", "mfa"]):
        category = "Cybersecurity & Digital Payments"
    elif any(k in text_lower for k in ["aml", "kyc", "money laundering", "identity", "pan", "aadhaar"]):
        category = "Compliance & KYC"
    elif any(k in text_lower for k in ["capital", "basel", "liquidity", "solvency"]):
        category = "Capital Adequacy & Risk"

    # 2. Affected Departments
    departments = ["Operations"]
    if category == "Cybersecurity & Digital Payments":
        departments = ["IT", "Information Security", "Operations"]
    elif category == "Compliance & KYC":
        departments = ["Compliance", "Legal", "KYC Operations"]
    elif category == "Capital Adequacy & Risk":
        departments = ["Risk Management", "Finance", "Treasury"]

    # 3. Priority Level
    priority = "Medium"
    if any(k in text_lower for k in ["penalty", "fine", "imprisonment", "prosecution", "monetary fines"]):
        priority = "Critical"
    elif any(k in text_lower for k in ["immediately", "forthwith", "no later than"]):
        priority = "High"
    elif "should" in text_lower or "advisory" in text_lower:
        priority = "Low"

    result = {
        "category": category,
        "departments": departments,
        "priority": priority,
        "language": "English"
    }
    
    # Cache classification result
    ACTIVE_DOCUMENT["classification"] = result
    return result

# Helper mapping for implicit deadline resolution
IMPLICIT_DEADLINES = {
    "immediately": 7,
    "forthwith": 3,
    "promptly": 14,
    "without delay": 7,
    "at the earliest": 7,
    "as soon as possible": 14
}

@tool
def extract_obligations(reference_date_str: str = "2026-07-15") -> Dict[str, Any]:
    """
    Extracts compliance obligations, associated deadlines (resolving relative terms),
    and obligation types from the active document's text. Caches extracted obligations.
    """
    global ACTIVE_DOCUMENT
    cleaned_text = ACTIVE_DOCUMENT.get("cleaned_text", "") or ACTIVE_DOCUMENT.get("raw_text", "")
    if not cleaned_text:
        return {"error": "No document content is currently available."}

    reference_date = datetime.strptime(reference_date_str, "%Y-%m-%d")
    obligations = []
    
    sentences = re.split(r'(?<=[.!?])\s+', cleaned_text)
    
    for sentence in sentences:
        sentence_lower = sentence.lower()
        if not any(v in sentence_lower for v in ["must", "shall", "required", "mandated", "hereby directs", "establishes"]):
            continue
            
        obligation_type = "REQUIRED"
        if any(p in sentence_lower for p in ["prohibited", "shall not", "must not", "forbidden"]):
            obligation_type = "PROHIBITED"
        elif any(a in sentence_lower for a in ["should", "advisable", "advisory", "recommended"]):
            obligation_type = "ADVISORY"
            
        action = sentence.strip()
        action = re.sub(r'^(?:(?:\([a-zA-Z0-9]+\)|\d+[\.\)]|[a-zA-Z][\.\)])\s*)+', '', action).strip()
        if not action:
            action = sentence.strip()
        
        deadline = "None"
        deadline_type = "implicit"
        
        # 1. Explicit dates
        date_match = re.search(
            r'(?:no later than|before|by)\s+([A-Z][a-z]+ \d{1,2},\s*\d{4}|\d{1,2} [A-Z][a-z]+,\s*\d{4})',
            sentence
        )
        if date_match:
            try:
                date_str = date_match.group(1).replace(",", "")
                for fmt in ("%B %d %Y", "%d %B %Y"):
                    try:
                        parsed_date = datetime.strptime(date_str, fmt)
                        deadline = parsed_date.strftime("%Y-%m-%d")
                        deadline_type = "explicit"
                        break
                    except ValueError:
                        continue
            except Exception:
                pass
                
        # 2. Implicit deadlines
        if deadline == "None":
            for phrase, days in IMPLICIT_DEADLINES.items():
                if phrase in sentence_lower:
                    calculated_date = reference_date + timedelta(days=days)
                    deadline = calculated_date.strftime("%Y-%m-%d")
                    deadline_type = "derived"
                    break
                    
        obligations.append({
            "action": action,
            "deadline": deadline,
            "deadline_type": deadline_type,
            "obligation_type": obligation_type,
            "source_sentence": sentence.strip()
        })
        
    # Cache obligations list
    ACTIVE_DOCUMENT["obligations"] = obligations
    return {"obligations": obligations}

@tool
def generate_map_objects() -> List[Dict[str, Any]]:
    """
    Formats the cached obligations and classification into structured MAP objects.
    Retrieves all required context from the internal document cache.
    """
    global ACTIVE_DOCUMENT
    obligations = ACTIVE_DOCUMENT.get("obligations", [])
    if not obligations:
        extract_result = extract_obligations.invoke({"reference_date_str": "2026-07-15"})
        if isinstance(extract_result, dict):
            obligations = extract_result.get("obligations", [])
    classification = ACTIVE_DOCUMENT.get("classification", {
        "category": "General Banking Regulations",
        "departments": ["Operations"],
        "priority": "Medium"
    })
    circular_id = ACTIVE_DOCUMENT.get("id", "unknown")
    
    map_objects = []
    
    for idx, ob in enumerate(obligations):
        confidence = 0.95
        if ob["deadline"] == "None":
            confidence -= 0.20
        elif ob["deadline_type"] == "derived":
            confidence -= 0.05
        if len(ob["action"]) < 20:
            confidence -= 0.15
            
        if not ob["action"] or not ob["source_sentence"]:
            continue
            
        map_objects.append({
            "action_id": f"MAP-{circular_id}-{idx+1:02d}",
            "action": ob["action"],
            "department": classification.get("departments", ["Operations"]),
            "deadline": ob["deadline"],
            "deadline_type": ob["deadline_type"],
            "priority": classification.get("priority", "Medium"),
            "obligation_type": ob["obligation_type"],
            "source_sentence": ob["source_sentence"],
            "confidence": round(max(0.1, confidence), 2),
            "circular_id": circular_id
        })
        
    return map_objects
