# vehicle_types.py - Different types of vehicles with unique behaviors

from vanet_simulator import Vehicle
import random

class Car(Vehicle):
    """Standard passenger car"""
    def __init__(self, position, speed, lane):
        super().__init__(position, speed, lane)
        self.type = "car"
        self.max_speed = 150
        self.acceleration = 2.0  # m/s²

class Truck(Vehicle):
    """Heavy truck with slower acceleration"""
    def __init__(self, position, speed, lane):
        super().__init__(position, speed, lane)
        self.type = "truck"
        self.max_speed = 100
        self.acceleration = 1.0
        self.color = "#8B4513"  # brown

    def update(self, dt):
        # Trucks have slower acceleration
        if not self.in_accident and self.speed < self.max_speed:
            self.speed = min(self.max_speed, self.speed + self.acceleration * dt * 3.6)
        super().update(dt)

class Motorcycle(Vehicle):
    """Motorcycle with high speed and agility"""
    def __init__(self, position, speed, lane):
        super().__init__(position, speed, lane)
        self.type = "motorcycle"
        self.max_speed = 180
        self.acceleration = 3.0
        self.color = "#FF4500"  # orange-red

    def update(self, dt):
        # Motorcycles can weave between lanes occasionally
        if random.random() < 0.01:  # 1% chance per update
            self.lane = 3 - self.lane  # Switch lanes
        super().update(dt)

class EmergencyVehicle(Vehicle):
    """Emergency vehicle with priority and special behaviors"""
    def __init__(self, position, speed, lane):
        super().__init__(position, speed, lane)
        self.type = "emergency"
        self.max_speed = 200
        self.color = "#FF0000"  # bright red
        self.priority = True

    def update(self, dt):
        # Emergency vehicles can exceed speed limits
        if not self.in_accident:
            self.speed = min(self.max_speed, self.speed + 4.0 * dt * 3.6)
        super().update(dt)

def create_vehicle_by_type(vehicle_type, position, speed, lane):
    """Factory function to create vehicles of different types"""
    types = {
        "car": Car,
        "truck": Truck,
        "motorcycle": Motorcycle,
        "emergency": EmergencyVehicle
    }
    return types.get(vehicle_type, Car)(position, speed, lane)