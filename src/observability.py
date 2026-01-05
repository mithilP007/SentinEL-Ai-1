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

# Persistent session for HTTP Bridge
_http_session: Optional['aiohttp.ClientSession'] = None

class AgentTelemetry:
    @staticmethod
    async def _get_session():
        global _http_session
        import aiohttp
        if _http_session is None or _http_session.closed:
            _http_session = aiohttp.ClientSession()
        return _http_session

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
        
        # 1. Console Log
        print(f"\r[AGENT] {state.value} | {event_id} | {details.get('topic', details.get('thought', '...'))[:50]}", end="")
        
        # 2. Local Broadcast
        await broadcast_queue.put(payload)
        
        # 3. HTTP Bridge (To Dashboard)
        try:
            from src.metrics import metrics
            metrics_snapshot = metrics.get_metrics_snapshot()
            
            payload_with_metrics = {
                "telemetry": payload,
                "metrics": metrics_snapshot
            }
            
            session = await AgentTelemetry._get_session()
            async with session.post(
                "http://localhost:8000/ingest/telemetry", 
                json=payload_with_metrics,
                timeout=2
            ) as resp:
                pass
        except Exception:
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
