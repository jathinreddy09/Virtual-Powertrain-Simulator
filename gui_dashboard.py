"""GUI dashboard / virtual instrument cluster.

This module opens a graphical window that:
- Subscribes to CAN messages from engine and transmission ECUs.
- Displays RPM, vehicle speed, gear, throttle, and drive mode.
- Helps visualize and tune the control logic in real time.
"""
import sys
import time
import math
import os
import can
import cantools
import tkinter as tk
import pygame
from tkinter import ttk

# Set window title in terminal
sys.stdout.write("\033]0;GUI Dashboard\007")
sys.stdout.flush()

MODE_FILE = "/home/jathin/Desktop/CAN_LAB/tcu_mode.txt"
DBC_PATH = "/home/jathin/Desktop/CAN_LAB/vehicle.dbc"
DRIVER_STATE_PATH = "/home/jathin/Desktop/CAN_LAB/driver_state.txt"

# Use diagnostic bus (vcan1) so it works via the gateway
bus = can.interface.Bus(channel="vcan1", bustype="socketcan")

db = cantools.database.load_file(DBC_PATH)

state = {
    "RPM": 0.0,
    "Speed": 0.0,
    "Coolant": 0.0,
    "Gear": 0,
    "TargetGear": 0,
    "Clutch1_Tq": 0.0,
    "Clutch2_Tq": 0.0,
    "OilTemp": 0.0,
    "ShiftInProgress": 0,
    "Wheel_FL": 0.0,
    "Wheel_FR": 0.0,
    "Wheel_RL": 0.0,
    "Wheel_RR": 0.0,
}

driver_state = {
    "throttle": 0,
    "brake": 0,
}

# ============================
# === MODE HELPERS (D / S) ===
# ============================
current_mode = "D"  # default; will be overwritten by read_mode()


def read_mode():
    """Read mode from MODE_FILE. Returns 'D' or 'S'."""
    global current_mode
    try:
        with open(MODE_FILE, "r") as f:
            m = f.read().strip().upper()
            if m in ("D", "S"):
                current_mode = m
            else:
                current_mode = "D"
    except FileNotFoundError:
        current_mode = "D"
    except Exception as e:
        print(f"Failed to read mode file: {e}")
        current_mode = "D"
    return current_mode


def write_mode(mode):
    """Write mode ('D' or 'S') to MODE_FILE."""
    try:
        with open(MODE_FILE, "w") as f:
            f.write(mode)
    except Exception as e:
        print(f"Failed to write mode file: {e}")


def toggle_mode():
    """Toggle between D and S, write to file, update GUI label."""
    global current_mode, mode_var
    current_mode = "S" if current_mode == "D" else "D"
    write_mode(current_mode)
    mode_var.set(f"Mode: {current_mode}")


def write_driver_state():
    """Write throttle/brake to a simple text file for the engine ECU."""
    try:
        with open(DRIVER_STATE_PATH, "w") as f:
            f.write(f"THROTTLE={driver_state['throttle']}\n")
            f.write(f"BRAKE={driver_state['brake']}\n")
    except Exception as e:
        print(f"Failed to write driver_state: {e}")


# ---------------- GUI SETUP ---------------- #

root = tk.Tk()
root.title("CAN Virtual Dashboard")

root.geometry("1000x550")
root.configure(bg="#20252b")

root.columnconfigure(0, weight=3)
root.columnconfigure(1, weight=2)
root.columnconfigure(2, weight=1)
root.rowconfigure(0, weight=3)
root.rowconfigure(1, weight=2)

# ==== Engine sound setup ====
engine_channel = None
try:
    pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=512)

    # Load engine loop sound (mono .wav is best)
    engine_sound = pygame.mixer.Sound("engine_loop.wav")

    # Start playing in a loop
    engine_channel = engine_sound.play(loops=-1)
    engine_channel.set_volume(0.0)  # start muted
except Exception as e:
    print(f"[AUDIO] Engine sound disabled: {e}")
    engine_channel = None
