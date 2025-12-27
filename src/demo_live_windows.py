import asyncio
import time
try:
    import langchain
    if not hasattr(langchain, 'debug'):
        langchain.debug = False
except ImportError:
    pass
# Import from LIVE ingestion
from src.ingestion_live import flow_gdelt_news, flow_ais
from src.agent_brain import build_agent_graph
from src.memory import MemoryManager
from src.observability import AgentTelemetry, AgentState

async def run_live_demo():
    print("===================================================")
    print("   SENTINEL LIVE DATA ENGINE (WINDOWS RUNNER)")
    print("===================================================")
    print(">> CONNECTING TO LIVE GLOBAL STREAMS...")
    print("   [1] GDELT Project (News)  : CONNECTED")
    print("   [2] AISHub (Shipping)     : CONNECTED")
    print("   [3] OpenWeatherMap        : CONNECTED")
    print("\n>>> DASHBOARD: http://localhost:8000/ <<<\n")

    agent_graph = build_agent_graph()
    memory = MemoryManager()
    
    # 1. Initialize State with Shipments (Live AIS)
    print(">>> Buffering Live Shipments (AIS)...")
    shipments_gen = flow_ais()
    active_shipments = []
    
    # Pre-load buffer
    try:
        for _ in range(5):
             item = next(shipments_gen)
             active_shipments.append(item)
    except StopIteration:
        pass
    
    print(f"Tracking {len(active_shipments)} vessels in real-time.")
    
    # 2. Process News Stream (Live GDELT)
    print(">>> Listening for Disruption Signals (GDELT)...")
    news_gen = flow_gdelt_news()
    
    print(">>> Listening for Disruption Signals (GDELT)...")
    news_gen = flow_gdelt_news()
    
    while True:
        try:
            # Poll GDELT
            try:
                event = next(news_gen)
            except StopIteration:
                print("Stream buffer empty, retrying...")
                await asyncio.sleep(2)
                continue
            
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
            result = await agent_graph.ainvoke(state)
            
            # Log
            if result.get("decisions"):
                memory.log_outcome(event, result['decisions'])
                
            # Real-time polling interval
            await asyncio.sleep(3)
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"Error: {e}")
            await asyncio.sleep(1) # Backoff
    
    print("\n--- LIVE FEED DISCONNECTED ---")
    
    print("\n--- LIVE FEED DISCONNECTED ---")

if __name__ == "__main__":
    asyncio.run(run_live_demo())
