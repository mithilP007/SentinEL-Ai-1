import csv
import os
import datetime
from typing import Dict, Any

class MemoryManager:
    def __init__(self, log_file="d:/SENETIAL ai/memory_log.csv"):
        self.log_file = log_file
        self._init_log()

    def _init_log(self):
        if not os.path.exists(self.log_file):
            with open(self.log_file, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["timestamp", "event_id", "shipment_id", "decision", "outcome_score"])

    def log_outcome(self, input_event: Dict[str, Any], decisions: list):
        """
        Logs the decision made for a specific event.
        """
        timestamp = datetime.datetime.now().isoformat()
        with open(self.log_file, "a", newline="") as f:
            writer = csv.writer(f)
            for decision in decisions:
                writer.writerow([
                    timestamp,
                    input_event.get('event_id'),
                    decision.get('shipment_id'),
                    decision.get('recommendation'),
                    0.0 # Placeholder for future feedback loop
                ])
                
    def get_recent_actions(self, limit=5):
        # Could be used by Agent Retrieve to see what we did last time
        pass
