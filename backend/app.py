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

app = Flask(__name__)
# Enable CORS for Next.js frontend (default http://localhost:3000)
CORS(app, resources={r"/*": {"origins": "*"}})

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
    """Returns available sample regulatory documents."""
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
    return jsonify({"documents": docs})

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
