import os
import sys
import json
import time
import uuid
import queue
import threading
from datetime import datetime
from flask import Flask, request, Response, jsonify
from flask_cors import CORS

# Add agent directory to sys.path so we can import agent modules
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
AGENT_DIR = os.path.join(PROJECT_ROOT, "agent")
if AGENT_DIR not in sys.path:
    sys.path.insert(0, AGENT_DIR)

from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
from graph import build_agent_graph
from sample_data import BENIGN_RBI_CIRCULAR, MALICIOUS_INJECTION_CIRCULAR, LOW_QUALITY_OCR_CIRCULAR
from tools import MOCK_DOCUMENTS
from pdf_extractor import extract_text_from_pdf, compute_text_quality, validate_pdf_bytes
from html_extractor import extract_text_from_html
from security_validator import validate_document_safety, calculate_sha256
from document_store import CATALOG
from scheduler import CRAWLER_SCHEDULER
from review_routes import review_bp
from metrics_routes import metrics_bp

# Register workspace Ledger.pdf if present
LEDGER_PDF_PATH = os.path.join(PROJECT_ROOT, "Ledger.pdf")
if os.path.exists(LEDGER_PDF_PATH):
    MOCK_DOCUMENTS["ledger_pdf_official"] = {
        "id": "ledger_pdf_official",
        "title": "Ledger (EnigmaGov) - Official Autonomous Regulatory Compliance Brief",
        "source_url": "https://rbi.org.in/guidelines/cybersecurity-brief",
        "format": "digital_pdf",
        "file_path": LEDGER_PDF_PATH,
        "raw_text": ""
    }
    try:
        with open(LEDGER_PDF_PATH, "rb") as f:
            pdf_bytes = f.read()
        pdf_res = extract_text_from_pdf(pdf_bytes)
        if pdf_res.get("success"):
            CATALOG.register_document(
                raw_text=pdf_res["text"],
                title="Ledger (EnigmaGov) - Official Autonomous Regulatory Compliance Brief",
                source_url="https://rbi.org.in/guidelines/cybersecurity-brief",
                format_type="digital_pdf",
                regulator="RBI",
                custom_id="ledger_pdf_official",
                quality_score=pdf_res["quality_score"]
            )
    except Exception:
        pass

app = Flask(__name__)
# Enable CORS for Next.js frontend (default http://localhost:3000)
CORS(app, resources={r"/*": {"origins": "*"}})
app.register_blueprint(review_bp)
app.register_blueprint(metrics_bp)

# In-memory store for agent sessions
# session_id -> { "queue": Queue, "state": dict, "events": list, "status": str, "created_at": str }
SESSIONS = {}

def serialize_message(msg):
    """Safely serializes a LangChain message object to a JSON-compatible dict."""
    if isinstance(msg, AIMessage):
        role = "assistant"
    elif isinstance(msg, ToolMessage):
        role = "tool"
    elif isinstance(msg, SystemMessage):
        role = "system"
    elif isinstance(msg, HumanMessage):
        role = "user"
    else:
        role = getattr(msg, "type", "unknown")

    tool_calls = getattr(msg, "tool_calls", None)
    serialized_tool_calls = []
    if tool_calls:
        for tc in tool_calls:
            serialized_tool_calls.append({
                "name": tc.get("name"),
                "args": tc.get("args"),
                "id": tc.get("id")
            })

    name = getattr(msg, "name", None)
    
    # Try parsing ToolMessage content if JSON string
    content = msg.content
    content_parsed = None
    if isinstance(content, str):
        try:
            content_parsed = json.loads(content)
        except Exception:
            pass

    return {
        "role": role,
        "name": name,
        "content": content,
        "content_parsed": content_parsed,
        "tool_calls": serialized_tool_calls
    }