try:
    turbo_sound = pygame.mixer.Sound("turbo_loop.wav")
    turbo_chan = turbo_sound.play(loops=-1)
    turbo_chan.set_volume(0)
except:
    turbo_chan = None

# Gauges (RPM / Speed)
gauge_frame = tk.Frame(root, bg="#20252b")
gauge_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

gauge_frame.columnconfigure(0, weight=1)
gauge_frame.columnconfigure(1, weight=1)

rpm_canvas = tk.Canvas(gauge_frame, width=300, height=200, bg="#20252b", highlightthickness=0)
rpm_canvas.grid(row=0, column=0, padx=10, pady=10)

speed_canvas = tk.Canvas(gauge_frame, width=300, height=200, bg="#20252b", highlightthickness=0)
speed_canvas.grid(row=0, column=1, padx=10, pady=10)

rpm_label = tk.Label(gauge_frame, text="RPM: 0", fg="white", bg="#20252b", font=("Arial", 14))
rpm_label.grid(row=1, column=0, pady=5)

speed_label = tk.Label(gauge_frame, text="Speed: 0 km/h", fg="white", bg="#20252b", font=("Arial", 14))
speed_label.grid(row=1, column=1, pady=5)


# Right: Gear, temps, shifting
right_frame = tk.Frame(root, bg="#20252b")
right_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)

gear_label = tk.Label(right_frame, text="Gear: N", fg="white", bg="#20252b", font=("Arial", 32, "bold"))
gear_label.pack(pady=10)

coolant_label = tk.Label(right_frame, text="Coolant: 0 °C", fg="white", bg="#20252b", font=("Arial", 14))
coolant_label.pack(pady=5)

oil_label = tk.Label(right_frame, text="Oil: 0 °C", fg="white", bg="#20252b", font=("Arial", 14))
oil_label.pack(pady=5)

shift_label = tk.Label(right_frame, text="Shifting: No", fg="white", bg="#20252b", font=("Arial", 14))
shift_label.pack(pady=5)


# Bottom: clutches + wheel speeds
bottom_frame = tk.Frame(root, bg="#20252b")
bottom_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=10, pady=10)

bottom_frame.columnconfigure(0, weight=1)
bottom_frame.columnconfigure(1, weight=1)

c1_label = tk.Label(bottom_frame, text="Clutch 1 (C1)", fg="white", bg="#20252b", font=("Arial", 12))
c1_label.grid(row=0, column=0, sticky="w")

c1_bar = ttk.Progressbar(bottom_frame, orient="horizontal", length=300, mode="determinate")
c1_bar.grid(row=1, column=0, sticky="we", padx=5)

c2_label = tk.Label(bottom_frame, text="Clutch 2 (C2)", fg="white", bg="#20252b", font=("Arial", 12))
c2_label.grid(row=2, column=0, sticky="w", pady=(10, 0))

c2_bar = ttk.Progressbar(bottom_frame, orient="horizontal", length=300, mode="determinate")
c2_bar.grid(row=3, column=0, sticky="we", padx=5)

wheel_label = tk.Label(bottom_frame, text="Wheel Speeds: --", fg="white", bg="#20252b", font=("Arial", 12))
wheel_label.grid(row=0, column=1, rowspan=4, sticky="n", padx=20)


# Rightmost: driver controls (Throttle / Brake / Mode)
ctrl_frame = tk.Frame(root, bg="#20252b")
ctrl_frame.grid(row=0, column=2, rowspan=2, sticky="nsew", padx=10, pady=10)

ctrl_title = tk.Label(ctrl_frame, text="Driver Controls", fg="white", bg="#20252b", font=("Arial", 14, "bold"))
ctrl_title.pack(pady=(0, 10))

# ============================
# === MODE WIDGETS (D / S) ===
# ============================
current_mode = read_mode()  # sync from file at startup
mode_var = tk.StringVar(value=f"Mode: {current_mode}")

mode_label = tk.Label(
    ctrl_frame,
    textvariable=mode_var,
    fg="white",
    bg="#20252b",
    font=("Arial", 12, "bold")
)
mode_label.pack(pady=(0, 5))

