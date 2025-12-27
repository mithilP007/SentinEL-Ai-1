import time
from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class MetricEvent:
    event_id: str
    occurred_at: float
    detected_at: float
    action_at: Optional[float] = None
    days_saved: float = 0.0

class MetricsTracker:
    def __init__(self):
        self.events: Dict[str, MetricEvent] = {}

    def track_detection(self, event_id: str, occurred_at: float):
        """
        Log when an event is detected by the Observer node.
        """
        # If occurred_at comes in as a string ISO, parse it? 
        # For this system, we rely on float timestamps being passed.
        # If occurred_at is 0 or None, we use current time (immediate detection assumption if data missing)
        now = time.time()
        
        # Guard against future timestamps or invalid ones
        if not occurred_at: occurred_at = now
            
        self.events[event_id] = MetricEvent(
            event_id=event_id,
            occurred_at=float(occurred_at),
            detected_at=now
        )

    def track_action(self, event_id: str, days_saved: float):
        """
        Log when an Action is executed (Act node).
        """
        if event_id in self.events:
            self.events[event_id].action_at = time.time()
            self.events[event_id].days_saved = float(days_saved)

    def get_metrics_snapshot(self):
        # Filter valid events
        valid_detections = [e for e in self.events.values()]
        valid_actions = [e for e in valid_detections if e.action_at is not None]

        # MTTD: Detected - Occurred
        if not valid_detections:
            mttd = None
        else:
            deltas = [(e.detected_at - e.occurred_at) for e in valid_detections]
            deltas = [d for d in deltas if d >= 0]
            mttd = sum(deltas) / len(deltas) if deltas else 0

        # MTTA: Action - Detected
        if not valid_actions:
            mtta = None
        else:
            deltas = [(e.action_at - e.detected_at) for e in valid_actions]
            deltas = [d for d in deltas if d >= 0]
            mtta = sum(deltas) / len(deltas) if deltas else 0

        total_days = sum(e.days_saved for e in valid_actions)
        
        # Advanced Metrics
        COST_PER_DAY = 50000  # $50,000 per day of delay
        cost_saved = total_days * COST_PER_DAY
        events_prevented = len([e for e in valid_actions if e.days_saved > 2])
        
        # Predicted delays = events detected but not yet acted upon
        pending_risks = len(valid_detections) - len(valid_actions)

        return {
            "mttd_seconds": round(mttd, 1) if mttd is not None else None,
            "mtta_seconds": round(mtta, 1) if mtta is not None else None,
            "estimated_days_saved": round(total_days, 1),
            "estimated_cost_saved": int(cost_saved),
            "events_prevented": events_prevented,
            "predicted_delays": pending_risks,
            "events_seen": len(valid_detections),
            "actions_taken": len(valid_actions)
        }

metrics = MetricsTracker()
