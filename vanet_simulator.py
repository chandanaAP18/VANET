#!/usr/bin/env python3
"""
VANET Highway Accident Prevention Simulator
============================================
Based on your assignment: Case Study 2 – VANET for Accident Prevention on Highways
Implements: IEEE 802.11p / DSRC | GPSR Routing | PKI Pseudonymous Certificates
            ETSI ITS CAM/DENM | Broadcast Storm Suppression | V2V + V2I + RSU relay
"""

import tkinter as tk
from tkinter import ttk, messagebox
import math
import random
import time
import uuid
import hashlib
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from config import config

# ─── Configuration Constants ──────────────────────────────────────────────────
HIGHWAY_LENGTH   = config.highway_length     # metres (5 km highway)
DEFAULT_DSRC_RANGE = config.dsrc_range    # metres DSRC V2V range  (300–1000 m typical)
RSU_RANGE        = config.rsu_range      # metres RSU coverage
MIN_SPEED        = config.min_speed       # km/h
MAX_SPEED        = config.max_speed      # km/h
SUPPRESSION_DIST = config.suppression_dist      # metres – broadcast suppression threshold
CAM_INTERVAL     = config.cam_interval      # seconds between CAM beacons
SIM_FPS          = config.sim_fps       # target frame rate
SIM_SPEEDUP      = config.sim_speedup      # simulation time multiplier

# ─── Colour Palette ───────────────────────────────────────────────────────────
BG_DARK   = "#0d1117"
BG_PANEL  = "#161b22"
BG_CARD   = "#21262d"
ACCENT    = "#e94560"
TEXT_PRI  = "#e6edf3"
TEXT_SEC  = "#8b949e"
GREEN     = "#3fb950"
YELLOW    = "#d29922"
ORANGE    = "#db6d28"
RED       = "#f85149"
PURPLE    = "#bc8cff"
BLUE      = "#58a6ff"


# ═════════════════════════════════════════════════════════════════════════════
# Data-model classes
# ═════════════════════════════════════════════════════════════════════════════

@dataclass
class Certificate:
    """PKI Pseudonymous Certificate — ensures authenticity without exposing identity."""
    vehicle_id: str
    pseudonym:  str
    issued_at:  float
    expires_at: float
    revoked:    bool = False

    def valid(self, now: float) -> bool:
        return not self.revoked and self.issued_at <= now <= self.expires_at

    def sign(self, data: str) -> str:
        raw = f"{self.pseudonym}:{data}:{self.issued_at}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]


@dataclass
class CAMMessage:
    """Cooperative Awareness Message – periodic beacon (1–10 Hz)."""
    sender_id:  str
    pseudonym:  str
    position:   float   # metres along highway
    speed:      float   # km/h
    heading:    float   # degrees
    timestamp:  float
    msg_type:   str = "CAM"
    msg_id:     str = field(default_factory=lambda: uuid.uuid4().hex[:8])


@dataclass
class DENMMessage:
    """Decentralized Environmental Notification Message – hazard alert."""
    sender_id:      str
    pseudonym:      str
    event_type:     str   # ACCIDENT | EMERGENCY_BRAKING | HAZARD
    position:       float
    speed_at_event: float
    timestamp:      float
    severity:       str   # HIGH | MEDIUM | LOW
    signature:      str = ""
    hop_count:      int   = 0
    msg_id:         str   = field(default_factory=lambda: uuid.uuid4().hex[:8])
    received_by:    List[str] = field(default_factory=list)
    msg_type:       str   = "DENM"


# ═════════════════════════════════════════════════════════════════════════════
# Network nodes
# ═════════════════════════════════════════════════════════════════════════════

