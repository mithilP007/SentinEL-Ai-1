try:
    import pathway as pw
    # Check if it's the real package by looking for Schema
    if not hasattr(pw, "Schema"):
        raise ImportError("Pathway stub detected")
except ImportError:
    # Windows fallback: Mock Pathway classes so the script loads
    class MockPW:
        class Schema:
            pass
        class io:
            class python:
                @staticmethod
                def read(*args, **kwargs): return "MockTable"
        class sql:
            @staticmethod
            def concat(*args): return "concat"
        class this:
            def __getattr__(self, name): return "col"
            def without(self, *args): return "cols"
        class udfs:
            class DiskCache: pass

    pw = MockPW()
    pw.this = MockPW.this()

import datetime
import json
import random
import time

# --- Schemas ---

class NewsAlert(pw.Schema):
    event_id: str
    timestamp: float
    topic: str
    location: str
    severity: int
    summary: str

class WeatherAlert(pw.Schema):
    alert_id: str
    timestamp: float
    region: str
    condition: str
    severity: int

class ShipmentStatus(pw.Schema):
    shipment_id: str
    timestamp: float
    route_id: str
    current_location: str
    status: str
    eta_days: int

# --- Data Generators (Simulation) ---

def prompt_news_stream():
    """Simulates a live stream of global logistical news."""
    topics = ["Port Strike", "Geopolitical Tension", "Trade Tariff", "Canal Blockage"]
    locations = ["Rotterdam", "Suez Canal", "Singapore", "Hamburg", "Panama Canal"]
    
    while True:
        yield {
            "event_id": f"news_{int(time.time()*1000)}",
            "timestamp": time.time(),
            "topic": random.choice(topics),
            "location": random.choice(locations),
            "severity": random.randint(1, 10),
            "summary": f"Reports of {random.choice(topics)} affecting operations in {random.choice(locations)}."
        }
        time.sleep(random.uniform(2, 5)) # Simulate event frequency

def prompt_weather_stream():
    """Simulates extreme weather alerts."""
    conditions = ["Cyclone", "Heavy Fog", "Flood", "Hurricane"]
    regions = ["North Atlantic", "Indian Ocean", "South China Sea", "Pacific"]
    
    while True:
        yield {
            "alert_id": f"weather_{int(time.time()*1000)}",
            "timestamp": time.time(),
            "region": random.choice(regions),
            "condition": random.choice(conditions),
            "severity": random.randint(1, 10)
        }
        time.sleep(random.uniform(3, 8))

def prompt_shipment_stream():
    """Simulates internal ERP shipment tracking updates."""
    routes = ["Route_A_Suez", "Route_B_Pacific", "Route_C_Atlantic"]
    locations = ["Suez Canal", "Singapore", "Hamburg", "Rotterdam", "Open Sea"]
    
    while True:
        yield {
            "shipment_id": f"SHP_{random.randint(1000, 9999)}",
            "timestamp": time.time(),
            "route_id": random.choice(routes),
            "current_location": random.choice(locations),
            "status": "In Transit",
            "eta_days": random.randint(5, 30)
        }
        time.sleep(random.uniform(1, 3))

# --- Pathway Tables ---

def get_news_table():
    return pw.io.python.read(
        prompt_news_stream,
        schema=NewsAlert,
        mode="streaming"
    )

def get_weather_table():
    return pw.io.python.read(
        prompt_weather_stream,
        schema=WeatherAlert,
        mode="streaming"
    )

def get_shipment_table():
    return pw.io.python.read(
        prompt_shipment_stream,
        schema=ShipmentStatus,
        mode="streaming"
    )
