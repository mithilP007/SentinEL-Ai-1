"""
SentinEL Real-Time Journey Tracker
Tracks position along route from start to end, continuously monitoring threats and weather.
This enables LIVE monitoring as if a vehicle is actually traveling the route.
"""
import asyncio
import time
import math
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from threading import Lock

@dataclass
class JourneyPoint:
    lat: float
    lng: float
    distance_from_start_km: float
    estimated_time_from_start_min: float
    weather: Optional[Dict] = None
    threats: List[Dict] = field(default_factory=list)
    
@dataclass
class ActiveJourney:
    journey_id: str
    start_address: str
    end_address: str
    polyline: List[List[float]]
    total_distance_km: float
    total_duration_min: float
    start_time: float  # Unix timestamp when journey started
    last_update_real_time: float  # Last time we updated accumulated journey time
    accumulated_journey_min: float = 0.0  # Total journey minutes elapsed so far
    speed_multiplier: float = 1.0
    is_active: bool = True
    last_check_distance: float = 0.0
    waypoint_alerts: List[Dict] = field(default_factory=list)
    cumulative_distances: List[float] = field(default_factory=list) # Cumulative distance at each polyline point

class JourneyTracker:
    """
    Manages real-time journey tracking with continuous threat/weather monitoring.
    """
    
    def __init__(self):
        self.active_journey: Optional[ActiveJourney] = None
        self.journey_history: List[Dict] = []
        self._lock = Lock()
        
    def start_journey(
        self, 
        journey_id: str,
        start_address: str,
        end_address: str,
        polyline: List[List[float]],
        total_distance_km: float,
        total_duration_min: float,
        speed_multiplier: float = 60.0
    ) -> Dict:
        """
        Start a new journey from start to end.
        """
        # Calculate cumulative distances for polyline
        cumulative = [0.0]
        current_dist = 0.0
        for i in range(len(polyline) - 1):
            p1 = polyline[i]
            p2 = polyline[i+1]
            current_dist += haversine_distance(p1[0], p1[1], p2[0], p2[1])
            cumulative.append(current_dist)
            
        # Ensure total_distance matches OSRM if slightly off
        if total_distance_km <= 0 and current_dist > 0:
            total_distance_km = current_dist

        now = time.time()
        with self._lock:
            self.active_journey = ActiveJourney(
                journey_id=journey_id,
                start_address=start_address,
                end_address=end_address,
                polyline=polyline,
                total_distance_km=total_distance_km,
                total_duration_min=total_duration_min,
                start_time=now,
                last_update_real_time=now,
                speed_multiplier=speed_multiplier,
                cumulative_distances=cumulative
            )
            
        return {
            "journey_id": journey_id,
            "started": True,
            "total_distance_km": round(total_distance_km, 1),
            "total_duration_min": round(total_duration_min, 1),
            "speed_multiplier": speed_multiplier,
            "estimated_real_time_min": total_duration_min / speed_multiplier
        }
    
    def get_current_position(self) -> Optional[Dict]:
        """
        Get current position with distance-based interpolation.
        Supports mid-journey speed changes correctly.
        """
        with self._lock:
            if not self.active_journey or not self.active_journey.is_active:
                return None
            
            journey = self.active_journey
            now = time.time()
            
            # 1. Update accumulated journey time
            delta_real_seconds = now - journey.last_update_real_time
            delta_journey_minutes = (delta_real_seconds / 60.0) * journey.speed_multiplier
            journey.accumulated_journey_min += delta_journey_minutes
            journey.last_update_real_time = now
            
            # 2. Calculate progress based on time
            # We use time-based progress relative to total estimated duration
            progress_time = min(journey.accumulated_journey_min / journey.total_duration_min, 1.0)
            
            # 3. Target distance
            target_distance = progress_time * journey.total_distance_km
            
            # 4. Find segment in polyline based on distance (Linear Interpolation)
            lat, lng = self._interpolate_position(target_distance, journey)
            
            # Check completion
            if progress_time >= 1.0:
                journey.is_active = False
            
            return {
                "lat": lat,
                "lng": lng,
                "progress_percent": round(progress_time * 100, 1),
                "distance_traveled_km": round(target_distance, 1),
                "distance_remaining_km": round(max(0, journey.total_distance_km - target_distance), 1),
                "time_elapsed_min": round(journey.accumulated_journey_min, 1),
                "time_remaining_min": round(max(0, journey.total_duration_min - journey.accumulated_journey_min), 1),
                "speed_multiplier": journey.speed_multiplier,
                "is_complete": not journey.is_active,
                "start_address": journey.start_address,
                "end_address": journey.end_address,
                "suggested_action": self._get_suggested_action(lat, lng, progress_time * 100)
            }

    def _get_suggested_action(self, lat: float, lng: float, progress: float) -> Optional[Dict]:
        """
        Logic to suggest rerouting or halting based on nearby threats.
        """
        threats = get_nearby_threats(lat, lng, radius_km=150)
        severe_threats = [t for t in threats if t.get("severity", 0) >= 6]
        
        if severe_threats:
            threat = severe_threats[0]
            topic = threat.get("topic", "Threat")
            
            action = "CONSIDER ALTERNATE"
            if threat["severity"] >= 8: action = "AUTO-REROUTE"
            
            # Type-specific overrides
            if topic == "Road Condition":
                action = "ROUTE OPTIMIZATION REQUIRED"
            elif topic == "Holiday/Event":
                action = "EXPECT DELAYS / BUFFER ETA"

            return {
                "type": "JOURNEY_ADVICE",
                "reason": f"{topic} detected {threat['distance_km']}km ahead",
                "severity": threat["severity"],
                "action": action,
                "confidence": 0.95
            }
        return None

    def _interpolate_position(self, target_dist: float, journey: ActiveJourney) -> Tuple[float, float]:
        """
        Find precise lat/lng based on cumulative distance.
        """
        dists = journey.cumulative_distances
        points = journey.polyline
        
        if target_dist <= 0: return points[0][0], points[0][1]
        if target_dist >= dists[-1]: return points[-1][0], points[-1][1]
        
        # Simple search for the segment
        for i in range(len(dists) - 1):
            if dists[i] <= target_dist <= dists[i+1]:
                # Interpolate between points[i] and points[i+1]
                segment_len = dists[i+1] - dists[i]
                if segment_len == 0: return points[i][0], points[i][1]
                
                factor = (target_dist - dists[i]) / segment_len
                
                p1, p2 = points[i], points[i+1]
                lat = p1[0] + (p2[0] - p1[0]) * factor
                lng = p1[1] + (p2[1] - p1[1]) * factor
                return lat, lng
                
        return points[-1][0], points[-1][1]

    def add_waypoint_alert(self, alert: Dict) -> None:
        """Add unique alerts to the journey log."""
        with self._lock:
            if not self.active_journey: return
            
            # De-duplicate by type and location for the current progress window
            # If we already have an alert for this location/type within last 5%, skip
            current_progress = alert.get("at_progress", 0)
            
            duplicate = False
            for existing in self.active_journey.waypoint_alerts[-5:]: # Check last few
                if (existing["type"] == alert["type"] and 
                    existing.get("location") == alert.get("location") and
                    abs(existing["at_progress"] - current_progress) < 5.0):
                    duplicate = True
                    break
            
            if not duplicate:
                self.active_journey.waypoint_alerts.append(alert)
    
    def get_waypoint_alerts(self) -> List[Dict]:
        return self.active_journey.waypoint_alerts.copy() if self.active_journey else []
    
    def stop_journey(self) -> Dict:
        with self._lock:
            if self.active_journey:
                j = self.active_journey
                j.is_active = False
                self.journey_history.append({
                    "id": j.journey_id,
                    "alerts": len(j.waypoint_alerts),
                    "time": time.time()
                })
                self.active_journey = None # Clear on stop
                return {"stopped": True, "id": j.journey_id}
            return {"stopped": False}

    def update_speed(self, new_speed: float) -> bool:
        """Update speed multiplier mid-journey, ensuring accumulated time is preserved."""
        with self._lock:
            if not self.active_journey or not self.active_journey.is_active:
                return False
            
            # Update accumulated time using OLD speed first
            now = time.time()
            delta_real_seconds = now - self.active_journey.last_update_real_time
            delta_journey_minutes = (delta_real_seconds / 60.0) * self.active_journey.speed_multiplier
            self.active_journey.accumulated_journey_min += delta_journey_minutes
            self.active_journey.last_update_real_time = now
            
            # Set new speed
            self.active_journey.speed_multiplier = new_speed
            return True

    def get_journey_status(self) -> Dict:
        with self._lock:
            if not self.active_journey: return {"active": False}
            return {
                "active": self.active_journey.is_active,
                "journey_id": self.active_journey.journey_id,
                "alerts_count": len(self.active_journey.waypoint_alerts)
            }

