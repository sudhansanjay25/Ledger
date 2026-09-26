import json
from langchain_core.messages import HumanMessage
from graph import build_agent_graph

def run_test_case(document_id: str, description: str):
    print("\n" + "="*80)
    print(f"TEST CASE: {description}")
    print(f"Document ID: {document_id}")
    print("="*80)
    
    # Initialize the compiled LangGraph
    app = build_agent_graph()
    
    # Setup initial state
    initial_state = {
        "messages": [HumanMessage(content=f"Please ingest and process document {document_id}.")],
        "document": {},
        "security_scan": {},
        "classification": {},
        "extracted_maps": [],
        "execution_logs": [],
        "terminate": False
    }
    
    # Run the state graph
    # Config is optional; we run synchronously here
    result = app.invoke(initial_state)
    
    # Print execution history log
    print("\n--- EXECUTION LOGS ---")
    if result.get("execution_logs"):
        for step in result["execution_logs"]:
            print(f" -> {step}")
    else:
        print("No tool logs recorded.")
        
    # Print the agent's final reasoning/response
    print("\n--- AGENT FINAL RESPONSE ---")
    if result.get("messages"):
        last_msg = result["messages"][-1]
        print(last_msg.content)
        
    # Print State summary
    print("\n--- FINAL STATE METRICS ---")
    print(f"Security Safe: {result.get('security_scan', {}).get('is_safe', 'N/A')}")
    if result.get('security_scan', {}).get('threat_detected'):
        print(f"Threat Flagged: {result['security_scan']['threat_detected']}")
    print(f"Text Quality: {result.get('document', {}).get('quality_score', 'N/A')}")
    print(f"Category Classified: {result.get('classification', {}).get('category', 'N/A')}")
    print(f"Generated MAPs Count: {len(result.get('extracted_maps', []))}")
    
    # Print generated MAPs if any
    if result.get("extracted_maps"):
        print("\n--- GENERATED MEASURABLE ACTION POINTS (MAPs) ---")
        for idx, map_obj in enumerate(result["extracted_maps"]):
            print(f"\n[{idx+1}] ID: {map_obj['action_id']}")
            print(f"    Action: {map_obj['action']}")
            print(f"    Department: {map_obj['department']}")
            print(f"    Deadline: {map_obj['deadline']} ({map_obj['deadline_type']})")
            print(f"    Priority: {map_obj['priority']}")
            print(f"    Obligation Type: {map_obj['obligation_type']}")
            print(f"    Source Text: \"{map_obj['source_sentence']}\"")
            print(f"    AI Confidence: {map_obj['confidence']}")
            
    print("="*80 + "\n")

def main():
    print("Initializing Ledger Planner Agent Test Suite...")
    
    # Test Case 1: Benign Payment Security Circular
    run_test_case(
        document_id="rbi_2026_payment_sec_01",
        description="Benign Circular Ingestion (Should succeed and generate MAPs)"
    )
    
    # Test Case 2: Malicious System Override Circular
    run_test_case(
        document_id="malicious_spoof_01",
        description="Prompt Injection Injection (Should flag threat and halt immediately)"
    )
    
    # Test Case 3: Poor Quality OCR scan document
    run_test_case(
        document_id="rbi_2026_low_ocr_02",
        description="Low Quality OCR Ingestion (Should halt due to reading quality score)"
    )

if __name__ == "__main__":
    main()
