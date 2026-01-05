"""
Route Service for SentinEL
Provides REAL geocoding and routing - NO MOCK DATA
Uses free public APIs: Nominatim (geocoding), OSRM (routing)
"""
import requests
import math
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass
import time

# Rate limiting for Nominatim (max 1 request/second)
_last_nominatim_request = 0

@dataclass
class GeocodingResult:
    lat: float
    lng: float
    display_name: str
    success: bool
    error: Optional[str] = None

@dataclass
class RouteResult:
    polyline: List[List[float]]  # List of [lat, lng] coordinates
    waypoints: List[Dict]  # List of waypoint details
    distance_km: float
    duration_minutes: float
    success: bool
    error: Optional[str] = None

def geocode_address(address: str) -> GeocodingResult:
    """
    Convert address string to lat/lng coordinates.
    Uses Nominatim (OpenStreetMap) - FREE, REAL DATA.
    """
    global _last_nominatim_request
    
    # Rate limiting - Nominatim requires 1 second between requests
    elapsed = time.time() - _last_nominatim_request
    if elapsed < 1.0:
        time.sleep(1.0 - elapsed)
    
    try:
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q": address,
            "format": "json",
            "limit": 1,
            "addressdetails": 1
        }
        headers = {
            "User-Agent": "SentinEL-SupplyChain-Monitor/1.0"
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        _last_nominatim_request = time.time()
        
        if response.status_code != 200:
            return GeocodingResult(0, 0, "", False, f"Nominatim returned {response.status_code}")
        
        data = response.json()
        
        if not data:
            return GeocodingResult(0, 0, "", False, f"No results found for: {address}")
        
        result = data[0]
        return GeocodingResult(
            lat=float(result["lat"]),
            lng=float(result["lon"]),
            display_name=result.get("display_name", address),
            success=True
        )
        
    except Exception as e:
        return GeocodingResult(0, 0, "", False, str(e))

def reverse_geocode(lat: float, lng: float) -> GeocodingResult:
    """
    Convert lat/lng to address string.
    Uses Nominatim (OpenStreetMap) - FREE, REAL DATA.
    """
    global _last_nominatim_request
    
    # Rate limiting - Nominatim requires 1 second between requests
    elapsed = time.time() - _last_nominatim_request
    if elapsed < 1.0:
        time.sleep(1.0 - elapsed)
    
    try:
        url = "https://nominatim.openstreetmap.org/reverse"
        params = {
            "lat": lat,
            "lon": lng,
            "format": "json",
            "zoom": 18,
            "addressdetails": 1
        }
        headers = {
            "User-Agent": "SentinEL-SupplyChain-Monitor/1.0"
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        _last_nominatim_request = time.time()
        
        if response.status_code != 200:
            return GeocodingResult(lat, lng, "", False, f"Nominatim returned {response.status_code}")
        
        data = response.json()
        
        if not data:
            return GeocodingResult(lat, lng, "", False, f"No address found for: {lat}, {lng}")
        
        return GeocodingResult(
            lat=float(data.get("lat", lat)),
            lng=float(data.get("lon", lng)),
            display_name=data.get("display_name", f"{lat}, {lng}"),
            success=True
        )
        
    except Exception as e:
        return GeocodingResult(lat, lng, "", False, str(e))

def calculate_route(start_lat: float, start_lng: float, end_lat: float, end_lng: float) -> RouteResult:
    """
    Calculate route between two points.
    Uses OSRM public API - FREE, REAL ROUTING DATA.
    Returns the full polyline and waypoints along the route.
    """
    try:
        # OSRM expects coordinates as lng,lat (opposite of most APIs)
        url = f"https://router.project-osrm.org/route/v1/driving/{start_lng},{start_lat};{end_lng},{end_lat}"
        params = {
            "overview": "full",
            "geometries": "geojson",
            "steps": "true"
        }
        
        response = requests.get(url, params=params, timeout=15)
        
        if response.status_code != 200:
            return RouteResult([], [], 0, 0, False, f"OSRM returned {response.status_code}")
        
        data = response.json()
        
        if data.get("code") != "Ok":
            return RouteResult([], [], 0, 0, False, data.get("message", "Routing failed"))
        
        route = data["routes"][0]
        
        # Extract polyline coordinates (convert from [lng, lat] to [lat, lng] for Leaflet)
        coordinates = route["geometry"]["coordinates"]
        polyline = [[coord[1], coord[0]] for coord in coordinates]
        
        # Extract waypoints with details
        waypoints = []
        legs = route.get("legs", [])
        for leg in legs:
            for step in leg.get("steps", []):
                if step.get("name"):
                    loc = step["maneuver"]["location"]
                    waypoints.append({
                        "lat": loc[1],
                        "lng": loc[0],
                        "name": step.get("name", ""),
                        "instruction": step.get("maneuver", {}).get("instruction", "")
                    })
        
        return RouteResult(
            polyline=polyline,
            waypoints=waypoints,
            distance_km=route["distance"] / 1000,
            duration_minutes=route["duration"] / 60,
            success=True
        )
        
    except Exception as e:
        return RouteResult([], [], 0, 0, False, str(e))

def calculate_routes_with_alternatives(start_lat: float, start_lng: float, end_lat: float, end_lng: float) -> List[RouteResult]:
    """
    Calculate multiple route options between two points.
    Uses OSRM public API with alternatives=true.
    """
    try:
        url = f"https://router.project-osrm.org/route/v1/driving/{start_lng},{start_lat};{end_lng},{end_lat}"
        params = {
            "overview": "full",
            "geometries": "geojson",
            "steps": "true",
            "alternatives": "true"
        }
        
        response = requests.get(url, params=params, timeout=15)
        
        if response.status_code != 200:
            return []
        
        data = response.json()
        if data.get("code") != "Ok":
            return []
        
        results = []
        for route in data["routes"]:
            coordinates = route["geometry"]["coordinates"]
            polyline = [[coord[1], coord[0]] for coord in coordinates]
            
            waypoints = []
            legs = route.get("legs", [])
            for leg in legs:
                for step in leg.get("steps", []):
                    if step.get("name"):
                        loc = step["maneuver"]["location"]
                        waypoints.append({
                            "lat": loc[1],
                            "lng": loc[0],
                            "name": step.get("name", ""),
                            "instruction": step.get("maneuver", {}).get("instruction", "")
                        })
            
            results.append(RouteResult(
                polyline=polyline,
                waypoints=waypoints,
                distance_km=route["distance"] / 1000,
                duration_minutes=route["duration"] / 60,
                success=True
            ))
            
        return results
        
    except Exception:
        return []

def analyze_route_risks(route: RouteResult) -> Dict:
    """
    Analyze real-time risks for a specific route object.
    Checks:
    1. Weather along the path (Real-time Open-Meteo)
    2. Event threats in corridor (GDELT via Memory Store)
    Returns a Score (0-100, where 100 is best) and Risk Factors.
    """
    if not route.success:
        return {"score": 0, "risks": ["Route failed"]}
    
    # 1. Weather Analysis (Sample 5 points)
    from src.weather_live import fetch_weather_for_point
    
    weather_score = 100
    weather_risks = []
    
    # Sample points: Start, 25%, 50%, 75%, End
    indices = [0, len(route.polyline)//4, len(route.polyline)//2, 3*len(route.polyline)//4, -1]
    
    max_weather_severity = 0
    
    for i in indices:
        if i < len(route.polyline):
            lat, lng = route.polyline[i]
            # Fetch real weather
            w = fetch_weather_for_point(lat, lng)
            if w:
                if w.severity > 5:
                    max_weather_severity = max(max_weather_severity, w.severity)
                    weather_risks.append(f"{w.condition} ({w.temperature}°C) at {w.location}")
            # NO SLEEP - Already optimized in weather_live to skip reverse geocode
            
    # Penalize score based on severity
    weather_score -= (max_weather_severity * 10)
    
    # 2. Event/Threat Analysis
    # We need to access Memory Store. This might be slow if we load full DB, 
    # so we'll just check if we can import it.
    event_score = 100
    event_risks = []
    
    try:
        from src.memory_store import memory
        # Get recent events (last 24h)
        recent_events = memory.get_recent_events(limit=50)
        
        # Check intersection
        # Create a simplified corridor (radius 50km for analysis)
        corridor = generate_corridor_points(route.polyline, buffer_km=50)
        
        for event in recent_events:
            loc = event.get("location", "")
            severity = event.get("severity", 5)
            # CRITICAL: Skip geocoding during route analysis to prevent hanging on Nominatim
            coords = get_coordinates_for_location(loc, skip_geocoding=True)
            
            if coords and is_point_in_corridor(coords[0], coords[1], corridor):
                event_risks.append(f"{event.get('topic', 'Event')} in {loc} (Sev: {severity})")
                event_score -= (severity * 5)
                
    except Exception as e:
        print(f"Risk analysis error: {e}")
        
    # 3. Calculate Final Score
    # Weighted: 40% Time (Efficiency), 30% Weather, 30% Events
    # But here we are just comparing risks vs standard.
    # Let's normalize. 
    # Base score 100.
    
    total_score = (weather_score + event_score) / 2
    
    # Adjust for duration? No, score is "Safety/Viability". 
    # Duration is displayed separately.
    
    return {
        "score": max(0, total_score),
        "weather_risks": list(set(weather_risks)),
        "event_risks": list(set(event_risks)),
        "max_weather_severity": max_weather_severity
    }


def generate_corridor_points(polyline: List[List[float]], buffer_km: float = 200) -> List[Tuple[float, float, float]]:
    """
    Generate monitoring points along a route corridor.
    Returns list of (lat, lng, radius_km) tuples for threat detection.
    """
    if not polyline:
        return []
    
    # Sample points every ~100km along the route
    corridor_points = []
    cumulative_dist = 0
    sample_interval = 100  # km
    
    for i in range(len(polyline) - 1):
        lat1, lng1 = polyline[i]
        lat2, lng2 = polyline[i + 1]
        
        segment_dist = haversine_distance(lat1, lng1, lat2, lng2)
        cumulative_dist += segment_dist
        
        if cumulative_dist >= sample_interval:
            corridor_points.append((lat2, lng2, buffer_km))
            cumulative_dist = 0
    
    # Always include start and end points
    if polyline:
        corridor_points.insert(0, (polyline[0][0], polyline[0][1], buffer_km))
        corridor_points.append((polyline[-1][0], polyline[-1][1], buffer_km))
    
    return corridor_points

def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Calculate distance between two points in kilometers.
    """
    R = 6371  # Earth's radius in km
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lng = math.radians(lng2 - lng1)
    
    a = math.sin(delta_lat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lng / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c

def is_point_in_corridor(lat: float, lng: float, corridor_points: List[Tuple[float, float, float]]) -> bool:
    """
    Check if a point is within any corridor circle.
    """
    for cp_lat, cp_lng, radius_km in corridor_points:
        if haversine_distance(lat, lng, cp_lat, cp_lng) <= radius_km:
            return True
    return False

# Location name to coordinates mapping for known supply chain hubs
KNOWN_LOCATIONS = {
    "suez canal": (30.5, 32.3),
    "panama canal": (9.1, -79.7),
    "singapore": (1.3, 103.8),
    "rotterdam": (51.9, 4.5),
    "hamburg": (53.5, 10.0),
    "los angeles": (33.7, -118.2),
    "shanghai": (31.2, 121.5),
    "mumbai": (19.0, 72.8),
    "hong kong": (22.3, 114.2),
    "dubai": (25.2, 55.3),
    "tokyo": (35.7, 139.7),
    "new york": (40.7, -74.0),
    "london": (51.5, -0.1),
    "sydney": (-33.9, 151.2),
    "cape town": (-33.9, 18.4),
    "singapore strait": (1.2, 103.8),
    "strait of malacca": (2.5, 101.0),
    "strait of hormuz": (26.5, 56.5),
    "red sea": (20.0, 38.0),
    "mediterranean": (35.0, 18.0),
    "chennai": (13.08, 80.27),
    "coimbatore": (11.01, 76.95),
    "bangalore": (12.97, 77.59),
    "salem": (11.66, 78.14),
    "highway 44": (11.5, 77.5),
}

def get_coordinates_for_location(location: str, skip_geocoding: bool = False) -> Optional[Tuple[float, float]]:
    """
    Get coordinates for a known location name.
    Fallback to geocoding if not found in cache.
    """
    location_lower = location.lower().strip()
    
    # Check known locations first (faster)
    for name, coords in KNOWN_LOCATIONS.items():
        if name in location_lower or location_lower in name:
            return coords
    
    if skip_geocoding:
        return None
    
    # Fallback to geocoding (SLOWER - Uses external API)
    result = geocode_address(location)
    if result.success:
        return (result.lat, result.lng)
    
    return None