def serialize_state(state):
    """Converts the internal AgentState into a clean, JSON-serializable dictionary."""
    if not isinstance(state, dict):
        return {}

    serialized_messages = []
    for m in state.get("messages", []):
        try:
            serialized_messages.append(serialize_message(m))
        except Exception as e:
            serialized_messages.append({"role": "unknown", "content": str(m)})

    return {
        "document": state.get("document", {}),
        "security_scan": state.get("security_scan", {}),
        "classification": state.get("classification", {}),
        "extracted_maps": state.get("extracted_maps", []),
        "execution_logs": list(state.get("execution_logs", [])),
        "terminate": state.get("terminate", False),
        "messages": serialized_messages
    }

def run_agent_workflow(session_id, document_id, custom_title=None, custom_text=None):
    """
    Background worker that runs the LangGraph agent workflow and emits
    Server-Sent Events (SSE) into the session queue.
    """
    session = SESSIONS.get(session_id)
    if not session:
        return

    q = session["queue"]

    try:
        # If custom document was provided, register it in MOCK_DOCUMENTS
        if custom_text:
            actual_doc_id = document_id or f"custom_{session_id[:8]}"
            MOCK_DOCUMENTS[actual_doc_id] = {
                "id": actual_doc_id,
                "title": custom_title or "Custom Regulatory Notice",
                "source_url": "https://rbi.org.in/custom-upload",
                "format": "digital_pdf",
                "raw_text": custom_text
            }
            target_id = actual_doc_id
        else:
            target_id = document_id

        # Initial event: Start
        start_event = {
            "type": "agent_start",
            "session_id": session_id,
            "document_id": target_id,
            "timestamp": datetime.now().isoformat(),
            "message": f"Agent initialized. Loading state graph for document '{target_id}'..."
        }
        session["events"].append(start_event)
        q.put(start_event)

        # Build the LangGraph
        graph_app = build_agent_graph()

        initial_state = {
            "messages": [HumanMessage(content=f"Please ingest and process document {target_id}.")],
            "document": {},
            "security_scan": {},
            "classification": {},
            "extracted_maps": [],
            "execution_logs": [],
            "terminate": False
        }

        # Keep track of aggregated state
        current_aggregated_state = dict(initial_state)

        step_counter = 0

        # Stream chunk updates from LangGraph
        for chunk in graph_app.stream(initial_state, stream_mode="updates"):
            step_counter += 1
            for node_name, updates in chunk.items():
                # Merge updates into current aggregated state
                for k, v in updates.items():
                    if k == "messages":
                        current_aggregated_state["messages"] = current_aggregated_state.get("messages", []) + v
                    elif k in ("document", "security_scan", "classification"):
                        merged = dict(current_aggregated_state.get(k, {}))
                        merged.update(v)
                        current_aggregated_state[k] = merged
                    elif k == "execution_logs":
                        current_aggregated_state["execution_logs"] = list(set(current_aggregated_state.get("execution_logs", []) + v))
                    elif k == "extracted_maps":
                        if v:
                            current_aggregated_state["extracted_maps"] = v
                    elif k == "terminate":
                        current_aggregated_state["terminate"] = v

                # Determine active activity description
                activity = f"Executed node: {node_name}"
                if node_name == "planner":
                    if updates.get("terminate"):
                        activity = "Planner detected termination condition and halted workflow."
                    elif updates.get("messages"):
                        last_m = updates["messages"][-1]
                        if getattr(last_m, "tool_calls", None):
                            tools_called = [t.get("name") for t in last_m.tool_calls]
                            activity = f"Planner reasoned and requested tool(s): {', '.join(tools_called)}"
                        else:
                            activity = "Planner produced final summary response."
                elif node_name == "tools":
                    tool_names = []
                    for m in updates.get("messages", []):
                        if isinstance(m, ToolMessage):
                            tool_names.append(m.name)
                    activity = f"Tools completed: {', '.join(tool_names) if tool_names else 'Tool Node'}"

                snapshot = serialize_state(current_aggregated_state)
                session["state"] = snapshot

                event = {
                    "type": "step_update",
                    "step": step_counter,
                    "node": node_name,
                    "activity": activity,
                    "timestamp": datetime.now().isoformat(),
                    "state": snapshot
                }
                session["events"].append(event)
                q.put(event)

                # Tiny pacing delay to provide smooth UI streaming visualization
                time.sleep(0.35)

        # Final completion event
        final_snapshot = serialize_state(current_aggregated_state)
        session["state"] = final_snapshot
        session["status"] = "completed"

        # Determine overall outcome status
        outcome = "SUCCESS"
        if final_snapshot.get("security_scan", {}).get("is_safe") is False:
            outcome = "THREAT_BLOCKED"
        elif final_snapshot.get("document", {}).get("quality_score", 1.0) < 0.5:
            outcome = "QUALITY_WARNING"

        completion_event = {
            "type": "agent_complete",
            "outcome": outcome,
            "timestamp": datetime.now().isoformat(),
            "total_steps": step_counter,
            "final_state": final_snapshot
        }
        session["events"].append(completion_event)
        q.put(completion_event)

    except Exception as exc:
        error_event = {
            "type": "agent_error",
            "error": str(exc),
            "timestamp": datetime.now().isoformat()
        }
        session["status"] = "error"
        session["events"].append(error_event)
        q.put(error_event)
    finally:
        # Sentinel to signal end of stream
        q.put({"type": "stream_end"})

