from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
import os
from src.observability import broadcast_queue
from src.metrics import metrics

app = FastAPI(title="SentinEL Route Monitor", version="2.0")

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================
# ACTIVE ROUTE STATE (Per-Session Monitoring)
# ============================================
active_routes = {}  # session_id -> route data
active_corridor_points = []  # Global corridor for filtering
active_route_data = None  # Store full route for journey tracking

@app.get("/")
async def get():
    # Serve the dashboard HTML (must use UTF-8 for emoji support)
    with open("src/dashboard/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())

# ============================================
# ROUTE-BASED ENDPOINTS (NEW - REAL DATA)
# ============================================

from pydantic import BaseModel
from typing import Optional, Dict, Any, List

class GeocodeRequest(BaseModel):
    address: str

class RouteRequest(BaseModel):
    start_lat: float
    start_lng: float
    end_lat: float
    end_lng: float

class SetRouteRequest(BaseModel):
    start_address: str
    end_address: str
    start_lat: Optional[float] = None
    start_lng: Optional[float] = None
    end_lat: Optional[float] = None
    end_lng: Optional[float] = None

@app.post("/api/geocode")
async def geocode_address(request: GeocodeRequest):
    """
    Convert address to coordinates using Nominatim (REAL, FREE).
    """
    from src.route_service import geocode_address as geo
    result = geo(request.address)
    return {
        "success": result.success,
        "lat": result.lat,
        "lng": result.lng,
        "display_name": result.display_name,
        "error": result.error
    }
    
class ReverseGeocodeRequest(BaseModel):
    lat: float
    lng: float

@app.post("/api/reverse-geocode")
async def reverse_geocode_endpoint(request: ReverseGeocodeRequest):
    """
    Convert coordinates to address using Nominatim (REAL, FREE).
    """
    from src.route_service import reverse_geocode as rev_geo
    result = rev_geo(request.lat, request.lng)
    return {
        "success": result.success,
        "lat": result.lat,
        "lng": result.lng,
        "display_name": result.display_name,
        "error": result.error
    }

@app.post("/api/route")
async def calculate_route(request: RouteRequest):
    """
    Calculate route between two points using OSRM (REAL, FREE).
    """
    from src.route_service import calculate_route as calc
    result = calc(request.start_lat, request.start_lng, request.end_lat, request.end_lng)
    return {
        "success": result.success,
        "polyline": result.polyline,
        "waypoints": result.waypoints,
        "distance_km": result.distance_km,
        "duration_minutes": result.duration_minutes,
        "error": result.error
    }

@app.post("/api/set-route")
async def set_active_route(request: SetRouteRequest):
    """
    Set the active monitoring route. Geocodes addresses if coordinates not provided.
    Returns full route with polyline and initializes corridor monitoring.
    """
    global active_corridor_points, active_route_data
    
    from src.route_service import geocode_address, calculate_route, generate_corridor_points, get_coordinates_for_location
    
    # Get start coordinates
    if request.start_lat and request.start_lng:
        start_lat, start_lng = request.start_lat, request.start_lng
    else:
        result = geocode_address(request.start_address)
        if not result.success:
            return {"success": False, "error": f"Could not geocode start: {result.error}"}
        start_lat, start_lng = result.lat, result.lng
    
    # Get end coordinates
    if request.end_lat and request.end_lng:
        end_lat, end_lng = request.end_lat, request.end_lng
    else:
        result = geocode_address(request.end_address)
        if not result.success:
            return {"success": False, "error": f"Could not geocode end: {result.error}"}
        end_lat, end_lng = result.lat, result.lng
    
    # Calculate route
    route = calculate_route(start_lat, start_lng, end_lat, end_lng)
    if not route.success:
        return {"success": False, "error": f"Could not calculate route: {route.error}"}
    
    # Generate corridor points for monitoring
    active_corridor_points = generate_corridor_points(route.polyline, buffer_km=200)
    
    # Store full route data for journey tracking
    active_route_data = {
        "start_address": request.start_address,
        "end_address": request.end_address,
        "start_lat": start_lat,
        "start_lng": start_lng,
        "end_lat": end_lat,
        "end_lng": end_lng,
        "polyline": route.polyline,
        "waypoints": route.waypoints,
        "distance_km": route.distance_km,
        "duration_minutes": route.duration_minutes
    }
    
    # SYSTEM SYNC: Write to shared file for the background Agent to see
    try:
        sync_data = {
            "shipment_id": "USER_ACTIVE_ROUTE",
            "current_location": request.start_address,
            "route_id": f"{request.start_address} to {request.end_address}",
            "status": "Priority Monitoring",
            "cargo_type": "Priority Shipment",
            "updated_at": time.time(),
            "waypoints": route.waypoints
        }
        with open("active_route.json", "w") as f:
            json.dump(sync_data, f)
    except Exception as e:
        print(f"Sync failed: {e}")
    
    # Get weather summary for route (FREE - Open-Meteo API, NO API KEY REQUIRED)
    weather_summary = {}
    try:
        from src.weather_live import get_weather_summary_for_route
        weather_summary = get_weather_summary_for_route(
            (start_lat, start_lng), 
            (end_lat, end_lng)
        )
    except Exception as e:
        print(f"Weather fetch failed: {e}")
    
    return {
        "success": True,
        "start": {"lat": start_lat, "lng": start_lng, "address": request.start_address},
        "end": {"lat": end_lat, "lng": end_lng, "address": request.end_address},
        "polyline": route.polyline,
        "waypoints": route.waypoints,
        "distance_km": route.distance_km,
        "duration_minutes": route.duration_minutes,
        "corridor_points": len(active_corridor_points),
        "weather_summary": weather_summary
    }

@app.post("/api/route/plan")
async def plan_smart_route(request: SetRouteRequest):
    """
    SMART ROUTE PLANNING:
    1. Calculates multiple route options (OSRM).
    2. Analyzes REAL-TIME weather and threats for EACH option.
    3. Uses AI to recommend the best route.
    """
    from src.route_service import geocode_address, calculate_routes_with_alternatives, analyze_route_risks
    from src.reasoning import ReasoningEngine
    
    # 1. Geocode
    if request.start_lat and request.start_lng:
        s_lat, s_lng = request.start_lat, request.start_lng
    else:
        res = geocode_address(request.start_address)
        if not res.success: return {"success": False, "error": f"Start location not found: {res.error}"}
        s_lat, s_lng = res.lat, res.lng
        
    if request.end_lat and request.end_lng:
        e_lat, e_lng = request.end_lat, request.end_lng
    else:
        res = geocode_address(request.end_address)
        if not res.success: return {"success": False, "error": f"End location not found: {res.error}"}
        e_lat, e_lng = res.lat, res.lng
        
    # 2. Get Alternatives
    routes = calculate_routes_with_alternatives(s_lat, s_lng, e_lat, e_lng)
    
    if not routes:
        return {"success": False, "error": "No routes found."}
        
    # 3. Analyze Risks for each
    options = []
    for i, r in enumerate(routes):
        analysis = analyze_route_risks(r)
        options.append({
            "id": i + 1,
            "distance_km": r.distance_km,
            "duration_minutes": r.duration_minutes,
            "polyline": r.polyline,
            "analysis": analysis
        })
        
    # 4. AI Recommendation
    engine = ReasoningEngine()
    ai_recommendation = engine.smart_route_selection({
        "start_address": request.start_address,
        "end_address": request.end_address,
        "options": options
    })
    
    return {
        "success": True,
        "start": {"lat": s_lat, "lng": s_lng, "address": request.start_address},
        "end": {"lat": e_lat, "lng": e_lng, "address": request.end_address},
        "options": options,
        "recommendation": ai_recommendation
    }


# ============================================
# REAL-TIME JOURNEY TRACKING ENDPOINTS
# ============================================

from src.journey_tracker import journey_tracker, get_nearby_threats, get_current_weather
import uuid

class StartJourneyRequest(BaseModel):
    speed_multiplier: float = 60.0  # 60x = 1 hour journey in 1 minute

@app.post("/api/journey/start")
async def start_journey(request: StartJourneyRequest):
    """
    Start real-time journey tracking along the active route.
    Position updates automatically based on elapsed time.
    """
    global active_route_data
    
    if not active_route_data:
        return {"success": False, "error": "No route data available. Please set a route first."}
    
    journey_id = str(uuid.uuid4())[:8]
    result = journey_tracker.start_journey(
        journey_id=journey_id,
        start_address=active_route_data["start_address"],
        end_address=active_route_data["end_address"],
        polyline=active_route_data["polyline"],
        total_distance_km=active_route_data["distance_km"],
        total_duration_min=active_route_data["duration_minutes"],
        speed_multiplier=request.speed_multiplier
    )
    
    return {"success": True, **result}

@app.get("/api/journey/position")
async def get_journey_position():
    """
    Get current position along the journey.
    Returns lat/lng, progress, distance traveled, time remaining.
    """
    position = journey_tracker.get_current_position()
    
    if not position:
        return {"success": False, "error": "No active journey", "active": False}
    
    return {"success": True, **position}

@app.get("/api/journey/position-with-data")
async def get_journey_position_with_data():
    """
    Get current position with weather and nearby threats.
    This is the main endpoint for real-time monitoring dashboard.
    """
    position = journey_tracker.get_current_position()
    
    if not position:
        return {"success": False, "error": "No active journey", "active": False}
    
    # Get weather at current position
    weather = await get_current_weather(position["lat"], position["lng"])
    
    # Get nearby threats
    threats = get_nearby_threats(position["lat"], position["lng"], radius_km=200)
    
    # Record alerts if there are severe threats or weather
    if threats:
        for threat in threats[:3]:  # Top 3 nearest
            if threat.get("severity", 0) >= 6:
                journey_tracker.add_waypoint_alert({
                    "type": "threat",
                    "location": threat["location"],
                    "severity": threat["severity"],
                    "distance_km": threat["distance_km"],
                    "at_progress": position["progress_percent"]
                })
    
    if weather and weather.get("severity", 0) >= 6:
        journey_tracker.add_waypoint_alert({
            "type": "weather",
            "condition": weather["condition"],
            "severity": weather["severity"],
            "at_progress": position["progress_percent"]
        })
    
    return {
        "success": True,
        "position": position,
        "weather": weather,
        "threats": threats[:5],  # Top 5 nearest threats
        "journey_alerts": journey_tracker.get_waypoint_alerts()[-10:]  # Last 10 alerts
    }

@app.post("/api/journey/stop")
async def stop_journey():
    """Stop the current journey tracking."""
    result = journey_tracker.stop_journey()
    return {"success": True, **result}

@app.get("/api/journey/status")
async def get_journey_status():
    """Get journey status without position details."""
    status = journey_tracker.get_journey_status()
    return {"success": True, **status}

@app.post("/api/journey/speed")
async def set_journey_speed(speed_multiplier: float = 60.0):
    """Adjust journey speed multiplier (for demo purposes)."""
    success = journey_tracker.update_speed(speed_multiplier)
    if success:
        return {"success": True, "speed_multiplier": speed_multiplier}
    return {"success": False, "error": "No active journey"}

@app.get("/api/weather-along-route")
async def get_weather_along_route():
    """
    Get current weather conditions along the active route.
    Uses Open-Meteo API - FREE, NO API KEY REQUIRED, REAL DATA.
    """
    global active_corridor_points
    
    if not active_corridor_points:
        return {"success": False, "error": "No active route set. Please set a route first."}
    
    from src.weather_live import fetch_weather_for_point
    
    weather_data = []
    # Sample 5 points from corridor
    sample_indices = [0, len(active_corridor_points)//4, len(active_corridor_points)//2, 
                      3*len(active_corridor_points)//4, len(active_corridor_points)-1]
    
    # Remove duplicates
    sample_indices = list(dict.fromkeys(sample_indices))
    
    for i in sample_indices:
        if i < len(active_corridor_points):
            lat, lng, _ = active_corridor_points[i]
            alert = fetch_weather_for_point(lat, lng)  # No API key needed!
            if alert:
                weather_data.append({
                    "location": alert.location,
                    "lat": alert.lat,
                    "lng": alert.lng,
                    "condition": alert.condition,
                    "temperature": alert.temperature,
                    "wind_speed": alert.wind_speed,
                    "humidity": alert.humidity,
                    "severity": alert.severity,
                    "description": alert.description
                })
            await asyncio.sleep(0.3)  # Be nice to the free API
    
    return {"success": True, "weather": weather_data}

@app.get("/api/threats-in-corridor")
async def get_threats_in_corridor():
    """
    Get current threats (news/events) within the active route corridor.
    Filters GDELT and other sources for route-specific threats.
    """
    global active_corridor_points
    
    if not active_corridor_points:
        return {"success": False, "error": "No active route set"}
    
    from src.route_service import is_point_in_corridor, get_coordinates_for_location
    
    # Get recent events from memory
    threats = []
    try:
        from src.memory_store import memory
        recent_events = memory.get_recent_events(limit=50)
        
        for event in recent_events:
            location = event.get("location", "")
            coords = get_coordinates_for_location(location)
            
            if coords and is_point_in_corridor(coords[0], coords[1], active_corridor_points):
                threats.append({
                    "event_id": event.get("event_id"),
                    "topic": event.get("topic"),
                    "location": location,
                    "lat": coords[0],
                    "lng": coords[1],
                    "severity": event.get("severity", 5),
                    "summary": event.get("summary", ""),
                    "timestamp": event.get("timestamp")
                })
    except Exception as e:
        print(f"Error fetching corridor threats: {e}")
    
    return {"success": True, "threats": threats}

# ============================================
# WEBSOCKET (Enhanced with Route Filtering)
# ============================================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    global active_corridor_points
    
    await websocket.accept()
    try:
        while True:
            # Wait for message from the Agent via the broadcast queue
            broadcast_data = await broadcast_queue.get()
            
            # Extract telemetry and metrics
            if isinstance(broadcast_data, dict) and "telemetry" in broadcast_data:
                telemetry = broadcast_data.get("telemetry", {})
                agent_metrics = broadcast_data.get("metrics", {})
            else:
                telemetry = broadcast_data
                agent_metrics = _agent_metrics
            
            # ROUTE FILTERING: If corridor is active, check if event is relevant
            is_relevant = True
            if active_corridor_points and telemetry.get("details", {}).get("location"):
                from src.route_service import is_point_in_corridor, get_coordinates_for_location
                location = telemetry["details"]["location"]
                coords = get_coordinates_for_location(location)
                if coords:
                    is_relevant = is_point_in_corridor(coords[0], coords[1], active_corridor_points)
                    telemetry["in_corridor"] = is_relevant
                    telemetry["coords"] = {"lat": coords[0], "lng": coords[1]}
            
            payload = {
                "type": "telemetry",
                "data": telemetry,
                "metrics": agent_metrics,
                "route_active": len(active_corridor_points) > 0,
                "is_relevant": is_relevant
            }
            
            await websocket.send_text(json.dumps(payload))
    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"WebSocket error: {e}")

# ============================================
# LEGACY ENDPOINTS (Kept for compatibility)
# ============================================

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
    Returns REAL-TIME memory insights when journey is active.
    Falls back to adaptive insights when no journey is running.
    """
    try:
        from src.memory_store import memory
        
        # Check if journey is active
        journey_status = journey_tracker.get_journey_status()
        
        if journey_status.get("active"):
            # Get current position data for real-time insights
            position = journey_tracker.get_current_position()
            
            if position:
                # Get threats near current position
                threats = get_nearby_threats(position["lat"], position["lng"], radius_km=200)
                
                journey_data = {
                    "progress_percent": position.get("progress_percent", 0),
                    "threats_count": len(threats),
                    "weather_severity": 0  # Will be updated from weather fetch
                }
                
                # Return real-time insights
                insights = memory.get_realtime_insights(journey_data)
                insights["journey_active"] = True
                insights["current_position"] = {
                    "lat": position["lat"],
                    "lng": position["lng"],
                    "progress": position["progress_percent"]
                }
                return insights
        
        # Fall back to adaptive insights when no journey
        insights = memory.get_adaptive_insights()
        insights["journey_active"] = False
        return insights
        
    except Exception as e:
        return {
            "insights": ["System initializing..."],
            "confidence_trend": {"initial": 60, "current": 60},
            "adaptation_score": 0,
            "recurring_patterns": [],
            "journey_active": False,
            "error": str(e)
        }

