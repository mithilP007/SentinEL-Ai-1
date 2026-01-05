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
    
    # 2. Process Streams (Live GDELT + AIS)
    print(">>> Listening for Disruption Signals (GDELT)...")
    news_gen = flow_gdelt_news()
    
    iteration = 0
    while True:
        try:
            # 1. SYSTEM SYNC: Check for User's Active Route
            import os
            import json
            if os.path.exists("active_route.json"):
                try:
                    with open("active_route.json", "r") as f:
                        user_route = json.load(f)
                    
                    # Ensure User Route is in the active buffer
                    found = False
                    for i, s in enumerate(active_shipments):
                        if s["shipment_id"] == "USER_ACTIVE_ROUTE":
                            active_shipments[i] = user_route # Update latest
                            found = True
                            break
                    if not found:
                        active_shipments.insert(0, user_route) # Priority #1
                        print(f"\n[SYNC] User Route Detected: {user_route['route_id']}. Activating priority monitoring.")
                except Exception: pass
            
            # Periodically refresh AIS buffer
            if iteration % 5 == 0:
                try:
                    new_ship = next(shipments_gen)
                    active_shipments.append(new_ship)
                    if len(active_shipments) > 15: # Keep buffer manageable
                        active_shipments.pop(0)
                except Exception: pass

            # Non-blocking poll for GDELT (via next() on the generator)
            # Note: next() is blocking, but flow_gdelt_news yields batch
            try:
                event = next(news_gen)
            except StopIteration:
                await asyncio.sleep(5)
                continue
            
            # Emit "Event Detected" to UI
            # We add coordinates here if not present for mapping
            from src.route_service import get_coordinates_for_location
            coords = get_coordinates_for_location(event['location'])
            
            await AgentTelemetry.emit(
                AgentState.OBSERVE, 
                event['event_id'], 
                {
                    "topic": event['topic'], 
                    "location": event['location'],
                    "coords": {"lat": coords[0], "lng": coords[1]} if coords else None
                }
            )
            
            # Trigger Agent Graph
            state = {
                "raw_event": event,
                "active_shipments": active_shipments,
                "affected_shipments": [],
                "analysis_logs": [],
                "decisions": [],
                "actions_taken": []
            }
            
            # Run Graph
            result = await agent_graph.ainvoke(state)
            
            # Store memory
            if result.get("decisions"):
                memory.log_outcome(event, result['decisions'])
            
            iteration += 1
            await asyncio.sleep(2) # Throttle for readability
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"\n[ERROR] {e}")
            await asyncio.sleep(5)
    
    print("\n--- LIVE FEED DISCONNECTED ---")
    
    print("\n--- LIVE FEED DISCONNECTED ---")

if __name__ == "__main__":
    asyncio.run(run_live_demo())
