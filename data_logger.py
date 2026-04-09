# data_logger.py - Logging and analysis of simulation data

import csv
import json
import os
from datetime import datetime
from typing import List, Dict, Any

class DataLogger:
    def __init__(self, log_dir="logs"):
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.vehicle_log = []
        self.event_log = []
        self.stats_log = []

    def log_vehicle_state(self, sim_time: float, vehicles: List):
        """Log the state of all vehicles at a given time"""
        for vehicle in vehicles:
            self.vehicle_log.append({
                "time": sim_time,
                "id": vehicle.id,
                "position": vehicle.position,
                "speed": vehicle.speed,
                "lane": vehicle.lane,
                "type": getattr(vehicle, 'type', 'car'),
                "in_accident": vehicle.in_accident,
                "emergency_braking": vehicle.emergency_braking,
                "alert_received": vehicle.alert_received,
                "msgs_forwarded": vehicle.msgs_forwarded,
                "msgs_suppressed": vehicle.msgs_suppressed
            })

    def log_event(self, sim_time: float, event_type: str, details: Dict[str, Any]):
        """Log simulation events"""
        self.event_log.append({
            "time": sim_time,
            "type": event_type,
            **details
        })

    def log_stats(self, sim_time: float, stats: Dict[str, Any]):
        """Log simulation statistics"""
        self.stats_log.append({
            "time": sim_time,
            **stats
        })

    def save_logs(self):
        """Save all logs to files"""
        # Save vehicle log
        with open(os.path.join(self.log_dir, f"vehicles_{self.session_id}.csv"), 'w', newline='') as f:
            if self.vehicle_log:
                writer = csv.DictWriter(f, fieldnames=self.vehicle_log[0].keys())
                writer.writeheader()
                writer.writerows(self.vehicle_log)

        # Save event log
        with open(os.path.join(self.log_dir, f"events_{self.session_id}.json"), 'w') as f:
            json.dump(self.event_log, f, indent=2)

        # Save stats log
        with open(os.path.join(self.log_dir, f"stats_{self.session_id}.csv"), 'w', newline='') as f:
            if self.stats_log:
                writer = csv.DictWriter(f, fieldnames=self.stats_log[0].keys())
                writer.writeheader()
                writer.writerows(self.stats_log)

    def get_summary_stats(self):
        """Generate summary statistics from the logs"""
        if not self.vehicle_log:
            return {}

        total_distance = sum(v["position"] for v in self.vehicle_log if v["time"] == max(vl["time"] for vl in self.vehicle_log))
        accidents = sum(1 for v in self.vehicle_log if v["in_accident"])
        alerts_received = sum(1 for v in self.vehicle_log if v["alert_received"])

        return {
            "total_vehicles": len(set(v["id"] for v in self.vehicle_log)),
            "total_distance_traveled": total_distance,
            "accidents_occurred": accidents,
            "alerts_received": alerts_received,
            "simulation_duration": max(v["time"] for v in self.vehicle_log) if self.vehicle_log else 0
        }