@app.route("/health", methods=["GET"])
@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status": "healthy",
        "service": "Ledger Agent API",
        "timestamp": datetime.now().isoformat()
    })

@app.route("/api/documents", methods=["GET"])
def list_documents():
    """Returns available sample and ingested regulatory documents."""
    docs = [
        {
            "id": "rbi_2026_payment_sec_01",
            "title": BENIGN_RBI_CIRCULAR["title"],
            "category": "Digital Payments & Cybersecurity",
            "type": "Benign Regulatory Direction",
            "description": "Master Direction on MFA, fraud monitoring, and immutable audit logs. Ideal for demonstrating compliance extraction.",
            "source_url": BENIGN_RBI_CIRCULAR["source_url"],
            "format": BENIGN_RBI_CIRCULAR["format"],
            "expected_outcome": "Extraction of 7 Measurable Action Points (MAPs)"
        },
        {
            "id": "malicious_spoof_01",
            "title": MALICIOUS_INJECTION_CIRCULAR["title"],
            "category": "Adversarial Attack Simulation",
            "type": "Prompt Injection Exploit",
            "description": "Adversarial document containing system override commands attempting to divert treasury funds.",
            "source_url": MALICIOUS_INJECTION_CIRCULAR["source_url"],
            "format": MALICIOUS_INJECTION_CIRCULAR["format"],
            "expected_outcome": "Immediate Security Scan Halt (Threat Flagged)"
        },
        {
            "id": "rbi_2026_low_ocr_02",
            "title": LOW_QUALITY_OCR_CIRCULAR["title"],
            "category": "Data Quality Guardrail",
            "type": "Degraded OCR Scan",
            "description": "Low-quality OCR scanned document with corrupted text and missing pages below readability thresholds.",
            "source_url": LOW_QUALITY_OCR_CIRCULAR["source_url"],
            "format": LOW_QUALITY_OCR_CIRCULAR["format"],
            "expected_outcome": "Text Quality Score Alert (< 0.5) & Routing to Review"
        }
    ]

    existing_ids = {d["id"] for d in docs}

    # Include workspace official PDF if registered
    if "ledger_pdf_official" in MOCK_DOCUMENTS and "ledger_pdf_official" not in existing_ids:
        docs.append({
            "id": "ledger_pdf_official",
            "title": "Ledger (EnigmaGov) - Official Regulatory Specification PDF",
            "category": "Real PDF Ingestion",
            "type": "Production PDF Circular",
            "description": "The real Ledger.pdf document from project root. Tests live multi-page PDF parsing, security checks, and MAP extraction.",
            "source_url": "https://rbi.org.in/guidelines/cybersecurity-brief",
            "format": "digital_pdf",
            "expected_outcome": "Multi-page PDF extraction and compliance structuring"
        })
        existing_ids.add("ledger_pdf_official")

    # Include all documents dynamically tracked in CATALOG
    for cat_doc in CATALOG.list_documents():
        doc_id = cat_doc["id"]
        if doc_id not in existing_ids:
            regulator = cat_doc.get("regulator", "Regulatory")
            word_count = len(cat_doc.get("raw_text", "").split())
            docs.append({
                "id": doc_id,
                "title": cat_doc.get("title", "Regulatory Circular"),
                "category": f"{regulator} Directives",
                "type": f"{regulator} Live Ingested Circular",
                "description": f"Published: {cat_doc.get('published_date', 'N/A')} · {word_count} words · SHA-256: {cat_doc.get('sha256', '')[:10]}...",
                "source_url": cat_doc.get("source_url", "https://rbi.org.in"),
                "format": cat_doc.get("format", "digital_pdf"),
                "expected_outcome": "Automated compliance extraction and MAP generation"
            })
            existing_ids.add(doc_id)

    # Include any dynamically uploaded documents from MOCK_DOCUMENTS
    for doc_id, doc in MOCK_DOCUMENTS.items():
        if doc_id not in existing_ids and doc_id.startswith("upload_"):
            word_count = len(doc.get("raw_text", "").split())
            docs.append({
                "id": doc_id,
                "title": doc.get("title", "Uploaded Document"),
                "category": "User Uploaded File",
                "type": f"Uploaded {doc.get('format', 'Document').replace('_', ' ').title()}",
                "description": f"Uploaded document ({word_count} words, quality {doc.get('quality_score', 1.0)}).",
                "source_url": doc.get("source_url", "https://rbi.org.in/uploaded-circular"),
                "format": doc.get("format", "digital_pdf"),
                "expected_outcome": "Pipeline ingestion and MAP structuring"
            })
            existing_ids.add(doc_id)

    return jsonify({"documents": docs})

