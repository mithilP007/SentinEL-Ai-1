"""
Actionable Suggestions Engine for Sentinel Core v1.1
Generates context-aware recommendations with confidence scores.
"""

from typing import List, Dict, Any

def generate_suggestions(event_type: str, risk_score: float, location: str) -> List[Dict[str, Any]]:
    """
    Generate actionable suggestions based on event context.
    Each suggestion has: action, description, confidence, priority.
    """
    suggestions = []
    
    # High-risk actions (>80)
    if risk_score > 80:
        suggestions.append({
            "action": "REROUTE_SHIPMENT",
            "description": f"Immediately reroute all shipments passing through {location}",
            "confidence": 0.95,
            "priority": "CRITICAL",
            "auto_execute": True
        })
        suggestions.append({
            "action": "NOTIFY_STAKEHOLDERS",
            "description": "Send emergency alerts to all affected parties",
            "confidence": 0.92,
            "priority": "CRITICAL",
            "auto_execute": True
        })
    
    # Medium-risk actions (50-80)
    if risk_score > 50:
        suggestions.append({
            "action": "PRIORITIZE_CRITICAL",
            "description": "Expedite time-sensitive and perishable cargo",
            "confidence": 0.85,
            "priority": "HIGH",
            "auto_execute": False
        })
        suggestions.append({
            "action": "SCHEDULE_ALTERNATIVE",
            "description": "Pre-book alternative transport routes",
            "confidence": 0.78,
            "priority": "HIGH",
            "auto_execute": False
        })
    
    # Event-type specific suggestions
    if event_type == "BLOCKAGE" or event_type == "Canal Blockage":
        suggestions.append({
            "action": "ACTIVATE_CAPE_ROUTE",
            "description": "Switch to Cape of Good Hope route for Suez-bound cargo",
            "confidence": 0.88,
            "priority": "HIGH",
            "auto_execute": risk_score > 85
        })
    
    if event_type == "STRIKE" or event_type == "Port Strike":
        suggestions.append({
            "action": "DIVERT_TO_NEARBY_PORT",
            "description": f"Redirect vessels to nearest operational port",
            "confidence": 0.82,
            "priority": "HIGH",
            "auto_execute": False
        })
    
    if event_type == "TARIFF" or event_type == "Trade Tariff":
        suggestions.append({
            "action": "OPTIMIZE_CUSTOMS",
            "description": "Pre-clear documentation to minimize delays",
            "confidence": 0.75,
            "priority": "MEDIUM",
            "auto_execute": False
        })
    
    # Sort by confidence
    suggestions.sort(key=lambda x: -x["confidence"])
    
    return suggestions[:5]  # Top 5 suggestions


def should_auto_execute(suggestion: Dict[str, Any]) -> bool:
    """
    Determine if an action should be auto-executed by the agent.
    """
    return suggestion.get("auto_execute", False) and suggestion.get("confidence", 0) > 0.9
