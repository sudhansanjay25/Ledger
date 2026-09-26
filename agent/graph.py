import os
import json
from typing import Dict, Any, List, Literal
from langchain_core.messages import AIMessage, ToolMessage, HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from state import AgentState, DocumentContext, SecurityScanResult, ClassificationResult
from planner import get_real_llm_planner, mock_planner_decision, PLANNER_SYSTEM_PROMPT, ALL_TOOLS

# --- State Synchronization Helper ---
def sync_state_from_messages(state: AgentState) -> Dict[str, Any]:
    """
    Parses ToolMessages from the message history and updates the corresponding
    structured state fields (document, security_scan, classification, extracted_maps).
    This ensures that custom state variables are correctly synchronized since
    the prebuilt ToolNode only appends messages.
    """
    messages = state.get("messages", [])
    doc_update = dict(state.get("document", {}))
    sec_update = dict(state.get("security_scan", {}))
    class_update = dict(state.get("classification", {}))
    maps_update = list(state.get("extracted_maps", []))
    terminate = state.get("terminate", False)
    execution_logs = list(state.get("execution_logs", []))
    
    for msg in messages:
        if isinstance(msg, ToolMessage):
            name = msg.name
            try:
                # Add to execution logs if not already present
                log_entry = f"Executed tool '{name}'"
                if not any(name in log for log in execution_logs):
                    execution_logs.append(f"Executing tool '{name}' via LangGraph ToolNode")
                
                # Parse tool output content
                result = json.loads(msg.content) if isinstance(msg.content, str) else msg.content
                
                if name == "fetch_document":
                    if isinstance(result, dict) and "error" not in result:
                        doc_update.update({
                            "id": result.get("id", ""),
                            "title": result.get("title", ""),
                            "source_url": result.get("source_url", ""),
                            "format": result.get("format", ""),
                            "raw_text": result.get("raw_text", "")
                        })
                elif name == "security_scan":
                    if isinstance(result, dict):
                        sec_update.update({
                            "is_safe": result.get("is_safe", False),
                            "threat_detected": result.get("threat_detected"),
                            "details": result.get("details", ""),
                            "logs": result.get("logs", [])
                        })
                        if not result.get("is_safe", False):
                            terminate = True # Terminate pipeline immediately on security threat
                elif name == "extract_text":
                    if isinstance(result, dict):
                        doc_update.update({
                            "cleaned_text": result.get("cleaned_text", ""),
                            "quality_score": result.get("quality_score", 1.0)
                        })
                elif name == "classify_document":
                    if isinstance(result, dict):
                        class_update.update({
                            "category": result.get("category", ""),
                            "departments": result.get("departments", []),
                            "priority": result.get("priority", ""),
                            "language": result.get("language", "English")
                        })
                elif name == "generate_map_objects":
                    if isinstance(result, list):
                        maps_update = result
                        
            except Exception:
                pass
                
    return {
        "document": doc_update,
        "security_scan": sec_update,
        "classification": class_update,
        "extracted_maps": maps_update,
        "terminate": terminate,
        "execution_logs": execution_logs
    }

# --- Node 1: The Planner Node ---
def planner_node(state: AgentState) -> Dict[str, Any]:
    """
    Executes the planner agent.
    First, synchronizes messages into custom state variables.
    Then, calls either the real Groq LLM or the mock planner decision handler.
    """
    # Sync messages to structured state variables first
    updates = sync_state_from_messages(state)
    
    # If security check has already failed and set terminate=True, halt immediately
    if updates.get("terminate", False):
        return updates
        
    # Merge updates into local state so planner sees the latest values
    temp_state = {**state, **updates}
    
    real_llm = get_real_llm_planner()
    
    # Check if user forced mock planner or if real LLM is available
    use_mock = os.environ.get("USE_MOCK_PLANNER", "").lower() in ("1", "true", "yes")
    
    if real_llm and not use_mock:
        try:
            messages = temp_state.get("messages", [])
            if not messages or not isinstance(messages[0], SystemMessage):
                messages = [SystemMessage(content=PLANNER_SYSTEM_PROMPT)] + messages
                
            # Call Groq LLM with tools bound
            response = real_llm.invoke(messages)
            if not response.content and not getattr(response, "tool_calls", None):
                response = mock_planner_decision(temp_state)
            updates["messages"] = [response]
        except Exception as exc:
            # Resilient fallback to deterministic rule planner if Groq encounters rate-limits/tool-arg parsing issues
            updates["execution_logs"].append(f"LLM planner warning: {str(exc)[:80]}... Falling back to rule planner.")
            response = mock_planner_decision(temp_state)
            updates["messages"] = [response]
    else:
        # Fallback to local rule-based planner
        response = mock_planner_decision(temp_state)
        updates["messages"] = [response]
        
    return updates

# --- Node 2: Routing Logic ---
def should_continue(state: AgentState) -> Literal["tools", "__end__"]:
    """
    Decides whether to route to the prebuilt ToolNode or terminate.
    """
    if state.get("terminate", False):
        return "__end__"
        
    messages = state.get("messages", [])
    if not messages:
        return "__end__"
        
    last_message = messages[-1]
    
    # If the last message contains tool calls, execute them
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "tools"
        
    return "__end__"

# --- Assemble the LangGraph ---
def build_agent_graph():
    """Assembles the state graph workflow using prebuilt ToolNode."""
    workflow = StateGraph(AgentState)
    
    # Register planner node and prebuilt ToolNode
    workflow.add_node("planner", planner_node)
    workflow.add_node("tools", ToolNode(ALL_TOOLS))
    
    # Set the starting node
    workflow.set_entry_point("planner")
    
    # Add conditional router edge from planner
    workflow.add_conditional_edges(
        "planner",
        should_continue,
        {
            "tools": "tools",
            "__end__": END
        }
    )
    
    # Add edge from tools back to planner
    workflow.add_edge("tools", "planner")
    
    # Compile the graph
    return workflow.compile()
