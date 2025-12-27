import time
import threading
from src.ingestion import prompt_news_stream, prompt_shipment_stream
from src.perception import detect_affected_shipments
from src.agent_brain import build_agent_graph
from src.memory import MemoryManager

# --- Mock Pathway Behavior ---
# Since Pathway runs on Linux/WSL, we simulate the "Subscribe" behavior 
# for the Windows verification step.

import asyncio
import time
from src.ingestion import prompt_news_stream, prompt_shipment_stream
from src.agent_brain import build_agent_graph
from src.memory import MemoryManager
from src.observability import AgentTelemetry, AgentState

async def run_windows_demo():
    print("--- STARTING SENTINEL (WINDOWS COMPATIBILITY MODE) ---")
    print("NB: Using Python generators to simulate Pathway streams.")
    print(">>> DASHBOARD SHOULD BE VISIBLE AT http://localhost:8000/ <<<\n")

    agent_graph = build_agent_graph()
    memory = MemoryManager()
    
    # 1. Initialize State with Shipments
    print(">>> Loading active shipments...")
    shipments_gen = prompt_shipment_stream()
    active_shipments = []
    
    # Pre-load 5 shipments
    for _ in range(5):
        active_shipments.append(next(shipments_gen))
    
    print(f"Loaded {len(active_shipments)} active shipments.")
    
    # 2. Process News Stream
    print(">>> Listening to News Stream (Simulated)...")
    news_gen = prompt_news_stream()
    
    try:
        while True:
            # Simulate event arrival
            event = next(news_gen)
            
            # Emit "Event Detected" to UI
            await AgentTelemetry.emit(
                AgentState.OBSERVE, 
                event['event_id'], 
                {"topic": event['topic'], "location": event['location']}
            )
            
            # Trigger Agent
            state = {
                "raw_event": event,
                "active_shipments": active_shipments,
                "affected_shipments": [],
                "analysis_logs": [],
                "decisions": [],
                "actions_taken": []
            }
            
            # Run Graph (Async)
            # LangGraph compiled graph is callable
            result = await agent_graph.ainvoke(state)
            
            # Log
            if result.get("decisions"):
                memory.log_outcome(event, result['decisions'])
                
            # Wait for next event (simulated delay)
            await asyncio.sleep(4)
            
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n--- DEMO STOPPED ---")

if __name__ == "__main__":
    asyncio.run(run_windows_demo())