mode_button = tk.Button(
    ctrl_frame,
    text="Toggle D / S",
    command=toggle_mode,
    bg="#444b52",
    fg="white"
)
mode_button.pack(pady=(0, 15))


throttle_label = tk.Label(ctrl_frame, text="Throttle %", fg="white", bg="#20252b", font=("Arial", 12))
throttle_label.pack(pady=(5, 0))


def on_throttle_change(val):
    try:
        driver_state["throttle"] = int(float(val))
        write_driver_state()
    except ValueError:
        pass


throttle_scale = tk.Scale(
    ctrl_frame,
    from_=100,
    to=0,
    orient="vertical",
    length=200,
    command=on_throttle_change,
    bg="#20252b",
    fg="white",
    highlightthickness=0
)
throttle_scale.set(0)
throttle_scale.pack(pady=(0, 15))

brake_label = tk.Label(ctrl_frame, text="Brake %", fg="white", bg="#20252b", font=("Arial", 12))
brake_label.pack(pady=(5, 0))


def on_brake_change(val):
    try:
        driver_state["brake"] = int(float(val))
        write_driver_state()
    except ValueError:
        pass


brake_scale = tk.Scale(
    ctrl_frame,
    from_=100,
    to=0,
    orient="vertical",
    length=200,
    command=on_brake_change,
    bg="#20252b",
    fg="white",
    highlightthickness=0
)
brake_scale.set(0)
brake_scale.pack(pady=(0, 15))


style = ttk.Style()
style.theme_use("default")
style.configure("TProgressbar", troughcolor="#3a3f46", background="#4caf50")


# ---------------- DRAW FUNCTIONS ---------------- #

def draw_gauge(canvas, center_x, center_y, radius, min_val, max_val, value, label):
    canvas.delete("all")

    start_angle = 135
    extent = -270

    canvas.create_arc(center_x - radius, center_y - radius,
                      center_x + radius, center_y + radius,
                      start=start_angle, extent=extent,
                      style="arc", width=10, outline="#555555")

    if value < min_val:
        value = min_val
    if value > max_val:
        value = max_val

    frac = (value - min_val) / (max_val - min_val + 1e-6)
    angle = start_angle + extent * frac

    angle_rad = math.radians(angle)
    x_end = center_x + radius * 0.8 * math.cos(angle_rad)
    y_end = center_y - radius * 0.8 * math.sin(angle_rad)

    canvas.create_line(center_x, center_y, x_end, y_end,
                       fill="#ffcc00", width=4)

    canvas.create_oval(center_x - 5, center_y - 5,
                       center_x + 5, center_y + 5,
                       fill="#ffcc00", outline="")

    canvas.create_text(center_x, center_y + radius * 0.6,
                       text=label, fill="white",
                       font=("Arial", 10))


# ---------------- CAN PROCESSING ---------------- #

def process_message(msg):
    global state

    try:
        decoded = db.decode_message(msg.arbitration_id, msg.data)
    except Exception:
        return

    if msg.arbitration_id == 0x100:
        state["RPM"] = float(decoded.get("RPM", 0.0))
        state["Speed"] = float(decoded.get("Speed", 0.0))
        state["Coolant"] = float(decoded.get("Coolant", 0.0))

    elif msg.arbitration_id == 0x200:
        state["Wheel_FL"] = float(decoded.get("WheelSpeed_FL", 0.0))
        state["Wheel_FR"] = float(decoded.get("WheelSpeed_FR", 0.0))
        state["Wheel_RL"] = float(decoded.get("WheelSpeed_RL", 0.0))
        state["Wheel_RR"] = float(decoded.get("WheelSpeed_RR", 0.0))

    elif msg.arbitration_id == 0x300:
        state["Gear"] = int(decoded.get("Gear", 0))
        state["TargetGear"] = int(decoded.get("TargetGear", 0))
        state["Clutch1_Tq"] = float(decoded.get("Clutch1_Tq", 0.0))
        state["Clutch2_Tq"] = float(decoded.get("Clutch2_Tq", 0.0))
        state["OilTemp"] = float(decoded.get("OilTemp", 0.0))
        state["ShiftInProgress"] = int(decoded.get("ShiftInProgress", 0))


