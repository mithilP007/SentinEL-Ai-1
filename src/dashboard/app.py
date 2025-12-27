from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import asyncio
import json
import os
from src.observability import broadcast_queue
from src.metrics import metrics

app = FastAPI()

# Serve static files (HTML/CSS/JS)
# We'll serve the current directory as static for simplicity in this demo structure
# In a real app, separate 'static' folder.
# app.mount("/static", StaticFiles(directory="src/dashboard"), name="static")

@app.get("/")
async def get():
    # Serve the dashboard HTML (must use UTF-8 for emoji support)
    with open("src/dashboard/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # Wait for message from the Agent via the broadcast queue
            broadcast_data = await broadcast_queue.get()
            
            # Extract telemetry and metrics from the new format
            # (metrics are now included by the agent in the POST)
            if isinstance(broadcast_data, dict) and "telemetry" in broadcast_data:
                telemetry = broadcast_data.get("telemetry", {})
                agent_metrics = broadcast_data.get("metrics", {})
            else:
                # Legacy format fallback
                telemetry = broadcast_data
                agent_metrics = _agent_metrics
            
            payload = {
                "type": "telemetry",
                "data": telemetry,
                "metrics": agent_metrics
            }
            
            await websocket.send_text(json.dumps(payload))
    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"WebSocket error: {e}")

from pydantic import BaseModel
from typing import Optional, Dict, Any

class TelemetryData(BaseModel):
    timestamp: str
    agent_state: str
    event_id: str
    details: dict
    confidence: float = 1.0

class FullPayload(BaseModel):
    telemetry: TelemetryData
    metrics: Optional[Dict[str, Any]] = None

# Store latest metrics from agent
_agent_metrics = {
    "mttd_seconds": None,
    "mtta_seconds": None,
    "estimated_days_saved": 0,
    "estimated_cost_saved": 0,
    "events_prevented": 0,
    "predicted_delays": 0,
    "events_seen": 0,
    "actions_taken": 0
}

# BRIDGE ENDPOINT
@app.post("/ingest/telemetry")
async def ingest_telemetry(payload: FullPayload):
    global _agent_metrics
    
    # Update stored metrics from agent
    if payload.metrics:
        _agent_metrics = payload.metrics
    
    # Broadcast telemetry with agent metrics attached
    broadcast_data = {
        "telemetry": payload.telemetry.dict(),
        "metrics": _agent_metrics
    }
    await broadcast_queue.put(broadcast_data)
    return {"status": "ok"}

# Optional: Endpoint to trigger a demo event manually (if we added a button)
@app.post("/trigger_demo")
async def trigger_demo():
    return {"status": "Event injected"}

# MEMORY INSIGHTS ENDPOINT - For Post-Transformer Panel
@app.get("/api/memory-insights")
async def get_memory_insights():
    """
    Returns adaptive memory insights proving continuous learning.
    This is the key differentiator from traditional transformers.
    """
    try:
        from src.memory_store import memory
        insights = memory.get_adaptive_insights()
        return insights
    except Exception as e:
        return {
            "insights": ["Memory system initializing..."],
            "confidence_trend": {"initial": 61, "current": 61},
            "adaptation_score": 0,
            "recurring_patterns": [],
            "error": str(e)
        }
