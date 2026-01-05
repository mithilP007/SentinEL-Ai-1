try:
    import pathway as pw
except Exception:
    pw = None
import os
import requests
import json
import time
from src.ingestion import NewsAlert, WeatherAlert, ShipmentStatus, prompt_news_stream, prompt_shipment_stream, prompt_weather_stream

# --- GDELT Live (News) ---
# We poll the GDELT 15-minute update file.
# Note: In a full Pathway deployment, we'd use `pw.io.http.read` directly.
# Here we wrap it slightly to parse the complex GDELT CSV format into our Schema.

# --- Hub Locations for Global Monitoring ---
HUB_LOCATIONS = [
    {"name": "Suez Canal", "lat": 29.9, "lng": 32.5},
    {"name": "Panama Canal", "lat": 9.1, "lng": -79.7},
    {"name": "Singapore Strait", "lat": 1.2, "lng": 103.8},
    {"name": "Strait of Hormuz", "lat": 26.6, "lng": 56.5},
    {"name": "English Channel", "lat": 50.6, "lng": 0.5},
    {"name": "Rotterdam Port", "lat": 51.9, "lng": 4.1},
    {"name": "Shanghai Port", "lat": 31.2, "lng": 121.5},
    {"name": "Malacca Strait", "lat": 2.2, "lng": 102.2},
    {"name": "Chennai Port", "lat": 13.1, "lng": 80.3},
    {"name": "Coimbatore Hub", "lat": 11.0, "lng": 77.0},
    {"name": "Bangalore Logistics", "lat": 12.9, "lng": 77.6},
]

def flow_gdelt_news():
    """
    Reads LIVE GDELT updates - Fetches real global news events.
    """
    import time
    import zipfile
    import io
    import csv
    
    GDELT_UPDATE_URL = "http://data.gdeltproject.org/gdeltv2/lastupdate.txt"
    KEYWORDS = ["strike", "blockage", "tariff", "port", "canal", "shipping", "supply", "transport", "suez", "panama", "embargo", "conflict", "piracy", "storm", "road", "highway", "traffic", "closure", "construction", "festival", "holiday", "event", "parade", "procession", "chennai", "coimbatore", "tamil nadu", "highway 44"]
    
    last_processed_url = None
    event_id_counter = 0
    
    while True:
        try:
            response = requests.get(GDELT_UPDATE_URL, timeout=10)
            if response.status_code != 200:
                time.sleep(30)
                continue
            
            lines = response.text.strip().split('\n')
            export_url = None
            for line in lines:
                if 'export' in line.lower() and '.zip' in line:
                    parts = line.split()
                    for part in parts:
                        if part.startswith('http'):
                            export_url = part
                            break
                    if export_url: break
            
            if not export_url or export_url == last_processed_url:
                time.sleep(60)
                continue
            
            last_processed_url = export_url
            print(f"[LIVE GDELT] Processing: {export_url}")
            zip_response = requests.get(export_url, timeout=30)
            
            if zip_response.status_code == 200:
                z = zipfile.ZipFile(io.BytesIO(zip_response.content))
                csv_name = z.namelist()[0]
                
                with z.open(csv_name) as f:
                    reader = csv.reader(io.TextIOWrapper(f, encoding='utf-8'), delimiter='\t')
                    events_found = 0
                    
                    for row in reader:
                        if len(row) < 60: continue
                        
                        # Col 57: Actor1Geo_FullName, Col 60: SOURCEURL
                        location_full = row[57] if row[57] else "Global"
                        source_url = row[60] if row[60] else ""
                        
                        full_content = (location_full + " " + source_url).lower()
                        
                        if any(kw in full_content for kw in KEYWORDS):
                            event_id_counter += 1
                            
                            # Intelligent topic mapping
                            topic = "Geopolitical Tension"
                            if "strike" in full_content: topic = "Port Strike"
                            elif "block" in full_content: topic = "Canal Blockage" 
                            elif "tariff" in full_content: topic = "Trade Tariff"
                            elif "piracy" in full_content or "conflict" in full_content: topic = "Security Threat"
                            elif "storm" in full_content or "flood" in full_content: topic = "Natural Disaster"
                            elif any(k in full_content for k in ["road", "highway", "traffic", "closure", "construction"]): topic = "Road Condition"
                            elif any(k in full_content for k in ["festival", "holiday", "event", "parade", "procession"]): topic = "Holiday/Event"
                            
                            yield {
                                "event_id": f"gdelt_{int(time.time())}_{event_id_counter}",
                                "topic": topic,
                                "location": location_full.split(',')[0], # Use shortest name
                                "summary": f"[LIVE] {topic} detected at {location_full}",
                                "severity": 6 if any(x in topic.lower() for x in ["strike", "block", "security"]) else 4,
                                "timestamp_epoch": time.time()
                            }
                            events_found += 1
                            if events_found >= 10: break # Process more events
        except Exception as e:
            print(f"[GDELT ERROR] {e}")
        
        time.sleep(60) # Reduced from 300 to 60 for faster demo updates

def flow_openweather():
    """
    REAL Hub Weather Monitoring using Open-Meteo (No Key Required).
    """
    import random
    from src.weather_live import fetch_weather_for_point
    
    while True:
        # Sample a random global transport hub
        hub = random.choice(HUB_LOCATIONS)
        weather = fetch_weather_for_point(hub["lat"], hub["lng"])
        
        if weather and weather.severity >= 4:
            yield {
                "alert_id": f"weather_{int(time.time())}",
                "timestamp": time.time(),
                "region": hub["name"],
                "condition": weather.condition,
                "severity": weather.severity
            }
        
        time.sleep(random.uniform(10, 20))

def flow_ais():
    """
    Hybrid AIS Stream - Real ship names and routes.
    """
    import random
    
    # Real current ships often found in AIS
    REAL_SHIPS = [
        "EVER GIVEN", "MSC OSCAR", "OOCL HONG KONG", "MADRID MAERSK", 
        "CMA CGM ANTOINE DE SAINT EXUPERY", "HMM ALGECIRAS", "MOL TRIUMPH",
        "COSCO SHIPPING UNIVERSE", "NYK BLUE JAY", "ONE APUS"
    ]
    
    while True:
        hub = random.choice(HUB_LOCATIONS)
        ship = random.choice(REAL_SHIPS)
        
        yield {
            "shipment_id": f"AIS_{ship.replace(' ', '_')}",
            "timestamp": time.time(),
            "route_id": f"GLOBAL_{hub['name'].replace(' ', '_')}",
            "current_location": hub["name"],
            "status": "In Transit",
            "eta_days": random.randint(2, 25),
            "cargo_type": "Containers"
        }
        time.sleep(random.uniform(5, 15))

# --- Table Definitions (Pathway compatible) ---

def get_live_news_table():
    if not pw: return None
    return pw.io.python.read(flow_gdelt_news, schema=NewsAlert, mode="streaming")

def get_live_weather_table():
    if not pw: return None
    return pw.io.python.read(flow_openweather, schema=WeatherAlert, mode="streaming")

def get_live_shipment_table():
    if not pw: return None
    return pw.io.python.read(flow_ais, schema=ShipmentStatus, mode="streaming")
