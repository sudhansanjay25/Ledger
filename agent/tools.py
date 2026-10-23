import re
import unicodedata
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple
from langchain_core.tools import tool

from sample_data import BENIGN_RBI_CIRCULAR, MALICIOUS_INJECTION_CIRCULAR, LOW_QUALITY_OCR_CIRCULAR
from pdf_extractor import extract_text_from_pdf
from classifier import CLASSIFIER
from extractor import EXTRACTOR
from models import MAPObject, HallucinationValidator
from amendment_detector import AMENDMENT_TRACKER
from confidence_router import ROUTER
from audit_trail import AUDIT_TRAIL
from jira_integration import JIRA
from database import SessionLocal, MAPRecordModel

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
    Supports in-memory presets as well as file-backed documents (e.g. PDFs).
    """
    global ACTIVE_DOCUMENT
    doc = MOCK_DOCUMENTS.get(document_id)
    if not doc:
        try:
            from document_store import CATALOG
            doc = CATALOG.get_document(document_id)
        except Exception:
            pass

    if not doc:
        return {"error": f"Document ID '{document_id}' not found. Available IDs: {list(MOCK_DOCUMENTS.keys())}"}
    
    raw_text = doc.get("raw_text", "")
    quality_score = doc.get("quality_score", 1.0)
    
    # If raw_text is not yet loaded but a file_path is provided, parse it
    file_path = doc.get("file_path")
    if not raw_text and file_path:
        if file_path.lower().endswith(".pdf"):
            pdf_result = extract_text_from_pdf(file_path)
            if pdf_result.get("success"):
                raw_text = pdf_result.get("text", "")
                quality_score = pdf_result.get("quality_score", 1.0)
        else:
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    raw_text = f.read()
            except Exception:
                raw_text = ""

    # Store in the global active document cache
    ACTIVE_DOCUMENT = {
        "id": doc.get("id"),
        "title": doc.get("title"),
        "source_url": doc.get("source_url", "https://rbi.org.in/uploaded-circular"),
        "format": doc.get("format", "digital_pdf"),
        "raw_text": raw_text,
        "cleaned_text": "",
        "quality_score": quality_score,
        "classification": {},
        "obligations": []
    }
    return ACTIVE_DOCUMENT

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
    affected departments, and priority level using multi-dimensional taxonomy.
    """
    global ACTIVE_DOCUMENT
    cleaned_text = ACTIVE_DOCUMENT.get("cleaned_text", "") or ACTIVE_DOCUMENT.get("raw_text", "")
    if not cleaned_text:
        return {"error": "No document content is currently available."}

    result = CLASSIFIER.classify(cleaned_text)
    ACTIVE_DOCUMENT["classification"] = result
    return result

@tool
def extract_obligations(reference_date_str: str = "2026-07-15") -> Dict[str, Any]:
    """
    Extracts compliance obligations, associated deadlines (resolving relative terms),
    and obligation types from the active document's text using NLP analysis.
    """
    global ACTIVE_DOCUMENT
    cleaned_text = ACTIVE_DOCUMENT.get("cleaned_text", "") or ACTIVE_DOCUMENT.get("raw_text", "")
    if not cleaned_text:
        return {"error": "No document content is currently available."}

    obligations = EXTRACTOR.extract_obligations(cleaned_text, reference_date_str=reference_date_str)
    ACTIVE_DOCUMENT["obligations"] = obligations
    return {"obligations": obligations}

