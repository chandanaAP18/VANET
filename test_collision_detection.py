# test_collision_detection.py - Test script for collision detection system

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from vanet_simulator import Vehicle

def test_collision_detection():
    """Test the collision detection algorithms"""

    # Create test vehicles
    v1 = Vehicle(1000, 100, 1)  # Vehicle at 1000m going 100 km/h
    v2 = Vehicle(1100, 80, 1)   # Vehicle at 1100m going 80 km/h (slower, being caught up)
    v3 = Vehicle(1200, 120, 1)  # Vehicle at 1200m going 120 km/h (faster, catching up)

    print("=== VANET Collision Detection Test ===\n")

    # Test 1: Basic distance and range
    print(f"Vehicle 1 position: {v1.position}m, speed: {v1.speed} km/h")
    print(f"Vehicle 2 position: {v2.position}m, speed: {v2.speed} km/h")
    print(f"Distance between V1-V2: {v1.dist(v2):.1f}m")
    print(f"V1 in range of V2 (400m): {v1.in_range(v2, 400)}")
    print()

    # Test 2: Time to collision calculations
    print("Time to Collision Analysis:")
    ttc_1_to_2 = v1.time_to_collision(v2)
    ttc_2_to_1 = v2.time_to_collision(v1)
    ttc_3_to_2 = v3.time_to_collision(v2)

    print(f"V1 → V2 TTC: {ttc_1_to_2:.2f}s ({'SAFE' if ttc_1_to_2 > 5 else 'WARNING' if ttc_1_to_2 > 2 else 'DANGER'})")
    print(f"V2 → V1 TTC: {ttc_2_to_1:.2f}s (∞ = not approaching)")
    print(f"V3 → V2 TTC: {ttc_3_to_2:.2f}s ({'SAFE' if ttc_3_to_2 > 5 else 'WARNING' if ttc_3_to_2 > 2 else 'DANGER'})")
    print()

    # Test 3: Collision warnings
    print("Collision Warning Tests:")
    vehicles = [v1, v2, v3]

    for vehicle in vehicles:
        warnings = vehicle.check_collisions(vehicles)
        if warnings:
            print(f"Vehicle {vehicle.id} collision warnings:")
            for v_self, v_other, ttc in warnings:
                print(f"  Warning: {v_self.id} ↔ {v_other.id}, TTC: {ttc:.2f}s")
        else:
            print(f"Vehicle {vehicle.id}: No collision warnings")

    print()
    print("=== Test Complete ===")
    print("The collision detection system monitors:")
    print("- Real-time position and velocity tracking")
    print("- Time-to-collision calculations for approaching vehicles")
    print("- Automatic warning generation for imminent collisions")
    print("- Emergency braking triggers for critical situations")

if __name__ == "__main__":
    test_collision_detection()