@app.route("/api/documents/upload", methods=["POST"])
def upload_document():
    """
    Accepts a real PDF, HTML, or TXT file upload.
    Validates file magic bytes (preventing extension spoofing),
    extracts text, computes readability metrics, and registers with SHA-256 deduplication.
    """
    if "file" not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    uploaded_file = request.files["file"]
    if uploaded_file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    filename = uploaded_file.filename
    title = request.form.get("title") or filename.replace("_", " ").rsplit(".", 1)[0]
    file_bytes = uploaded_file.read()

    # 1. Pre-ingestion magic byte validation
    safety = validate_document_safety(file_bytes, filename=filename)
    if not safety["is_safe_format"]:
        return jsonify({
            "error": safety["error"] or "File failed format safety checks."
        }), 400

    detected_format = safety["format"]
    page_count = 1

    # 2. Extract text by format
    if detected_format == "pdf":
        result = extract_text_from_pdf(file_bytes)
        if not result.get("success"):
            return jsonify({"error": result.get("error", "Failed to parse PDF document")}), 400

        raw_text = result["text"]
        quality_score = result["quality_score"]
        is_readable = result["is_readable"]
        page_count = result["page_count"]
        total_words = result["total_words"]
        format_type = "digital_pdf"
    elif detected_format == "html":
        result = extract_text_from_html(file_bytes)
        if not result.get("success"):
            return jsonify({"error": result.get("error", "Failed to parse HTML document")}), 400

        raw_text = result["text"]
        quality_score = result["quality_score"]
        is_readable = result["is_readable"]
        total_words = result["total_words"]
        format_type = "html"
        if result.get("title"):
            title = result["title"]
    else:
        # Plain text
        try:
            raw_text = file_bytes.decode("utf-8")
        except Exception:
            raw_text = file_bytes.decode("latin-1", errors="ignore")

        metrics = compute_text_quality(raw_text)
        quality_score = metrics["quality_score"]
        is_readable = metrics["is_readable"]
        total_words = metrics["total_words"]
        format_type = "plain_text"

    # 3. Register in DocumentStore with SHA-256 deduplication
    doc_entry = CATALOG.register_document(
        raw_text=raw_text,
        title=title,
        source_url="https://rbi.org.in/uploaded-circular",
        format_type=format_type,
        regulator="Uploaded",
        quality_score=quality_score,
        is_readable=is_readable,
        metadata={
            "page_count": page_count,
            "total_words": total_words,
            "filename": filename
        }
    )

    # Sync with tools.MOCK_DOCUMENTS
    MOCK_DOCUMENTS[doc_entry["id"]] = doc_entry

    return jsonify({
        "status": "success",
        "document_id": doc_entry["id"],
        "title": doc_entry["title"],
        "format": doc_entry["format"],
        "sha256": doc_entry["sha256"],
        "is_duplicate": doc_entry.get("is_duplicate", False),
        "page_count": page_count,
        "total_words": total_words,
        "quality_score": quality_score,
        "is_readable": is_readable,
        "sample_preview": raw_text[:300] + ("..." if len(raw_text) > 300 else "")
    })

