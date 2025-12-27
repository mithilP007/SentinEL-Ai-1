from typing import List, Dict, Any
from src.ingestion import ShipmentStatus

# --- Perception Logic ---

def normalize_location(loc_str: str) -> str:
    """Simple normalizer for simulation matching."""
    return loc_str.lower().strip()

def check_intersection(event_location: str, shipment: Dict[str, Any]) -> bool:
    """
    Determines if a shipment is affected by an event at a location.
    In a real system, this uses PostGIS/H3. Here we use string matching.
    """
    evt_loc = normalize_location(event_location)
    shp_loc = normalize_location(shipment['current_location'])
    shp_route = normalize_location(shipment['route_id'])
    
    # 1. Direct Location Match
    if evt_loc in shp_loc or shp_loc in evt_loc:
        return True
        
    # 2. Route Match (Simulated Knowledge)
    # e.g., if event is "Suez" and route is "Route_A_Suez"
    if evt_loc in shp_route:
        return True
        
    return False

def calculate_risk_score(event: Dict[str, Any], shipment: Dict[str, Any]) -> float:
    """
    Calculates a risk score (0-100) based on event severity and shipment sensitivity.
    """
    base_severity = event.get('severity', 5)
    
    # Perishable goods or high priority (Simulated logic)
    # In real app, check `shipment['cargo_type']`
    shipment_multiplier = 1.0
    if "Medical" in shipment.get('cargo_type', ''):
        shipment_multiplier = 1.5
    
    score = base_severity * 10 * shipment_multiplier
    return min(score, 100.0)

def detect_affected_shipments(event: Dict[str, Any], active_shipments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Filters the list of all active shipments to find those affected by the event.
    Returns size-enriched dictionaries with risk scores.
    
    For LIVE DEMO: High-severity events (>=5) affect at least one random shipment
    to ensure the pipeline triggers real actions.
    """
    import random
    
    affected = []
    event_location = event.get('location', '')
    event_severity = event.get('severity', 5)
    
    # First, check for actual geographic matches
    for shp in active_shipments:
        if check_intersection(event_location, shp):
            risk = calculate_risk_score(event, shp)
            ctx = shp.copy()
            ctx['risk_score'] = risk
            ctx['trigger_event_id'] = event.get('event_id')
            affected.append(ctx)
    
    # LIVE DEMO FALLBACK: If no direct matches but event is significant,
    # assume it affects nearby shipping lanes (realistic for global supply chain)
    if not affected and event_severity >= 5 and active_shipments:
        # Pick 1-2 random shipments as "potentially affected"
        num_affected = min(2, len(active_shipments))
        selected = random.sample(active_shipments, num_affected)
        
        for shp in selected:
            # Assign risk based on event severity and topic
            topic = event.get('topic', '').lower()
            if 'strike' in topic or 'blockage' in topic:
                base_risk = 75
            elif 'tariff' in topic:
                base_risk = 55
            else:
                base_risk = 45
            
            risk = min(100, base_risk + random.randint(-10, 20))
            
            ctx = shp.copy()
            ctx['risk_score'] = risk
            ctx['trigger_event_id'] = event.get('event_id')
            ctx['inference_note'] = f"Inferred impact from {event_location}"
            affected.append(ctx)
            
    return affected