class Vehicle:
    """Vehicle with an On-Board Unit (OBU): DSRC radio + GPS + CAN-bus interface."""

    _counter = 0

    def __init__(self, position: float, speed: float, lane: int):
        Vehicle._counter += 1
        self.id   = f"V{Vehicle._counter:02d}"
        self.position  = position    # metres
        self.speed     = speed       # km/h
        self.lane      = lane        # 1 or 2
        self.color     = BLUE

        # OBU state
        self.cert: Certificate = self._new_cert()
        self.received: Dict[str, float] = {}   # msg_id → received_time
        self.cam_timer  = random.uniform(0, CAM_INTERVAL)

        # Event flags
        self.in_accident       = False
        self.emergency_braking = False
        self.alert_received    = False
        self.collision_warning = False

        # Stats per vehicle
        self.msgs_forwarded  = 0
        self.msgs_suppressed = 0

    # ── PKI ──────────────────────────────────────────────────────────────────
    def _new_cert(self) -> Certificate:
        now    = time.time()
        pseudo = hashlib.md5(f"{self.id}:{now}".encode()).hexdigest()[:10]
        return Certificate(self.id, pseudo, now, now + 300)

    def rotate_pseudonym(self):
        self.cert = self._new_cert()

    # ── Motion ───────────────────────────────────────────────────────────────
    def update(self, dt: float):
        if not self.in_accident:
            self.position += (self.speed / 3.6) * dt
            if self.position > HIGHWAY_LENGTH:
                self.position %= HIGHWAY_LENGTH
        self.cam_timer -= dt

    # ── Communication ────────────────────────────────────────────────────────
    def dist(self, other: 'Vehicle') -> float:
        return abs(self.position - other.position)

    def in_range(self, other: 'Vehicle', r: float) -> bool:
        return self.dist(other) <= r

    def time_to_collision(self, other: 'Vehicle') -> float:
        """Calculate time to collision if vehicles continue at current speeds"""
        if self.speed <= other.speed:
            return float('inf')  # Not approaching
        relative_speed = self.speed - other.speed
        distance = abs(self.position - other.position)
        if relative_speed <= 0:
            return float('inf')
        return distance / (relative_speed / 3.6)  # Convert km/h to m/s

    def will_collide(self, other: 'Vehicle', time_horizon: float = 5.0) -> bool:
        """Check if collision is imminent within time horizon"""
        ttc = self.time_to_collision(other)
        return ttc <= time_horizon and ttc > 0

    def make_denm(self, event: str) -> DENMMessage:
        sig = self.cert.sign(f"{event}:{self.position}")
        return DENMMessage(
            sender_id=self.id,
            pseudonym=self.cert.pseudonym,
            event_type=event,
            position=self.position,
            speed_at_event=self.speed,
            timestamp=time.time(),
            severity="HIGH" if event == "ACCIDENT" else "MEDIUM",
            signature=sig,
        )

    def should_suppress(self, alert_pos: float) -> bool:
        """Distance-based broadcast suppression (Torrent-Moreno 2006)."""
        return abs(self.position - alert_pos) < SUPPRESSION_DIST

    # ── Accident / braking ───────────────────────────────────────────────────
    def trigger_accident(self):
        self.in_accident = True
        self.speed = 0
        self.color = RED

    def trigger_braking(self):
        self.emergency_braking = True
        self.speed = max(20, self.speed - 70)
        self.color = ORANGE

    def receive_alert(self):
        self.alert_received = True
        if not self.in_accident and not self.emergency_braking:
            self.color = YELLOW

    def check_collisions(self, vehicles: List['Vehicle']) -> List[tuple]:
        """Check for potential collisions and return warning pairs"""
        warnings = []
        for other in vehicles:
            if other.id == self.id or other.in_accident:
                continue
            if self.will_collide(other, 3.0):  # 3 second warning
                warnings.append((self, other, self.time_to_collision(other)))
        return warnings


class RSU:
    """Road-Side Unit – fixed V2I node bridging VANET to backend."""

    def __init__(self, rid: str, position: float):
        self.id       = rid
        self.position = position
        self.range    = RSU_RANGE
        self.relayed  = 0

    def covers(self, v: Vehicle) -> bool:
        return abs(self.position - v.position) <= self.range

    def relay(self, denm: DENMMessage) -> str:
        self.relayed += 1
        return f"DISPATCH_EMERGENCY + ADJUST_SPEED_LIMITS @ {denm.position:.0f}m"


# ═════════════════════════════════════════════════════════════════════════════
# Simulator + GUI
# ═════════════════════════════════════════════════════════════════════════════