@app.route("/api/crawler/trigger", methods=["POST"])
def trigger_crawler():
    """Triggers an on-demand crawl across regulatory portals (RBI, SEBI, IRDAI, NPCI)."""
    summary = CRAWLER_SCHEDULER.trigger_now()
    return jsonify({
        "status": "success",
        "summary": summary
    })

@app.route("/api/crawler/status", methods=["GET"])
def crawler_status():
    """Returns scheduler state, intervals, and crawl execution history."""
    return jsonify(CRAWLER_SCHEDULER.get_status())

@app.route("/api/agent/run", methods=["POST"])
def run_agent():
    """
    Initiates an agent run in a background thread and returns the session_id
    to connect to the SSE stream.
    """
    data = request.get_json(force=True, silent=True) or {}
    document_id = data.get("document_id", "rbi_2026_payment_sec_01")
    custom_title = data.get("custom_title")
    custom_text = data.get("custom_text")

    session_id = str(uuid.uuid4())
    session_queue = queue.Queue()

    SESSIONS[session_id] = {
        "id": session_id,
        "queue": session_queue,
        "events": [],
        "state": {},
        "status": "running",
        "created_at": datetime.now().isoformat()
    }

    # Start background execution thread
    thread = threading.Thread(
        target=run_agent_workflow,
        args=(session_id, document_id, custom_title, custom_text),
        daemon=True
    )
    thread.start()

    return jsonify({
        "session_id": session_id,
        "status": "started",
        "stream_url": f"/api/agent/stream/{session_id}"
    })

@app.route("/api/agent/stream/<session_id>", methods=["GET"])
def stream_agent(session_id):
    """
    Server-Sent Events (SSE) endpoint to stream agent updates in real-time.
    """
    session = SESSIONS.get(session_id)
    if not session:
        return jsonify({"error": f"Session '{session_id}' not found"}), 404

    q = session["queue"]

    def event_generator():
        # First, yield any events that occurred before the client connected
        # (prevents missing events due to network timing)
        for prev_event in list(session.get("events", [])):
            yield f"data: {json.dumps(prev_event)}\n\n"

        # Now stream new events from the queue
        while True:
            try:
                event = q.get(timeout=25)
                if event.get("type") == "stream_end":
                    yield f"data: {json.dumps({'type': 'stream_end'})}\n\n"
                    break
                
                # Check if this event was already delivered in the replay
                if event not in session.get("events", [])[:-1]:
                    yield f"data: {json.dumps(event)}\n\n"

                if event.get("type") in ("agent_complete", "agent_error"):
                    # Give one small beat before ending stream
                    time.sleep(0.1)
                    break
            except queue.Empty:
                # Keep-alive heartbeat comment
                yield ": keep-alive\n\n"

    response = Response(event_generator(), mimetype="text/event-stream")
    response.headers["Cache-Control"] = "no-cache"
    response.headers["X-Accel-Buffering"] = "no"
    response.headers["Connection"] = "keep-alive"
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response

@app.route("/api/agent/status/<session_id>", methods=["GET"])
def get_session_status(session_id):
    """Allows checking snapshot status of a session."""
    session = SESSIONS.get(session_id)
    if not session:
        return jsonify({"error": f"Session '{session_id}' not found"}), 404

    return jsonify({
        "session_id": session_id,
        "status": session.get("status"),
        "created_at": session.get("created_at"),
        "state": session.get("state", {}),
        "events_count": len(session.get("events", []))
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"Starting Ledger Flask API on port {port}...")
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
