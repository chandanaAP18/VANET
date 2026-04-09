# Enhanced VANET Highway Accident Prevention Simulator

An advanced simulation of Vehicular Ad-hoc Networks (VANET) for highway accident prevention, featuring realistic vehicle behaviors, multiple scenarios, data logging, and comprehensive visualization.

> This repository includes a pull-request workflow example branch for merging into `main` and earning GitHub contribution credit.

## Features

### Core VANET Implementation
- **IEEE 802.11p / DSRC**: Dedicated Short-Range Communications for V2V and V2I
- **GPSR Routing**: Greedy Perimeter Stateless Routing for multi-hop message propagation
- **PKI Certificates**: Pseudonymous certificates for secure, privacy-preserving authentication
- **ETSI ITS Standards**: CAM (Cooperative Awareness Messages) and DENM (Decentralized Environmental Notification Messages)
- **Broadcast Storm Suppression**: Distance-based suppression to prevent network flooding
- **RSU Integration**: Road-Side Units for V2I communication and cloud connectivity

### Advanced Accident Prevention Features
- **Real-time Collision Detection**: Continuous monitoring of vehicle positions and speeds
- **Time-to-Collision Calculations**: Precise TTC calculations for imminent collision warnings
- **Automatic Emergency Braking**: AI-driven automatic braking when collisions are imminent
- **Proximity-based Warnings**: Dynamic warnings when vehicles get too close
- **Collision Visualization**: Visual indicators for collision warnings and alerts

### Enhanced Features
- **Multiple Vehicle Types**: Cars, trucks, motorcycles, and emergency vehicles with unique behaviors
- **Traffic Scenarios**: Normal traffic, congested conditions, and emergency response situations
- **Data Logging**: Comprehensive logging of vehicle states, events, and statistics to CSV/JSON files
- **Advanced Visualization**: Real-time charts for message statistics, network connectivity, and speed distributions
- **Configurable Parameters**: JSON-based configuration system for easy customization
- **Modular Architecture**: Separated concerns for better maintainability and extensibility


## Collision Detection System

The simulator now includes a sophisticated collision detection system that goes beyond simple proximity checks:

### Real-time Collision Monitoring
- **Continuous Position Tracking**: Monitors all vehicle positions and velocities in real-time
- **Time-to-Collision (TTC) Calculation**: Computes exact time until collision for approaching vehicles
- **Multi-threshold Warning System**: Different warning levels based on TTC (3s warning, 1.5s critical, 1s emergency)

### Automatic Safety Interventions
- **Collision Warning Alerts**: Visual and textual warnings when vehicles get too close
- **Automatic Emergency Braking**: AI-triggered braking for the faster vehicle when TTC < 1 second
- **DENM Broadcasting**: Automatic dissemination of emergency messages to nearby vehicles

### Visual Indicators
- 🚨 **Collision Warning**: Red alarm symbol for imminent collision danger
- ⚠ **Alert Received**: Yellow warning for vehicles that have received hazard alerts
- 💥 **Accident**: Red vehicle color for crashed vehicles
- 🛑 **Emergency Braking**: Orange vehicle color for vehicles performing emergency stops

### Accident Scenarios
- **Proximity-based Accidents**: Real collisions when vehicles get within 10 meters
- **Simulated Accidents**: Manual accident triggering for demonstration purposes
- **Chain Reaction Prevention**: Warning system prevents secondary accidents

### Scenario Selection
Choose from predefined scenarios:
- **Normal Traffic**: Standard highway conditions
- **Congested Traffic**: Heavy traffic with slower speeds
- **Emergency Response**: Scenarios with emergency vehicles

### Visualization Tabs
- **Simulation**: Main highway view with vehicles and RSUs
- **Statistics**: Real-time charts of message counts and propagation
- **Network**: Visualization of vehicle connectivity and communication ranges
- **Speed Analysis**: Distribution of vehicle speeds


## File Structure

- `main.py`: Main entry point with enhanced GUI
- `vanet_simulator.py`: Core simulation engine
- `config.py`: Configuration management
- `vehicle_types.py`: Different vehicle implementations
- `scenarios.py`: Predefined simulation scenarios
- `data_logger.py`: Data logging and analysis
- `visualization.py`: Additional plotting and visualization
- `config.json`: Configuration file (auto-generated)
- `logs/`: Directory for simulation logs

## Data Logging

The simulator automatically logs:
- **Vehicle States**: Position, speed, lane, status for each vehicle over time
- **Events**: Accidents, emergency braking, and other significant events
- **Statistics**: Message counts, propagation times, and network metrics

Logs are saved in CSV and JSON formats in the `logs/` directory with timestamps.

## Architecture

The simulator uses a modular architecture:
- **Core Engine**: Handles physics, networking, and event propagation
- **GUI Layer**: Tkinter-based interface with real-time visualization
- **Data Layer**: Logging and configuration management
- **Visualization Layer**: Matplotlib-based charts and plots