class VANETSimulator:
    """Main simulation engine with Tkinter visualisation."""

    # ── init ─────────────────────────────────────────────────────────────────
    def __init__(self, root: tk.Tk):
        self.root      = root
        self.root.title("VANET Highway Accident Prevention Simulator")
        self.root.configure(bg=BG_DARK)
        self.root.resizable(True, True)

        # Simulation state
        self.vehicles: List[Vehicle]     = []
        self.rsus:     List[RSU]         = []
        self.alerts:   List[DENMMessage] = []
        self.ripples:  List[dict]        = []   # visual expanding circles
        self.running   = False
        self.sim_time  = 0.0
        self._last_t   = time.time()
        self._cam_acc  = 0.0             # accumulator for CAM stat

        # Stats
        self.S = dict(
            cams=0, denms=0, alerted=0,
            suppressed=0, rsu_relays=0, avg_ms=0.0,
            risk=0, min_gap=0.0
        )
        self._prop_times: List[float] = []

        Vehicle._counter = 0

        self._build_gui()
        self._init_sim()

    # ── GUI builder ──────────────────────────────────────────────────────────
    def _build_gui(self):
        # ─ Top bar ─
        topbar = tk.Frame(self.root, bg="#010409", pady=6)
        topbar.pack(fill=tk.X)
        tk.Label(topbar,
                 text="🚗  VANET Highway Accident Prevention Simulator",
                 font=("Segoe UI", 15, "bold"),
                 bg="#010409", fg=ACCENT).pack(side=tk.LEFT, padx=14)
        tk.Label(topbar,
                 text="IEEE 802.11p / DSRC · GPSR · PKI · CAM / DENM · DCC",
                 font=("Segoe UI", 8),
                 bg="#010409", fg=TEXT_SEC).pack(side=tk.LEFT, padx=6)

        # ─ Main layout ─
        body = tk.Frame(self.root, bg=BG_DARK)
        body.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        left  = tk.Frame(body, bg=BG_DARK)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        right = tk.Frame(body, bg=BG_DARK, width=290)
        right.pack(side=tk.RIGHT, fill=tk.Y, padx=(6, 0))
        right.pack_propagate(False)

        # ─ Highway canvas ─
        cf = self._card(left, "🛣  Highway View  (5 km)")
        self.canvas = tk.Canvas(cf, height=195, bg="#010409", highlightthickness=0)
        self.canvas.pack(fill=tk.X, padx=4, pady=4)
        self.canvas.bind("<Configure>", lambda e: self._draw())

        # ─ Controls ─
        cc = self._card(left, "⚙  Controls")
        row1 = tk.Frame(cc, bg=BG_CARD); row1.pack(fill=tk.X, padx=6, pady=4)

        self.btn_start  = self._btn(row1, "▶  Start",  self.start,  GREEN)
        self.btn_pause  = self._btn(row1, "⏸  Pause",  self.pause,  TEXT_SEC, state=tk.DISABLED)
        self._btn(row1, "💥  Accident",        self.do_accident,     RED)
        self._btn(row1, "🛑  Emerg. Brake",    self.do_braking,      ORANGE)
        self._btn(row1, "🔄  Reset",           self.reset,           "#388e3c")
        self._btn(row1, "🔑  Rotate Pseudonyms", self.rotate_all,    PURPLE)

        row2 = tk.Frame(cc, bg=BG_CARD); row2.pack(fill=tk.X, padx=6, pady=(0, 6))
        tk.Label(row2, text="Vehicles:", bg=BG_CARD, fg=TEXT_SEC,
                 font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=4)
        self.v_vehicle_n = tk.IntVar(value=config.num_vehicles)
        tk.Scale(row2, from_=4, to=30, orient=tk.HORIZONTAL,
                 variable=self.v_vehicle_n, length=120,
                 bg=BG_CARD, fg=BLUE, troughcolor="#30363d",
                 highlightthickness=0, bd=0).pack(side=tk.LEFT)

        tk.Label(row2, text="  DSRC Range (m):", bg=BG_CARD, fg=TEXT_SEC,
                 font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=4)
        self.v_dsrc = tk.IntVar(value=DEFAULT_DSRC_RANGE)
        tk.Scale(row2, from_=100, to=1000, orient=tk.HORIZONTAL,
                 variable=self.v_dsrc, length=130,
                 bg=BG_CARD, fg=BLUE, troughcolor="#30363d",
                 highlightthickness=0, bd=0).pack(side=tk.LEFT)

        tk.Label(row2, text="  Weather:", bg=BG_CARD, fg=TEXT_SEC,
                 font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=4)
        self.v_weather = tk.StringVar(value="clear")
        tk.OptionMenu(row2, self.v_weather, "clear", "rain", "fog").pack(side=tk.LEFT, padx=2)

        tk.Label(row2, text="  Safety gap (m):", bg=BG_CARD, fg=TEXT_SEC,
                 font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=4)
        self.v_safety_gap = tk.IntVar(value=100)
        tk.Scale(row2, from_=30, to=200, orient=tk.HORIZONTAL,
                 variable=self.v_safety_gap, length=120,
                 bg=BG_CARD, fg=YELLOW, troughcolor="#30363d",
                 highlightthickness=0, bd=0).pack(side=tk.LEFT)

        # ─ Stats grid ─
        sc = self._card(left, "📊  Live Statistics")
        sg = tk.Frame(sc, bg=BG_CARD); sg.pack(fill=tk.X, padx=6, pady=4)
        self._sv: Dict[str, tk.StringVar] = {}
        metrics = [
            ("CAMs Sent",          "cams",      GREEN),
            ("DENMs Broadcast",    "denms",     RED),
            ("Vehicles Alerted",   "alerted",   YELLOW),
            ("Avg Propagation",    "avg_ms",    BLUE),
            ("Collision Risk",     "risk",      ORANGE),
            ("Min Gap",            "min_gap",   GREEN),
        ]
        for i, (label, key, color) in enumerate(metrics):
            r, c = divmod(i, 3)
            tk.Label(sg, text=label, bg=BG_CARD, fg=TEXT_SEC,
                     font=("Segoe UI", 7), anchor=tk.E, width=20
                     ).grid(row=r*2, column=c, padx=6, pady=1, sticky=tk.E)
            sv = tk.StringVar(value="—")
            self._sv[key] = sv
            tk.Label(sg, textvariable=sv, bg=BG_CARD, fg=color,
                     font=("Segoe UI", 11, "bold"), anchor=tk.W
                     ).grid(row=r*2+1, column=c, padx=6, pady=(0, 6), sticky=tk.W)

        # ─ Legend ─
        lf = tk.Frame(left, bg=BG_DARK)
        lf.pack(fill=tk.X, pady=2)
        for color, label in [(BLUE,"Normal"),(RED,"Accident/Collision Warning"),(ORANGE,"Emerg. Brake"),
                             (YELLOW,"Alert Received"),(PURPLE,"RSU")]:
            tk.Label(lf, text="●", bg=BG_DARK, fg=color,
                     font=("Segoe UI", 11)).pack(side=tk.LEFT, padx=2)
            tk.Label(lf, text=label, bg=BG_DARK, fg=TEXT_SEC,
                     font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=(0, 6))

        # ─ Sim time bar ─
        self.v_time = tk.StringVar(value="Sim time: 0.0 s")
        tk.Label(left, textvariable=self.v_time, bg=BG_DARK, fg=TEXT_SEC,
                 font=("Courier", 8), anchor=tk.W).pack(fill=tk.X, padx=8)

        # ─ Event log ─
        tk.Label(right, text="📡  Event Log",
                 bg=BG_DARK, fg=ACCENT, font=("Segoe UI", 10, "bold"),
                 anchor=tk.W).pack(fill=tk.X, padx=4, pady=(4, 2))
        lf2 = tk.Frame(right, bg="#010409")
        lf2.pack(fill=tk.BOTH, expand=True)
        sb = tk.Scrollbar(lf2, bg=BG_PANEL)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.log = tk.Text(lf2, bg="#010409", fg=GREEN,
                           font=("Courier New", 8),
                           state=tk.DISABLED, wrap=tk.WORD,
                           yscrollcommand=sb.set, bd=0,
                           selectbackground="#30363d")
        sb.config(command=self.log.yview)
        self.log.pack(fill=tk.BOTH, expand=True)
        for tag, col in [("R",RED),("O",ORANGE),("G",GREEN),
                         ("Y",YELLOW),("B",BLUE),("P",PURPLE),("W",TEXT_PRI)]:
            self.log.tag_configure(tag, foreground=col)

    # ── helper widgets ───────────────────────────────────────────────────────
    def _card(self, parent, title: str) -> tk.Frame:
        outer = tk.Frame(parent, bg=BG_DARK)
        outer.pack(fill=tk.X, pady=3)
        tk.Label(outer, text=title, bg=BG_DARK, fg=TEXT_SEC,
                 font=("Segoe UI", 8, "bold"), anchor=tk.W,
                 padx=4).pack(fill=tk.X)
        inner = tk.Frame(outer, bg=BG_CARD, bd=1, relief=tk.FLAT)
        inner.pack(fill=tk.X, padx=1)
        return inner

    def _btn(self, parent, text, cmd, color=ACCENT, state=tk.NORMAL) -> tk.Button:
        b = tk.Button(parent, text=text, command=cmd,
                      bg=color, fg="white", relief=tk.FLAT,
                      font=("Segoe UI", 8, "bold"),
                      padx=8, pady=4, cursor="hand2", state=state,
                      activebackground=color, activeforeground="white",
                      bd=0)
        b.pack(side=tk.LEFT, padx=3, pady=2)
        return b

    # ── logging ──────────────────────────────────────────────────────────────
    def emit(self, msg: str, tag: str = "G"):
        self.log.configure(state=tk.NORMAL)
        ts = f"[{self.sim_time:07.2f}s] "
        self.log.insert(tk.END, ts + msg + "\n", tag)
        self.log.see(tk.END)
        self.log.configure(state=tk.DISABLED)

    # ── simulation init ───────────────────────────────────────────────────────
    def _init_sim(self):
        Vehicle._counter = 0
        self.vehicles.clear(); self.rsus.clear()
        self.alerts.clear();   self.ripples.clear()
        self._prop_times.clear()
        self.sim_time = 0.0
        self.S = dict(cams=0, denms=0, alerted=0, suppressed=0, rsu_relays=0, avg_ms=0.0, risk=0, min_gap=0.0)

        # Vehicles — spread evenly with jitter, two lanes
        n = self.v_vehicle_n.get()
        spacing = HIGHWAY_LENGTH / (n + 1)
        for i in range(n):
            pos  = spacing * (i + 1) + random.uniform(-spacing*0.3, spacing*0.3)
            pos  = max(50, min(HIGHWAY_LENGTH - 50, pos))
            spd  = random.uniform(MIN_SPEED, MAX_SPEED)
            lane = 1 if i % 2 == 0 else 2
            self.vehicles.append(Vehicle(pos, spd, lane))

        # RSUs at 1 km, 2.5 km, 4 km
        for i, p in enumerate([1000, 2500, 4000], 1):
            self.rsus.append(RSU(f"RSU{i}", float(p)))

        self.emit("═══ VANET Simulator Initialised ═══", "W")
        self.emit(f"Vehicles: {n}  |  RSUs: {len(self.rsus)}", "B")
        self.emit(f"DSRC range: {self.v_dsrc.get()} m  |  RSU range: {RSU_RANGE} m", "B")
        self.emit("IEEE 802.11p WAVE active", "G")
        self.emit("PKI pseudonymous certs issued ✓", "G")
        self.emit("ETSI ITS CAM broadcasting at 1–10 Hz", "G")
        self.emit("Press ▶ Start to begin", "Y")
        self.emit("─" * 34, "B")
        self._refresh_stats()
        self._draw()

    # ── controls ─────────────────────────────────────────────────────────────
    def start(self):
        if self.running:
            return
        self.running = True
        self._last_t = time.time()
        self.btn_start.configure(state=tk.DISABLED)
        self.btn_pause.configure(state=tk.NORMAL)
        self.emit("▶ Simulation started — CAMs broadcasting", "G")
        self._loop()

    def pause(self):
        self.running = False
        self.btn_start.configure(state=tk.NORMAL, text="▶ Resume")
        self.btn_pause.configure(state=tk.DISABLED)
        self.emit("⏸ Paused", "Y")

    def reset(self):
        self.running = False
        self.log.configure(state=tk.NORMAL)
        self.log.delete(1.0, tk.END)
        self.log.configure(state=tk.DISABLED)
        self.btn_start.configure(state=tk.NORMAL, text="▶ Start")
        self.btn_pause.configure(state=tk.DISABLED)
        self._init_sim()

    def rotate_all(self):
        for v in self.vehicles:
            v.rotate_pseudonym()
        self.emit("🔑 Pseudonyms rotated for all vehicles (privacy refresh)", "P")

    # ── event triggers ───────────────────────────────────────────────────────
    def do_accident(self):
        # Check for vehicles that are very close to each other (actual collision)
        for i, v1 in enumerate(self.vehicles):
            for v2 in self.vehicles[i+1:]:
                if abs(v1.position - v2.position) < 10:  # Very close (10 meters)
                    # Determine which vehicle "causes" the accident (faster one or random)
                    victim = v1 if v1.speed > v2.speed else v2
                    victim.trigger_accident()
                    denm = victim.make_denm("ACCIDENT")
                    self.emit(f"💥 COLLISION ACCIDENT – {victim.id} & {v1.id if victim==v2 else v2.id}", "R")
                    self.emit(f"   Position: {victim.position:.0f}m  |  Speed: {victim.speed:.0f} km/h", "R")
                    self._broadcast_denm(denm, victim)
                    return

        # If no actual collisions, trigger a random accident for demonstration
        victims = [v for v in self.vehicles
                   if not v.in_accident and 400 < v.position < HIGHWAY_LENGTH - 400]
        if not victims:
            self.emit("⚠ No suitable candidate for accident (try triggering when vehicles are close)", "O"); return
        v = random.choice(victims)
        v.trigger_accident()
        denm = v.make_denm("ACCIDENT")
        self.emit(f"💥 SIMULATED ACCIDENT – {v.id}  pos={v.position:.0f} m", "R")
        self.emit(f"   Severity: HIGH  |  Pseudonym: {v.cert.pseudonym}", "P")
        self._broadcast_denm(denm, v)

    def do_braking(self):
        victims = [v for v in self.vehicles
                   if not v.in_accident and not v.emergency_braking
                   and 300 < v.position < HIGHWAY_LENGTH - 300]
        if not victims:
            self.emit("⚠ No suitable candidate for emergency braking", "O"); return
        v = random.choice(victims)
        v.trigger_braking()
        denm = v.make_denm("EMERGENCY_BRAKING")
        self.emit(f"🛑 EMERGENCY BRAKING – {v.id}  pos={v.position:.0f} m", "O")
        self.emit(f"   Speed now: {v.speed:.0f} km/h  |  Severity: MEDIUM", "O")
        self._broadcast_denm(denm, v)

    # ── VANET propagation core ────────────────────────────────────────────────
    def _broadcast_denm(self, denm: DENMMessage, source: Vehicle):
        """
        Multi-hop V2V broadcast with distance-based suppression (GPSR-style).
        Each vehicle checks if it should re-broadcast based on its distance
        from the alert origin — close nodes suppress to avoid broadcast storm.
        """
        self.alerts.append(denm)
        self.S["denms"] += 1
        self._add_ripple(source.position)

        dsrc = self._effective_dsrc_range()
        t0   = time.time()
        seen = {source.id}
        queue: List[tuple] = [(source, 0, t0)]  # (node, hop, abs_time)

        while queue:
            node, hop, t_node = queue.pop(0)

            # ── V2V delivery ──
            for v in self.vehicles:
                if v.id in seen: continue
                if abs(v.position - node.position) > dsrc: continue

                prop_ms = (time.time() - t0) * 1000 + random.uniform(1, 8)
                seen.add(v.id)
                denm.received_by.append(v.id)
                v.received[denm.msg_id] = time.time()
                v.receive_alert()

                self._prop_times.append(prop_ms)
                self.S["alerted"]  = len(denm.received_by)
                self.S["avg_ms"]   = sum(self._prop_times) / len(self._prop_times)

                ms_color = "G" if prop_ms < 100 else "O"
                self.emit(
                    f"   📡 {v.id}←DENM  hop={hop+1}  {prop_ms:.1f}ms",
                    ms_color
                )

                # Broadcast suppression decision
                if v.should_suppress(denm.position):
                    v.msgs_suppressed += 1
                    self.S["suppressed"] += 1
                    self.emit(f"   ↳ {v.id} SUPPRESSED (too close to source)", "Y")
                else:
                    v.msgs_forwarded += 1
                    t_fwd = t_node + random.uniform(0.001, 0.006)
                    queue.append((v, hop + 1, t_fwd))

            # ── V2I RSU delivery ──
            for rsu in self.rsus:
                if abs(node.position - rsu.position) <= rsu.range:
                    action = rsu.relay(denm)
                    self.S["rsu_relays"] += 1
                    self.emit(f"   🏢 {rsu.id}→Cloud: {action}", "P")

        self._add_ripple(source.position)   # second ripple for visual effect
        self.emit(
            f"✔ DENM propagated to {len(denm.received_by)} vehicles  "
            f"avg={self.S['avg_ms']:.1f}ms  "
            f"suppressed={self.S['suppressed']}",
            "G"
        )
        self._refresh_stats()

    # ── main loop ─────────────────────────────────────────────────────────────
    def _loop(self):
        if not self.running:
            return
        now = time.time()
        dt  = (now - self._last_t) * SIM_SPEEDUP
        self._last_t = now
        self.sim_time += dt

        # Check for collisions and warnings
        self._check_for_warnings()

        # Move vehicles
        for v in self.vehicles:
            v.update(dt)

        # CAM counter (approximate)
        self._cam_acc += dt
        if self._cam_acc >= CAM_INTERVAL:
            self._cam_acc -= CAM_INTERVAL
            self.S["cams"] += len(self.vehicles)

        # Risk analysis
        self._analyze_collision_risk()
        self._refresh_stats()

        # Ripple animation
        for r in self.ripples[:]:
            r["radius"] += 5
            r["alpha"]  -= 0.025
            if r["alpha"] <= 0:
                self.ripples.remove(r)

        weather_var = getattr(self, "v_weather", None)
        weather_label = weather_var.get().capitalize() if weather_var is not None else "Clear"
        self.v_time.set(
            f"Sim time: {self.sim_time:.1f} s  |  "
            f"Vehicles: {len(self.vehicles)}  |  "
            f"Speed-up: {SIM_SPEEDUP}×  |  "
            f"Weather: {weather_label}"
        )
        self._draw()
        self.root.after(1000 // SIM_FPS, self._loop)

    def _check_for_warnings(self):
        """Check for potential collisions and trigger warnings"""
        # Clear previous collision warnings
        for vehicle in self.vehicles:
            vehicle.collision_warning = False

        all_warnings = []
        for vehicle in self.vehicles:
            if not vehicle.in_accident:
                warnings = vehicle.check_collisions(self.vehicles)
                all_warnings.extend(warnings)

        # Process warnings (avoid duplicates)
        processed_pairs = set()
        for v1, v2, ttc in all_warnings:
            pair_key = tuple(sorted([v1.id, v2.id]))
            if pair_key not in processed_pairs:
                processed_pairs.add(pair_key)
                self._trigger_collision_warning(v1, v2, ttc)

    def _trigger_collision_warning(self, v1: Vehicle, v2: Vehicle, ttc: float):
        """Trigger warning for imminent collision"""
        # Set warning flags
        v1.collision_warning = True
        v2.collision_warning = True

        # Only warn if vehicles haven't been warned recently
        warning_key = f"{min(v1.id, v2.id)}-{max(v1.id, v2.id)}"
        if not hasattr(self, '_last_warnings'):
            self._last_warnings = {}

        last_warn = self._last_warnings.get(warning_key, 0)
        if self.sim_time - last_warn > 2.0:  # Don't spam warnings
            self._last_warnings[warning_key] = self.sim_time

            severity = "HIGH" if ttc < 1.5 else "MEDIUM"
            color = RED if severity == "HIGH" else ORANGE

            self.emit(f"⚠ COLLISION WARNING – {v1.id} & {v2.id}  TTC: {ttc:.1f}s", "O" if severity == "MEDIUM" else "R")
            self.emit(f"   Positions: {v1.position:.0f}m, {v2.position:.0f}m  |  Speeds: {v1.speed:.0f}, {v2.speed:.0f} km/h", "Y")

            # Trigger automatic braking for the faster vehicle if very close
            if ttc < 1.0 and not v1.emergency_braking and not v2.emergency_braking:
                faster_vehicle = v1 if v1.speed > v2.speed else v2
                self._trigger_automatic_braking(faster_vehicle)

    def _trigger_automatic_braking(self, vehicle: Vehicle):
        """Automatically trigger emergency braking for collision avoidance"""
        vehicle.trigger_braking()
        denm = vehicle.make_denm("EMERGENCY_BRAKING")
        self.emit(f"🚨 AUTO-BRAKE – {vehicle.id}  Speed now: {vehicle.speed:.0f} km/h", "R")
        self._broadcast_denm(denm, vehicle)

    def _effective_dsrc_range(self) -> float:
        """Apply weather attenuation to DSRC range."""
        base = self.v_dsrc.get()
        weather_var = getattr(self, "v_weather", None)
        weather = weather_var.get() if weather_var is not None else "clear"
        if weather == "rain":
            return base * 0.85
        if weather == "fog":
            return base * 0.75
        return base

    def _analyze_collision_risk(self):
        """Compute a collision risk score and minimum gap from the current traffic."""
        min_gap = float("inf")
        imminent = 0
        safety_gap = getattr(self, "v_safety_gap", None)
        gap_threshold = safety_gap.get() if safety_gap is not None else 100
        for i, v1 in enumerate(self.vehicles):
            for v2 in self.vehicles[i+1:]:
                gap = abs(v1.position - v2.position)
                min_gap = min(min_gap, gap)
                if gap < gap_threshold and v1.will_collide(v2, 4.0):
                    imminent += 1

        if min_gap == float("inf"):
            min_gap = 0.0

        self.S["min_gap"] = min_gap
        self.S["risk"] = min(100, imminent * 30)

    # ── drawing ───────────────────────────────────────────────────────────────
    def _draw(self):
        c  = self.canvas
        c.delete("all")
        W  = c.winfo_width()  or 860
        H  = 195
        sc = W / HIGHWAY_LENGTH     # pixels per metre

        # Sky / road background
        c.create_rectangle(0, 0, W, H, fill="#010409", outline="")

        # Ground strip
        c.create_rectangle(0, H - 20, W, H, fill="#0d1117", outline="")

        # Road body
        r_top, r_bot = 55, 140
        c.create_rectangle(0, r_top, W, r_bot, fill="#1c1c1c", outline="")
        # Shoulder lines
        c.create_line(0, r_top,     W, r_top,     fill="#e0e0e0", width=2)
        c.create_line(0, r_bot,     W, r_bot,     fill="#e0e0e0", width=2)
        # Centre dashes
        mid = (r_top + r_bot) // 2
        for x in range(0, W, 28):
            c.create_line(x, mid, x + 14, mid, fill="#d4ac0d", width=2)

        # km markers
        for km in range(6):
            mx = int(km * 1000 * sc)
            c.create_line(mx, r_bot, mx, r_bot + 8, fill="#444")
            c.create_text(mx, r_bot + 14, text=f"{km} km",
                          fill="#555", font=("Segoe UI", 6))

        # ── Ripple rings ──
        for r in self.ripples:
            rx = int(r["position"] * sc)
            rad = int(r["radius"])
            alpha = int(r["alpha"] * 255)
            col = f"#{alpha:02x}{alpha // 4:02x}{alpha // 4:02x}"
            c.create_oval(rx - rad, mid - rad // 2,
                          rx + rad, mid + rad // 2,
                          outline=col, width=2)

        # ── DSRC range arc for active alerts ──
        dsrc = self._effective_dsrc_range()
        for denm in self.alerts:
            ax = int(denm.position * sc)
            dr = int(dsrc * sc)
            c.create_oval(ax - dr, r_top - 8,
                          ax + dr, r_bot + 8,
                          outline="#f85149", width=1, dash=(5, 5))

        # Warning banner
        risk_score = self.S.get("risk", 0)
        if risk_score >= 40:
            risk_color = RED if risk_score >= 75 else ORANGE
            c.create_rectangle(0, 0, W, 26, fill="#111111", outline="")
            c.create_text(W - 140, 14,
                          text=f"⚠ Collision risk {risk_score}%",
                          fill=risk_color, font=("Segoe UI", 9, "bold"))
            weather = getattr(self, "v_weather", None)
            weather_label = weather.get().capitalize() if weather is not None else "Clear"
            c.create_text(12, 14,
                          text=f"Min gap: {self.S.get('min_gap', 0.0):.0f} m  |  Weather: {weather_label}",
                          fill=TEXT_PRI, font=("Segoe UI", 8), anchor="w")

        # ── RSUs ──
        for rsu in self.rsus:
            rx = int(rsu.position * sc)
            # tower
            c.create_rectangle(rx - 5, r_top - 28, rx + 5, r_top,
                                fill=PURPLE, outline="#d2a8ff", width=1)
            c.create_polygon(rx - 11, r_top - 28,
                             rx, r_top - 44,
                             rx + 11, r_top - 28,
                             fill=PURPLE, outline="#d2a8ff")
            c.create_text(rx, r_top - 50, text=rsu.id,
                          fill="#d2a8ff", font=("Segoe UI", 7, "bold"))
            # range arc
            rr = int(rsu.range * sc)
            c.create_oval(rx - rr, r_top - 6,
                          rx + rr, r_bot + 6,
                          outline=PURPLE, width=1, dash=(3, 5))

        # ── Vehicles ──
        lane_y = {1: r_top + (r_bot - r_top) // 4,
                  2: r_top + 3 * (r_bot - r_top) // 4}
        for v in self.vehicles:
            vx  = int(v.position * sc)
            vy  = lane_y.get(v.lane, mid)
            col = v.color

            # Car shadow
            c.create_rectangle(vx - 13, vy + 7, vx + 13, vy + 11,
                                fill="#000000", outline="")
            # Car body
            c.create_rectangle(vx - 12, vy - 6, vx + 12, vy + 7,
                                fill=col, outline="#ffffff", width=1)
            # Roof
            c.create_rectangle(vx - 7, vy - 12, vx + 7, vy - 6,
                                fill=col, outline="#ffffff", width=1)
            # Wheels
            for wx in [vx - 8, vx + 4]:
                c.create_oval(wx, vy + 5, wx + 8, vy + 11,
                              fill="#1a1a1a", outline="#555")
            # Headlights
            c.create_oval(vx + 10, vy - 2, vx + 14, vy + 2,
                          fill="#fffde7", outline="")

            # ID label
            c.create_text(vx, vy - 20, text=v.id,
                          fill=TEXT_PRI, font=("Segoe UI", 6, "bold"))
            # Speed
            c.create_text(vx, vy + 22, text=f"{v.speed:.0f}",
                          fill="#666", font=("Segoe UI", 6))

            # Alert indicator
            if v.collision_warning:
                c.create_text(vx, vy - 32, text="🚨",
                              fill=RED, font=("Segoe UI", 10))
            elif v.alert_received:
                c.create_text(vx, vy - 32, text="⚠",
                              fill=YELLOW, font=("Segoe UI", 9))

    # ── stats refresh ─────────────────────────────────────────────────────────
    def _refresh_stats(self):
        self._sv["cams"].set(str(self.S["cams"]))
        self._sv["denms"].set(str(self.S["denms"]))
        self._sv["alerted"].set(str(self.S["alerted"]))
        avg = self.S["avg_ms"]
        self._sv["avg_ms"].set(f"{avg:.1f} ms")
        self._sv["suppressed"].set(str(self.S["suppressed"]))
        self._sv["rsu_relays"].set(str(self.S["rsu_relays"]))
        if "risk" in self._sv:
            self._sv["risk"].set(f"{self.S.get("risk", 0)}%")
        if "min_gap" in self._sv:
            self._sv["min_gap"].set(f"{self.S.get("min_gap", 0.0):.0f} m")

    # ── ripple helper ─────────────────────────────────────────────────────────
    def _add_ripple(self, position: float):
        self.ripples.append({"position": position, "radius": 5, "alpha": 0.85})


# ═════════════════════════════════════════════════════════════════════════════
# Entry point
# ═════════════════════════════════════════════════════════════════════════════

def main():
    root = tk.Tk()
    root.geometry("1300x740")
    root.minsize(1050, 640)
    app = VANETSimulator(root)
    root.mainloop()


if __name__ == "__main__":
    main()
