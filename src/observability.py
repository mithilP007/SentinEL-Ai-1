import json
import datetime
import asyncio
from enum import Enum
from typing import Dict, Any, Optional

# Global queue for broadcasting to WebSockets
# In a real distributed system, use Redis Pub/Sub
broadcast_queue = asyncio.Queue()

class AgentState(str, Enum):
    OBSERVE = "OBSERVE"
    RETRIEVE = "RETRIEVE"
    ANALYZE = "ANALYZE"
    DECIDE = "DECIDE"
    ACT = "ACT"
    IDLE = "IDLE"

class AgentTelemetry:
    @staticmethod
    async def emit(
        state: AgentState, 
        event_id: str, 
        details: Dict[str, Any], 
        confidence: float = 1.0
    ):
        """
        Emits a structured telemetry event.
        """
        payload = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "agent_state": state.value,
            "event_id": event_id,
            "details": details,
            "confidence": confidence
        }
        
        # 1. Console Log (Structured)
        print(f"\n[TELEMETRY] {json.dumps(payload, default=str)}")
        
        # 2. Broadcast to UI
        # Try local queue first (if in same process)
        await broadcast_queue.put(payload)
        
        # 3. HTTP Bridge (Bridge to separate Dashboard process)
        # Include current metrics snapshot so Dashboard shows live values
        try:
            from src.metrics import metrics
            metrics_snapshot = metrics.get_metrics_snapshot()
            
            import aiohttp
            full_payload = {
                "telemetry": payload,
                "metrics": metrics_snapshot
            }
            async with aiohttp.ClientSession() as session:
                await session.post("http://localhost:8000/ingest/telemetry", json=full_payload)
        except Exception:
            # If dashboard is down or connection fails, just ignore (log is preserved)
            pass

    @staticmethod
    def emit_sync(state: AgentState, event_id: str, details: Dict[str, Any], confidence: float = 1.0):
        """
        Sync wrapper for non-async contexts (if needed).
        """
        # For the demo, we are running in an async loop mostly, but if called from sync code, 
        # we might drop the UI update or use run_coroutine_threadsafe.
        # Fallback to just print for safety in sync-only blocks.
        payload = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "agent_state": state.value,
            "event_id": event_id,
            "details": details,
            "confidence": confidence
        }
        print(f"\n[TELEMETRY-SYNC] {json.dumps(payload, default=str)}")
        
        # Best effort broadcast (will fail if no loop running)
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(broadcast_queue.put(payload))
        except:
            pass
