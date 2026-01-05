from src.ingestion_live import flow_gdelt_news, flow_ais
from src.perception import detect_affected_shipments
from src.agent_brain import build_agent_graph
from src.memory import MemoryManager
import threading
import time
import json
import os
import asyncio

# --- Setup System ---

print("--- INITIALIZING SENTINEL (WINDOWS RUNTIME) ---")
agent_graph = build_agent_graph()
memory = MemoryManager()

# --- Shared State ---
latest_shipments = []
shipments_lock = threading.Lock()

def load_active_route_shipment():
    """Reads the active route from disk if it exists."""
    if os.path.exists("active_route.json"):
        try:
            with open("active_route.json", "r") as f:
                return json.load(f)
        except:
            pass
    return None

def on_shipment_received(row):
    """Updates local cache of shipments."""
    with shipments_lock:
        # Check if already in list (by shipment_id)
        existing = next((s for s in latest_shipments if s['shipment_id'] == row['shipment_id']), None)
        if existing:
            latest_shipments.remove(existing)
        latest_shipments.append(row)
        # Keep cache size reasonable
        if len(latest_shipments) > 50:
            latest_shipments.pop(0)

async def on_news_received(row):
    """
    Triggered whenever a new News item arrives.
    Fires the Agent.
    """
    print(f"\n[EVENT DETECTED] {row['topic']} at {row['location']}")
    
    # Check for user active route and inject it into shipments
    active_route = load_active_route_shipment()
    
    with shipments_lock:
        combined_shipments = list(latest_shipments)
    
    if active_route:
        combined_shipments.append(active_route)
    
    # Trigger Agent
    initial_state = {
        "raw_event": row,
        "active_shipments": combined_shipments,
        "affected_shipments": [],
        "analysis_logs": [],
        "decisions": [],
        "actions_taken": []
    }
    
    print(">>> WAKING AGENT...")
    try:
        result = await agent_graph.ainvoke(initial_state)
        
        if result and result.get('decisions'):
            print(">>> AGENT FINISHED. Decisions made.")
        else:
            print(">>> AGENT FINISHED. No actions needed.")
    except Exception as e:
        print(f">>> AGENT ERROR: {e}")

# --- Worker Threads ---

def shipment_worker():
    print("[RUNNER] Shipment stream started.")
    for shipment in flow_ais():
        on_shipment_received(shipment)

def news_worker():
    print("[RUNNER] News stream started.")
    # Since news_received is async, we need an event loop in this thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    for event in flow_gdelt_news():
        loop.run_until_complete(on_news_received(event))

def run():
    t1 = threading.Thread(target=shipment_worker, daemon=True)
    t2 = threading.Thread(target=news_worker, daemon=True)
    
    t1.start()
    t2.start()
    
    print("--- REAL-TIME MONITORING ACTIVE ---")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping...")

if __name__ == "__main__":
    run()
