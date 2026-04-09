# visualization.py - Additional visualization features

import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter as tk
from typing import List, Dict
import numpy as np

class StatsVisualizer:
    def __init__(self, parent_frame):
        self.parent = parent_frame
        self.fig, (self.ax1, self.ax2) = plt.subplots(2, 1, figsize=(8, 6))
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.parent)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self.time_data = []
        self.cam_data = []
        self.denm_data = []
        self.alerted_data = []

        self.ax1.set_title('Message Statistics Over Time')
        self.ax1.set_xlabel('Time (s)')
        self.ax1.set_ylabel('Count')
        self.line1, = self.ax1.plot([], [], 'g-', label='CAMs')
        self.line2, = self.ax1.plot([], [], 'r-', label='DENMs')
        self.ax1.legend()

        self.ax2.set_title('Alert Propagation')
        self.ax2.set_xlabel('Time (s)')
        self.ax2.set_ylabel('Vehicles Alerted')
        self.line3, = self.ax2.plot([], [], 'b-', label='Alerted Vehicles')

        plt.tight_layout()

    def update_stats(self, sim_time: float, stats: Dict[str, int]):
        self.time_data.append(sim_time)
        self.cam_data.append(stats.get('cams', 0))
        self.denm_data.append(stats.get('denms', 0))
        self.alerted_data.append(stats.get('alerted', 0))

        # Keep only last 100 data points for performance
        if len(self.time_data) > 100:
            self.time_data = self.time_data[-100:]
            self.cam_data = self.cam_data[-100:]
            self.denm_data = self.denm_data[-100:]
            self.alerted_data = self.alerted_data[-100:]

        self.line1.set_data(self.time_data, self.cam_data)
        self.line2.set_data(self.time_data, self.denm_data)
        self.line3.set_data(self.time_data, self.alerted_data)

        for ax in [self.ax1, self.ax2]:
            ax.relim()
            ax.autoscale_view()

        self.canvas.draw()

class NetworkVisualizer:
    def __init__(self, parent_frame):
        self.parent = parent_frame
        self.fig, self.ax = plt.subplots(figsize=(8, 6))
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.parent)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self.ax.set_title('Network Connectivity')
        self.ax.set_xlabel('Position (m)')
        self.ax.set_ylabel('Vehicle ID')
        self.ax.set_xlim(0, 5000)
        self.ax.set_ylim(0, 20)

    def update_network(self, vehicles: List, dsrc_range: int):
        self.ax.clear()
        self.ax.set_title('Network Connectivity')
        self.ax.set_xlabel('Position (m)')
        self.ax.set_ylabel('Vehicle ID')
        self.ax.set_xlim(0, 5000)
        self.ax.set_ylim(0, len(vehicles) + 1)

        # Plot vehicles
        for i, vehicle in enumerate(vehicles):
            self.ax.plot(vehicle.position, i + 1, 'bo', markersize=8)
            self.ax.text(vehicle.position + 50, i + 1, vehicle.id, fontsize=8)

            # Draw communication ranges
            self.ax.plot([vehicle.position - dsrc_range, vehicle.position + dsrc_range],
                        [i + 1, i + 1], 'g-', alpha=0.3)

        # Draw connections between vehicles in range
        for i, v1 in enumerate(vehicles):
            for j, v2 in enumerate(vehicles):
                if i != j and abs(v1.position - v2.position) <= dsrc_range:
                    self.ax.plot([v1.position, v2.position], [i + 1, j + 1], 'r-', alpha=0.5)

        self.canvas.draw()

class SpeedDistributionPlot:
    def __init__(self, parent_frame):
        self.parent = parent_frame
        self.fig, self.ax = plt.subplots(figsize=(6, 4))
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.parent)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self.ax.set_title('Vehicle Speed Distribution')
        self.ax.set_xlabel('Speed (km/h)')
        self.ax.set_ylabel('Number of Vehicles')

    def update_speeds(self, vehicles: List):
        self.ax.clear()
        self.ax.set_title('Vehicle Speed Distribution')
        self.ax.set_xlabel('Speed (km/h)')
        self.ax.set_ylabel('Number of Vehicles')

        speeds = [v.speed for v in vehicles]
        if speeds:
            self.ax.hist(speeds, bins=10, alpha=0.7, color='blue', edgecolor='black')
            self.ax.axvline(np.mean(speeds), color='red', linestyle='dashed', linewidth=2, label=f'Mean: {np.mean(speeds):.1f}')
            self.ax.legend()

        self.canvas.draw()