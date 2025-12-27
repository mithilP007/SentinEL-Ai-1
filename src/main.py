import pathway as pw
from src.ingestion import get_news_table, get_shipment_table
from src.perception import detect_affected_shipments
from src.agent_brain import build_agent_graph
from src.memory import MemoryManager
import threading
import time

# --- Setup System ---

print("--- INITIALIZING SENTINEL ---")
agent_graph = build_agent_graph()
memory = MemoryManager()

# --- Pathway Pipeline ---
# 1. Get Streams
news_table = get_news_table()
shipment_table = get_shipment_table()

# 2. Join/Filter Logic (The "Perception" Layer in Pathway)
# Since we need to join an "Event" stream with "State" (Shipments),
# In a full Pathway app we'd use `pw.join`.
# For this demo, we will subscribe to the NEWS table and look up shipments in the callback.
# To make "shipments" available to the callback, we'll keep a local cache of the latest shipment table snapshot.
# (Note: In pure Pathway, you'd do the join in the engine. Here we bridge to Python for the Agent).

latest_shipments = []

def on_shipment_change(key, row, time, is_addition):
    """Updates local cache of shipments."""
    if is_addition:
        latest_shipments.append(row)
    else:
        # Simplification: In a real stream, we handle updates/deletes.
        # For this infinite "new status" stream, we just append or replace.
        pass

def on_news_event(key, row, time, is_addition):
    """
    Triggered whenever a new News item arrives.
    Fires the Agent.
    """
    if not is_addition:
        return

    print(f"\n[PATHWAY DETECTED] New Event: {row['topic']} at {row['location']}")
    
    # 3. Trigger Agent
    initial_state = {
        "raw_event": row,
        "active_shipments": latest_shipments, # Injected from live cache
        "affected_shipments": [],
        "analysis_logs": [],
        "decisions": [],
        "actions_taken": []
    }
    
    # Invoke LangGraph
    print(">>> WAKING AGENT...")
    result = agent_graph.invoke(initial_state)
    
    # 4. Log Result
    if result and result.get('decisions'):
        print(">>> AGENT FINISHED. Decisions made.")
        memory.log_outcome(row, result['decisions'])
    else:
        print(">>> AGENT FINISHED. No actions needed.")

# --- Run ---

def run_simulation():
    # Subscribe to streams
    # We use `pw.io.subscribe` to trigger python functions on updates
    pw.io.subscribe(shipment_table, on_shipment_change)
    pw.io.subscribe(news_table, on_news_event)
    
    print("--- LIVE STREAMS STARTED. WAITING FOR EVENTS... ---")
    pw.run()

if __name__ == "__main__":
    run_simulation()
