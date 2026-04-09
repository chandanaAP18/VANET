# config.py - Configuration settings for VANET Simulator

import json
import os

class Config:
    def __init__(self):
        self.highway_length = 5000  # metres
        self.dsrc_range = 400  # metres
        self.rsu_range = 800  # metres
        self.min_speed = 80  # km/h
        self.max_speed = 150  # km/h
        self.suppression_dist = 150  # metres
        self.cam_interval = 1.0  # seconds
        self.sim_fps = 25
        self.sim_speedup = 3.0
        self.num_vehicles = 14
        self.weather_conditions = "clear"  # clear, rain, fog
        self.traffic_density = "normal"  # low, normal, high

    def load_from_file(self, filename="config.json"):
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                data = json.load(f)
                for key, value in data.items():
                    if hasattr(self, key):
                        setattr(self, key, value)

    def save_to_file(self, filename="config.json"):
        data = {key: getattr(self, key) for key in dir(self) if not key.startswith('_') and not callable(getattr(self, key))}
        with open(filename, 'w') as f:
            json.dump(data, f, indent=4)

# Global config instance
config = Config()