@tool
def generate_map_objects() -> List[Dict[str, Any]]:
    """
    Formats the cached obligations and classification into strictly validated,
    auditable MAP objects with hallucination checks and amendment/supersession detection.
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
    cleaned_text = ACTIVE_DOCUMENT.get("cleaned_text", "") or ACTIVE_DOCUMENT.get("raw_text", "")

    # Detect amendment & supersession
    supersession_info = AMENDMENT_TRACKER.detect_supersession(cleaned_text, circular_id)
    has_supersession = supersession_info.get("has_supersession", False)
    explicit_refs = supersession_info.get("explicit_references", [])
    superseded_by_val = explicit_refs[0] if explicit_refs else None

    # Index active document in ChromaDB for future amendment queries
    try:
        AMENDMENT_TRACKER.index_circular(
            circular_id=circular_id,
            text=cleaned_text,
            metadata={
                "title": ACTIVE_DOCUMENT.get("title", ""),
                "category": classification.get("category", "")
            }
        )
    except Exception:
        pass

    map_objects = []

    for idx, ob in enumerate(obligations):
        action_text = ob.get("action", "").strip()
        source_sentence = ob.get("source_sentence", "").strip()

        if not action_text or not source_sentence:
            continue

        confidence = 0.95
        if ob.get("deadline") == "None":
            confidence -= 0.20
        elif ob.get("deadline_type") == "derived":
            confidence -= 0.05
        if len(action_text) < 20:
            confidence -= 0.15

        # Hallucination check
        quote_check = HallucinationValidator.verify_source_quote(source_sentence, cleaned_text)
        if not quote_check["verified"]:
            confidence -= 0.30

        try:
            map_item = MAPObject(
                action_id=f"MAP-{circular_id}-{idx+1:02d}",
                action=action_text,
                department=classification.get("departments", ["Operations"]),
                deadline=ob.get("deadline", "None"),
                deadline_type=ob.get("deadline_type", "implicit"),
                priority=classification.get("priority", "Medium"),
                obligation_type=ob.get("obligation_type", "REQUIRED"),
                source_sentence=source_sentence,
                confidence=max(0.1, confidence),
                circular_id=circular_id,
                is_superseded=has_supersession and len(explicit_refs) > 0,
                superseded_by=superseded_by_val
            )
            map_dict = map_item.model_dump()
        except Exception:
            map_dict = {
                "action_id": f"MAP-{circular_id}-{idx+1:02d}",
                "action": action_text,
                "department": classification.get("departments", ["Operations"]),
                "deadline": ob.get("deadline", "None"),
                "deadline_type": ob.get("deadline_type", "implicit"),
                "priority": classification.get("priority", "Medium"),
                "obligation_type": ob.get("obligation_type", "REQUIRED"),
                "source_sentence": source_sentence,
                "confidence": round(max(0.1, confidence), 2),
                "circular_id": circular_id,
                "is_superseded": False,
                "superseded_by": None
            }

        # 3-Tier Confidence Routing
        routing = ROUTER.evaluate_routing({
            **map_dict,
            "quote_verified": quote_check["verified"]
        })
        map_dict["status"] = routing["status"]
        map_dict["assigned_department"] = routing["assigned_department"]
        map_dict["routing_tier"] = routing["routing_tier"]
        map_dict["routing_reason"] = routing["reason"]

        # External System Hook: Mock Jira synchronization for auto-assigned MAPs
        if routing["status"] == "auto_assigned":
            try:
                jira_issue = JIRA.create_issue(
                    action_id=map_dict["action_id"],
                    summary=map_dict["action"],
                    description=f"Auto-assigned regulatory obligation from circular {circular_id}.\nSource quote: {map_dict['source_sentence']}",
                    department=routing["assigned_department"],
                    priority=map_dict["priority"],
                    due_date=map_dict["deadline"]
                )
                map_dict["jira_issue_key"] = jira_issue["key"]
            except Exception:
                map_dict["jira_issue_key"] = None
        else:
            map_dict["jira_issue_key"] = None

        # State persistence & Immutable Audit Trail
        try:
            db = SessionLocal()
            existing_rec = db.query(MAPRecordModel).filter(MAPRecordModel.action_id == map_dict["action_id"]).first()
            if existing_rec:
                existing_rec.action = map_dict["action"]
                existing_rec.department = map_dict["department"]
                existing_rec.deadline = map_dict["deadline"]
                existing_rec.priority = map_dict["priority"]
                existing_rec.status = map_dict["status"]
                existing_rec.assigned_department = map_dict["assigned_department"]
                existing_rec.jira_issue_key = map_dict.get("jira_issue_key")
            else:
                new_rec = MAPRecordModel(
                    action_id=map_dict["action_id"],
                    circular_id=circular_id,
                    action=map_dict["action"],
                    department=map_dict["department"],
                    deadline=map_dict["deadline"],
                    deadline_type=map_dict["deadline_type"],
                    priority=map_dict["priority"],
                    obligation_type=map_dict["obligation_type"],
                    source_sentence=map_dict["source_sentence"],
                    confidence=map_dict["confidence"],
                    status=map_dict["status"],
                    assigned_department=map_dict["assigned_department"],
                    jira_issue_key=map_dict.get("jira_issue_key"),
                    is_superseded=map_dict.get("is_superseded", False),
                    superseded_by=map_dict.get("superseded_by")
                )
                db.add(new_rec)
            db.commit()

            # Record creation in AuditTrail
            AUDIT_TRAIL.record_event(
                action_id=map_dict["action_id"],
                action_type="CREATED",
                actor_role="system_agent",
                actor_id="langgraph_planner",
                previous_state=None,
                new_state=map_dict,
                notes=f"Auto-generated. Routed to '{map_dict['status']}' ({routing['reason']})",
                session=db
            )
            db.close()
        except Exception:
            pass

        map_objects.append(map_dict)

    return map_objects
