# scenarios.py - Predefined simulation scenarios

from vehicle_types import create_vehicle_by_type
import random

class Scenario:
    def __init__(self, name, description):
        self.name = name
        self.description = description

    def setup_vehicles(self, highway_length, num_vehicles):
        """Override this method to setup vehicles for the scenario"""
        return []

class NormalTrafficScenario(Scenario):
    def __init__(self):
        super().__init__("Normal Traffic", "Standard highway traffic with mixed vehicle types")

    def setup_vehicles(self, highway_length, num_vehicles):
        vehicles = []
        spacing = highway_length / (num_vehicles + 1)
        vehicle_types = ["car", "car", "car", "truck", "motorcycle"]

        for i in range(num_vehicles):
            pos = spacing * (i + 1) + random.uniform(-spacing*0.3, spacing*0.3)
            pos = max(50, min(highway_length - 50, pos))
            speed = random.uniform(80, 150)
            lane = 1 if i % 2 == 0 else 2
            vehicle_type = random.choice(vehicle_types)
            vehicles.append(create_vehicle_by_type(vehicle_type, pos, speed, lane))
        return vehicles

class CongestedTrafficScenario(Scenario):
    def __init__(self):
        super().__init__("Congested Traffic", "Heavy traffic with slower speeds and more vehicles")

    def setup_vehicles(self, highway_length, num_vehicles):
        vehicles = []
        spacing = highway_length / (num_vehicles * 1.5)  # Closer spacing
        vehicle_types = ["car", "truck", "car", "truck", "car"]

        for i in range(num_vehicles):
            pos = spacing * (i + 1) + random.uniform(-spacing*0.1, spacing*0.1)
            pos = max(50, min(highway_length - 50, pos))
            speed = random.uniform(30, 80)  # Slower speeds
            lane = random.choice([1, 2])
            vehicle_type = random.choice(vehicle_types)
            vehicles.append(create_vehicle_by_type(vehicle_type, pos, speed, lane))
        return vehicles

class EmergencyResponseScenario(Scenario):
    def __init__(self):
        super().__init__("Emergency Response", "Scenario with emergency vehicles responding to incidents")

    def setup_vehicles(self, highway_length, num_vehicles):
        vehicles = []
        spacing = highway_length / (num_vehicles + 1)

        # Add some emergency vehicles
        emergency_positions = [highway_length * 0.3, highway_length * 0.7]
        for pos in emergency_positions:
            vehicles.append(create_vehicle_by_type("emergency", pos, 50, 1))

        # Add regular vehicles
        for i in range(num_vehicles - len(emergency_positions)):
            pos = spacing * (i + 1) + random.uniform(-spacing*0.3, spacing*0.3)
            pos = max(50, min(highway_length - 50, pos))
            # Avoid emergency vehicle positions
            while any(abs(pos - ev.position) < 200 for ev in vehicles if ev.type == "emergency"):
                pos = spacing * (i + 1) + random.uniform(-spacing*0.3, spacing*0.3)
                pos = max(50, min(highway_length - 50, pos))
            speed = random.uniform(80, 150)
            lane = 1 if i % 2 == 0 else 2
            vehicle_type = random.choice(["car", "truck", "motorcycle"])
            vehicles.append(create_vehicle_by_type(vehicle_type, pos, speed, lane))
        return vehicles

# Available scenarios
SCENARIOS = {
    "normal": NormalTrafficScenario(),
    "congested": CongestedTrafficScenario(),
    "emergency": EmergencyResponseScenario()
}