# main.py - Main entry point for the enhanced VANET Simulator

import tkinter as tk
from tkinter import ttk, messagebox
from vanet_simulator import VANETSimulator, HIGHWAY_LENGTH
from config import config
from scenarios import SCENARIOS
from data_logger import DataLogger
from visualization import StatsVisualizer, NetworkVisualizer, SpeedDistributionPlot
import os

class EnhancedVANETSimulator(VANETSimulator):
    def __init__(self, root: tk.Tk):
        self.logger = DataLogger()
        self.current_scenario = "normal"
        self.visualizers = []
        super().__init__(root)

    def _build_gui(self):
        # Setup basic window
        self.root.title("Enhanced VANET Highway Accident Prevention Simulator")
        self.root.configure(bg="#0d1117")
        self.root.resizable(True, True)

        # Add scenario selection at the top
        scenario_frame = tk.Frame(self.root, bg="#0d1117")
        scenario_frame.pack(fill=tk.X, padx=8, pady=4)

        tk.Label(scenario_frame, text="🎭 Scenario:", bg="#0d1117", fg="#e6edf3",
                 font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT, padx=6)
        self.scenario_var = tk.StringVar(value="normal")
        scenario_combo = ttk.Combobox(scenario_frame, textvariable=self.scenario_var,
                                     values=list(SCENARIOS.keys()), state="readonly", width=15)
        scenario_combo.pack(side=tk.LEFT, padx=6)
        scenario_combo.bind("<<ComboboxSelected>>", self._change_scenario)

        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        # Simulation tab - will contain the original GUI
        self.sim_tab = tk.Frame(self.notebook)
        self.notebook.add(self.sim_tab, text="Simulation")

        # Temporarily set root to sim_tab for the original GUI building
        original_root = self.root
        self.root = self.sim_tab

        # Build the original GUI in the sim_tab
        self._build_original_gui()

        # Restore original root
        self.root = original_root

        # Add other tabs
        stats_tab = tk.Frame(self.notebook)
        self.notebook.add(stats_tab, text="Statistics")
        self.stats_viz = StatsVisualizer(stats_tab)

        network_tab = tk.Frame(self.notebook)
        self.notebook.add(network_tab, text="Network")
        self.network_viz = NetworkVisualizer(network_tab)

        speed_tab = tk.Frame(self.notebook)
        self.notebook.add(speed_tab, text="Speed Analysis")
        self.speed_viz = SpeedDistributionPlot(speed_tab)

    # ── helper widgets ───────────────────────────────────────────────────────
    def _card(self, parent, title: str) -> tk.Frame:
        outer = tk.Frame(parent, bg="#0d1117")
        outer.pack(fill=tk.X, pady=3)
        tk.Label(outer, text=title, bg="#0d1117", fg="#8b949e",
                 font=("Segoe UI", 8, "bold"), anchor=tk.W,
                 padx=4).pack(fill=tk.X)
        inner = tk.Frame(outer, bg="#21262d", bd=1, relief=tk.FLAT)
        inner.pack(fill=tk.X, padx=1)
        return inner

    def _btn(self, parent, text, cmd, color="#e94560", state=tk.NORMAL) -> tk.Button:
        b = tk.Button(parent, text=text, command=cmd,
                      bg=color, fg="white", relief=tk.FLAT,
                      font=("Segoe UI", 8, "bold"),
                      padx=8, pady=4, cursor="hand2", state=state,
                      activebackground=color, activeforeground="white",
                      bd=0)
        b.pack(side=tk.LEFT, padx=3, pady=2)
        return b

    def _build_original_gui(self):
        """Build the original VANET simulator GUI"""
        # ─ Top bar ─
        topbar = tk.Frame(self.root, bg="#010409", pady=6)
        topbar.pack(fill=tk.X)
        tk.Label(topbar,
                 text="🚗  VANET Highway Accident Prevention Simulator",
                 font=("Segoe UI", 15, "bold"),
                 bg="#010409", fg="#e94560").pack(side=tk.LEFT, padx=14)
        tk.Label(topbar,
                 text="IEEE 802.11p / DSRC · GPSR · PKI · CAM / DENM · DCC",
                 font=("Segoe UI", 8),
                 bg="#010409", fg="#8b949e").pack(side=tk.LEFT, padx=6)

        # ─ Main layout ─
        body = tk.Frame(self.root, bg="#0d1117")
        body.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        left  = tk.Frame(body, bg="#0d1117")
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        right = tk.Frame(body, bg="#0d1117", width=290)
        right.pack(side=tk.RIGHT, fill=tk.Y, padx=(6, 0))
        right.pack_propagate(False)

        # ─ Highway canvas ─
        cf = self._card(left, "🛣  Highway View  (5 km)")
        self.canvas = tk.Canvas(cf, height=195, bg="#010409", highlightthickness=0)
        self.canvas.pack(fill=tk.X, padx=4, pady=4)
        self.canvas.bind("<Configure>", lambda e: self._draw())

        # ─ Controls ─
        cc = self._card(left, "⚙  Controls")
        row1 = tk.Frame(cc, bg="#21262d"); row1.pack(fill=tk.X, padx=6, pady=4)

        self.btn_start  = self._btn(row1, "▶  Start",  self.start,  "#3fb950")
        self.btn_pause  = self._btn(row1, "⏸  Pause",  self.pause,  "#8b949e", state=tk.DISABLED)
        self._btn(row1, "💥  Accident",        self.do_accident,     "#f85149")
        self._btn(row1, "🛑  Emerg. Brake",    self.do_braking,      "#db6d28")
        self._btn(row1, "🔄  Reset",           self.reset,           "#388e3c")
        self._btn(row1, "🔑  Rotate Pseudonyms", self.rotate_all,    "#bc8cff")

        row2 = tk.Frame(cc, bg="#21262d"); row2.pack(fill=tk.X, padx=6, pady=(0, 6))
        tk.Label(row2, text="Vehicles:", bg="#21262d", fg="#8b949e",
                 font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=4)
        self.v_vehicle_n = tk.IntVar(value=config.num_vehicles)
        tk.Scale(row2, from_=4, to=30, orient=tk.HORIZONTAL,
                 variable=self.v_vehicle_n, length=120,
                 bg="#21262d", fg="#58a6ff", troughcolor="#30363d",
                 highlightthickness=0, bd=0).pack(side=tk.LEFT)

        tk.Label(row2, text="  DSRC Range (m):", bg="#21262d", fg="#8b949e",
                 font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=4)
        self.v_dsrc = tk.IntVar(value=config.dsrc_range)
        tk.Scale(row2, from_=100, to=1000, orient=tk.HORIZONTAL,
                 variable=self.v_dsrc, length=130,
                 bg="#21262d", fg="#58a6ff", troughcolor="#30363d",
                 highlightthickness=0, bd=0).pack(side=tk.LEFT)

        # ─ Stats grid ─
        sc = self._card(left, "📊  Live Statistics")
        sg = tk.Frame(sc, bg="#21262d"); sg.pack(fill=tk.X, padx=6, pady=4)
        self._sv: Dict[str, tk.StringVar] = {}
        metrics = [
            ("CAMs Sent",          "cams",      "#3fb950"),
            ("DENMs Broadcast",    "denms",     "#f85149"),
            ("Vehicles Alerted",   "alerted",   "#d29922"),
            ("Avg Propagation",    "avg_ms",    "#58a6ff"),
            ("Broadcasts Suppressed","suppressed","#db6d28"),
            ("RSU Cloud Relays",   "rsu_relays","#bc8cff"),
        ]
        for i, (label, key, color) in enumerate(metrics):
            r, c = divmod(i, 3)
            tk.Label(sg, text=label, bg="#21262d", fg="#8b949e",
                     font=("Segoe UI", 7), anchor=tk.E, width=20
                     ).grid(row=r*2, column=c, padx=6, pady=1, sticky=tk.E)
            sv = tk.StringVar(value="—")
            self._sv[key] = sv
            tk.Label(sg, textvariable=sv, bg="#21262d", fg=color,
                     font=("Segoe UI", 11, "bold"), anchor=tk.W
                     ).grid(row=r*2+1, column=c, padx=6, pady=(0, 6), sticky=tk.W)

        # ─ Legend ─
        lf = tk.Frame(left, bg="#0d1117")
        lf.pack(fill=tk.X, pady=2)
        for color, label in [("#58a6ff","Normal"),("#f85149","Accident"),("#db6d28","Emerg. Brake"),
                             ("#d29922","Alert Received"),("#bc8cff","RSU")]:
            tk.Label(lf, text="●", bg="#0d1117", fg=color,
                     font=("Segoe UI", 11)).pack(side=tk.LEFT, padx=2)
            tk.Label(lf, text=label, bg="#0d1117", fg="#8b949e",
                     font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=(0, 6))

        # ─ Sim time bar ─
        self.v_time = tk.StringVar(value="Sim time: 0.0 s")
        tk.Label(left, textvariable=self.v_time, bg="#0d1117", fg="#8b949e",
                 font=("Courier", 8), anchor=tk.W).pack(fill=tk.X, padx=8)

        # ─ Event log ─
        tk.Label(right, text="📡  Event Log",
                 bg="#0d1117", fg="#e94560", font=("Segoe UI", 10, "bold"),
                 anchor=tk.W).pack(fill=tk.X, padx=4, pady=(4, 2))
        lf2 = tk.Frame(right, bg="#010409")
        lf2.pack(fill=tk.BOTH, expand=True)
        sb = tk.Scrollbar(lf2, bg="#161b22")
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.log = tk.Text(lf2, bg="#010409", fg="#3fb950",
                           font=("Courier New", 8),
                           state=tk.DISABLED, wrap=tk.WORD,
                           yscrollcommand=sb.set, bd=0,
                           selectbackground="#30363d")
        sb.config(command=self.log.yview)
        self.log.pack(fill=tk.BOTH, expand=True)
        for tag, col in [("R","#f85149"),("O","#db6d28"),("G","#3fb950"),
                         ("Y","#d29922"),("B","#58a6ff"),("P","#bc8cff"),("W","#e6edf3")]:
            self.log.tag_configure(tag, foreground=col)

    def _change_scenario(self, event=None):
        self.current_scenario = self.scenario_var.get()
        self.reset()

    def _init_sim(self):
        super()._init_sim()
        # Use scenario to setup vehicles with the actual highway length
        scenario = SCENARIOS[self.current_scenario]
        self.vehicles = scenario.setup_vehicles(HIGHWAY_LENGTH, self.v_vehicle_n.get())
        self.emit(f"Loaded scenario: {scenario.name}", "B")
        self.emit(scenario.description, "B")

    def _loop(self):
        if self.running:
            # Log data
            self.logger.log_vehicle_state(self.sim_time, self.vehicles)
            self.logger.log_stats(self.sim_time, self.S)

            # Update visualizers
            self.stats_viz.update_stats(self.sim_time, self.S)
            self.network_viz.update_network(self.vehicles, self.v_dsrc.get())
            self.speed_viz.update_speeds(self.vehicles)

        super()._loop()

    def do_accident(self):
        super().do_accident()
        self.logger.log_event(self.sim_time, "accident", {"victim": self.vehicles[-1].id if self.vehicles else "unknown"})

    def do_braking(self):
        super().do_braking()
        self.logger.log_event(self.sim_time, "emergency_braking", {"victim": self.vehicles[-1].id if self.vehicles else "unknown"})

    def reset(self):
        super().reset()
        # Save logs when resetting
        if self.logger.vehicle_log:
            self.logger.save_logs()
            summary = self.logger.get_summary_stats()
            self.emit(f"Session saved. Summary: {summary}", "G")
            self.logger = DataLogger()  # Reset logger for new session

def main():
    # Load configuration
    config.load_from_file()

    root = tk.Tk()
    root.title("Enhanced VANET Highway Accident Prevention Simulator")
    root.geometry("1400x900")
    root.minsize(1200, 700)

    app = EnhancedVANETSimulator(root)

    # Save config on exit
    def on_closing():
        config.save_to_file()
        app.logger.save_logs()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()