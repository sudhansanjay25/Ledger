from typing import TypedDict, List, Dict, Any, Annotated
from langgraph.graph.message import add_messages

class DocumentContext(TypedDict, total=False):
    id: str
    title: str
    source_url: str
    format: str
    raw_text: str
    cleaned_text: str
    quality_score: float

class SecurityScanResult(TypedDict, total=False):
    is_safe: bool
    threat_detected: str
    details: str
    logs: List[str]

class ClassificationResult(TypedDict, total=False):
    category: str
    departments: List[str]
    priority: str
    language: str

class AgentState(TypedDict):
    # Standard LangGraph message history
    messages: Annotated[list, add_messages]
    
    # Document context and steps
    document: DocumentContext
    security_scan: SecurityScanResult
    classification: ClassificationResult
    extracted_maps: List[Dict[str, Any]]
    
    # Logs of steps executed by the planner
    execution_logs: List[str]
    
    # Flag to terminate early (e.g., security violation)
    terminate: bool