# Global tracker instance
journey_tracker = JourneyTracker()

# Helper utilities
def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1-a))

def get_nearby_threats(lat: float, lng: float, radius_km: float = 200) -> List[Dict]:
    threats = []
    try:
        from src.memory_store import memory
        from src.route_service import get_coordinates_for_location
        # Get more events for better coverage
        recent = memory.get_recent_events(limit=200)
        for e in recent:
            # First try if event has lat/lng already (some might)
            e_lat = e.get("lat")
            e_lng = e.get("lng")
            
            if e_lat is None or e_lng is None:
                coords = get_coordinates_for_location(e.get("location", ""))
                if coords:
                    e_lat, e_lng = coords
            
            if e_lat is not None and e_lng is not None:
                dist = haversine_distance(lat, lng, e_lat, e_lng)
                if dist <= radius_km:
                    threats.append({
                        **e, 
                        "distance_km": round(dist, 1), 
                        "lat": e_lat, 
                        "lng": e_lng
                    })
    except Exception as e: 
        print(f"Error in get_nearby_threats: {e}")
    return sorted(threats, key=lambda x: x["distance_km"])[:10]

async def get_current_weather(lat: float, lng: float) -> Optional[Dict]:
    try:
        from src.weather_live import fetch_weather_for_point
        w = fetch_weather_for_point(lat, lng)
        if w: return {
            "condition": w.condition, "temp": w.temperature, 
            "severity": w.severity, "location": w.location,
            "wind": w.wind_speed
        }
    except: pass
    return None