def poll_can():
    while True:
        msg = bus.recv(0.0)
        if msg is None:
            break
        process_message(msg)
    root.after(20, poll_can)

def update_clutch_bars_simple(gear, shifting):
    # If shifting, do NOT override — the TCU already updates real torque
    if shifting:
        return

    # Odd gears = C1 on, C2 off
    if gear in (1, 3, 5):
        c1_bar['value'] = 100
        c2_bar['value'] = 0

    # Even gears = C2 on, C1 off
    elif gear in (2, 4, 6):
        c1_bar['value'] = 0
        c2_bar['value'] = 100

    # Neutral
    else:
        c1_bar['value'] = 0
        c2_bar['value'] = 0

def update_gui():
    rpm = state["RPM"]
    speed = state["Speed"]
    coolant = state["Coolant"]
    gear = state["Gear"]
    tgt_gear = state["TargetGear"]
    c1 = state["Clutch1_Tq"]
    c2 = state["Clutch2_Tq"]
    oil = state["OilTemp"]
    shifting = state["ShiftInProgress"]

    rpm_label.config(text=f"RPM: {rpm:5.0f}")
    speed_label.config(text=f"Speed: {speed:3.0f} km/h")
    coolant_label.config(text=f"Coolant: {coolant:3.0f} °C")
    oil_label.config(text=f"Oil: {oil:3.0f} °C")
    shift_label.config(text=f"Shifting: {'Yes' if shifting else 'No'}")

    # ==== Improved engine sound ====
    try:
        max_rpm = 7000.0
        thr = driver_state.get("throttle", 0)

        rpm_norm = max(0.0, min(rpm / max_rpm, 1.0))
        thr_norm = max(0.0, min(thr / 100.0, 1.0))

        # Non-linear shaping for realism
        # Aggressive response near 3k–5k rpm where turbo would spool
        rpm_curve = rpm_norm ** 1.6  
        thr_curve = thr_norm ** 1.3  

        # Base idle sound
        base_idle = 0.12

        # More realistic turbo-ish ramp
        volume = base_idle + (rpm_curve * 0.4) + (thr_curve * 0.5)

        # Clamp
        volume = max(0.0, min(volume, 1.0))

        # Apply
        if engine_channel:
            engine_channel.set_volume(volume)

    except Exception:
        pass
    # ==== Turbo spool ====
    try:
        # turbo wakes up around 2500–4000 rpm and medium+ throttle
        turbo_factor = max(0.0, min((rpm - 2500) / 3000, 1.0))
        turbo_factor *= (thr_norm ** 1.5)

        if turbo_chan:
            turbo_chan.set_volume(turbo_factor * 0.8)
    except:
        pass

    if gear == 0:
        gear_text = "N"
    else:
        gear_text = str(gear)
    if tgt_gear != gear:
        gear_label.config(text=f"Gear: {gear_text} → {tgt_gear}")
    else:
        gear_label.config(text=f"Gear: {gear_text}")

    c1_bar["value"] = max(0, min(c1, 100))
    c2_bar["value"] = max(0, min(c2, 100))
    update_clutch_bars_simple(gear, shifting)

    fl = state["Wheel_FL"]
    fr = state["Wheel_FR"]
    rl = state["Wheel_RL"]
    rr = state["Wheel_RR"]
    wheel_label.config(
        text=f"Wheel Speeds:\n"
             f"FL={fl:4.1f}  FR={fr:4.1f}\n"
             f"RL={rl:4.1f}  RR={rr:4.1f}"
    )

    draw_gauge(rpm_canvas, 150, 100, 80, 0, 7000, rpm, "RPM")
    draw_gauge(speed_canvas, 150, 100, 80, 0, 200, speed, "km/h")

    root.after(50, update_gui)


# Start everything
write_driver_state()
poll_can()
update_gui()

try:
    root.mainloop()
except KeyboardInterrupt:
    print("GUI Dashboard closed.")
