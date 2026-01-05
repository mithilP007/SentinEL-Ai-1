"""
Live Weather Service for SentinEL
REAL weather data from Open-Meteo API - FREE, NO API KEY REQUIRED
https://open-meteo.com/
"""
import requests
import time
from typing import List, Dict, Optional
from dataclasses import dataclass

@dataclass
class WeatherAlert:
    location: str
    lat: float
    lng: float
    condition: str
    temperature: float
    wind_speed: float
    humidity: float
    severity: int  # 1-10 scale
    description: str
    timestamp: float

# Weather code mapping from Open-Meteo
# https://open-meteo.com/en/docs
WMO_CODES = {
    0: ("Clear sky", 1),
    1: ("Mainly clear", 1),
    2: ("Partly cloudy", 2),
    3: ("Overcast", 3),
    45: ("Fog", 7),
    48: ("Depositing rime fog", 8),
    51: ("Light drizzle", 3),
    53: ("Moderate drizzle", 4),
    55: ("Dense drizzle", 5),
    56: ("Light freezing drizzle", 6),
    57: ("Dense freezing drizzle", 7),
    61: ("Slight rain", 4),
    63: ("Moderate rain", 5),
    65: ("Heavy rain", 7),
    66: ("Light freezing rain", 7),
    67: ("Heavy freezing rain", 8),
    71: ("Slight snow", 5),
    73: ("Moderate snow", 6),
    75: ("Heavy snow", 8),
    77: ("Snow grains", 5),
    80: ("Slight rain showers", 4),
    81: ("Moderate rain showers", 5),
    82: ("Violent rain showers", 8),
    85: ("Slight snow showers", 5),
    86: ("Heavy snow showers", 7),
    95: ("Thunderstorm", 8),
    96: ("Thunderstorm with slight hail", 9),
    99: ("Thunderstorm with heavy hail", 10),
}

def get_weather_info(weather_code: int) -> tuple:
    """Get weather condition and base severity from WMO code."""
    return WMO_CODES.get(weather_code, ("Unknown", 5))

def calculate_severity(weather_code: int, wind_speed: float, humidity: float) -> int:
    """Calculate overall weather severity for shipping (1-10)."""
    condition, base_severity = get_weather_info(weather_code)
    
    # Wind speed factor (km/h) - strong winds dangerous for ships
    if wind_speed > 90:  # Hurricane force
        base_severity = max(base_severity, 10)
    elif wind_speed > 70:  # Storm
        base_severity = max(base_severity, 8)
    elif wind_speed > 50:  # Strong gale
        base_severity = max(base_severity, 6)
    elif wind_speed > 30:  # Strong wind
        base_severity = max(base_severity, 4)
    
    return min(base_severity, 10)

def fetch_weather_for_point(lat: float, lng: float) -> Optional[WeatherAlert]:
    """
    Fetch current weather for a single point using Open-Meteo API.
    FREE - NO API KEY REQUIRED - REAL DATA
    """
    try:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lng,
            "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
            "timezone": "auto"
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code != 200:
            print(f"[WEATHER] API error for ({lat}, {lng}): {response.status_code}")
            return None
        
        data = response.json()
        current = data.get("current", {})
        
        weather_code = current.get("weather_code", 0)
        temperature = current.get("temperature_2m", 0)
        wind_speed = current.get("wind_speed_10m", 0)
        humidity = current.get("relative_humidity_2m", 0)
        
        condition, _ = get_weather_info(weather_code)
        severity = calculate_severity(weather_code, wind_speed, humidity)
        
        # Try to get location name via reverse geocoding
        # SKIP to prevent Nominatim rate limiting/timeouts during bulk analysis
        # location_name = get_location_name(lat, lng)
        location_name = f"{lat:.2f}, {lng:.2f}"
        
        return WeatherAlert(
            location=location_name,
            lat=lat,
            lng=lng,
            condition=condition,
            temperature=temperature,
            wind_speed=wind_speed,
            humidity=humidity,
            severity=severity,
            description=f"{condition}, {temperature}°C, Wind: {wind_speed} km/h",
            timestamp=time.time()
        )
        
    except Exception as e:
        print(f"[WEATHER] Error fetching weather: {e}")
        return None

def get_location_name(lat: float, lng: float) -> str:
    """Get location name using free Nominatim reverse geocoding."""
    try:
        url = "https://nominatim.openstreetmap.org/reverse"
        params = {
            "lat": lat,
            "lon": lng,
            "format": "json",
            "zoom": 10
        }
        headers = {"User-Agent": "SentinEL-SupplyChain-Monitor/2.0"}
        
        response = requests.get(url, params=params, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            # Try to get city, state, or country
            address = data.get("address", {})
            city = address.get("city") or address.get("town") or address.get("village")
            country = address.get("country", "")
            
            if city:
                return f"{city}, {country}"
            return data.get("display_name", f"Point ({lat:.2f}, {lng:.2f})")[:50]
    except:
        pass
    return f"Point ({lat:.2f}, {lng:.2f})"

def fetch_weather_along_route(waypoints: List[Dict]) -> List[WeatherAlert]:
    """
    Fetch weather for waypoints along a route.
    Uses Open-Meteo API - FREE, NO API KEY REQUIRED.
    """
    alerts = []
    
    # Sample waypoints - don't call API for every single one
    # Take max 10 points evenly distributed
    step = max(1, len(waypoints) // 10)
    sampled_waypoints = waypoints[::step][:10]
    
    for wp in sampled_waypoints:
        alert = fetch_weather_for_point(wp["lat"], wp["lng"])
        if alert:
            alerts.append(alert)
        time.sleep(0.5)  # Be nice to the free API
    
    return alerts

def get_weather_summary_for_route(start: tuple, end: tuple) -> Dict:
    """
    Get a quick weather summary for a route (start and end points only).
    Useful for initial route assessment.
    FREE - NO API KEY REQUIRED.
    """
    summary = {
        "start_weather": None,
        "end_weather": None,
        "max_severity": 0,
        "alerts": []
    }
    
    start_weather = fetch_weather_for_point(start[0], start[1])
    if start_weather:
        summary["start_weather"] = {
            "condition": start_weather.condition,
            "temp": start_weather.temperature,
            "wind": start_weather.wind_speed,
            "severity": start_weather.severity
        }
        summary["max_severity"] = max(summary["max_severity"], start_weather.severity)
    
    time.sleep(0.5)  # Rate limiting
    
    end_weather = fetch_weather_for_point(end[0], end[1])
    if end_weather:
        summary["end_weather"] = {
            "condition": end_weather.condition,
            "temp": end_weather.temperature,
            "wind": end_weather.wind_speed,
            "severity": end_weather.severity
        }
        summary["max_severity"] = max(summary["max_severity"], end_weather.severity)
    
    if summary["max_severity"] >= 7:
        summary["alerts"].append("⚠️ Severe weather detected along route")
    elif summary["max_severity"] >= 5:
        summary["alerts"].append("⚡ Moderate weather conditions - monitor closely")
    else:
        summary["alerts"].append("✅ Weather conditions are favorable")
    
    return summary
