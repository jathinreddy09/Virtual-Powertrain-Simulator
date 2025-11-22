"""Engine ECU simulation node.

This module simulates an engine control unit that:
- Listens for target RPM / mode / gear commands on the powertrain CAN bus.
- Applies simple control logic (idle, redline, engine braking).
- Publishes engine state (RPM, torque, load, etc.) over CAN.
"""

import can
import time
import sys
import os
import random
import cantools

sys.stdout.write("\033]0;Engine ECU (DEBUG)\007")
sys.stdout.flush()

# ============================================
# ENGINE CONSTANTS
# ============================================
BASE_IDLE_RPM = 800.0       # idle speed
REDLINE_RPM   = 7000.0      # new redline

# amount of torque-converter slip at full throttle
MAX_SLIP_RPM  = 3000.0

# Torque converter slip curve (PATCH A)
def torque_converter_slip(throttle):
    """
    Returns slip RPM based on throttle.
    0%   → 0 rpm slip
    10%  → ~200 rpm slip (light creep)
    50%  → ~1500 rpm slip
    100% → MAX_SLIP_RPM (e.g. 3000 rpm)
    """
    t = throttle / 100.0
    if t <= 0.0:
        return 0.0
    if t < 0.10:
        # small slip so the car can creep at low throttle
        return t * 2000.0
    # from 10% to 100% throttle, ramp up to MAX_SLIP_RPM
    return 200.0 + (t - 0.10) * (MAX_SLIP_RPM - 200.0) / 0.90

# ============================================
# PATHS / DBC
# ============================================
STATE_FILE = "/home/jathin/Desktop/CAN_LAB/global_state.txt"
DRIVER_STATE_PATH = "/home/jathin/Desktop/CAN_LAB/driver_state.txt"
DBC_PATH = "/home/jathin/Desktop/CAN_LAB/vehicle.dbc"

bus = can.interface.Bus(interface="socketcan", channel="vcan0")
db = cantools.database.load_file(DBC_PATH)

# ============================================
# HELPERS
# ============================================
def clamp(x, lo, hi):
    return max(lo, min(x, hi))

def is_paused():
    try:
        with open(STATE_FILE) as f:
            return f.read().strip().lower() == "pause"
    except FileNotFoundError:
        return False

def read_driver_state():
    throttle, brake = 0, 0
    try:
        with open(DRIVER_STATE_PATH) as f:
            for line in f:
                line = line.strip()
                if line.startswith("THROTTLE="):
                    throttle = int(line.split("=")[1])
                elif line.startswith("BRAKE="):
                    brake = int(line.split("=")[1])
    except:
        pass
    return clamp(throttle, 0, 100), clamp(brake, 0, 100)

def build_frame(rpm, speed_kph, cool):
    rpm_raw = int(rpm / 4)
    rpm_raw = clamp(rpm_raw, 0, 65535)
    speed_raw = clamp(int(speed_kph), 0, 255)
    cool_raw = clamp(int(cool + 40), 0, 255)

    data = [
        (rpm_raw >> 8) & 0xFF,
        rpm_raw & 0xFF,
        speed_raw,
        cool_raw,
        0, 0, 0, 0
    ]
    return can.Message(arbitration_id=0x100, data=data, is_extended_id=False)

print("Engine ECU (debug build)")
print("Shows: speed, gear, rpm_from_speed, target_rpm, rpm, throttle\n")

# ============================================
# INITIAL STATE
# ============================================
rpm = 900.0
speed_kph = 0.0
cool = 70.0
current_gear = 1

# physics
dt = 0.1
A_MAX = 4.0      # was 2.0 → stronger acceleration
B_MAX = 6.0
DRAG = 0.058     # was 0.1 → allows ~250 km/h top speed

# drivetrain
GEAR_RATIOS = {1:3.6, 2:2.1, 3:1.4, 4:1.0, 5:0.8, 6:0.7}
FINAL_DRIVE = 3.2
TIRE_CIRC_M = 2.05

def poll_tcu():
    """Read gear from 0x300 if present."""
    global current_gear
    while True:
        msg = bus.recv(0.0)
        if msg is None:
            return
        if msg.arbitration_id != 0x300:
            continue
        try:
            data = db.decode_message(0x300, msg.data)
            g = int(data.get("Gear", current_gear))
            if g > 0:
                current_gear = g
        except:
            continue

last_debug_print = 0

# ============================================
# MAIN LOOP
# ============================================
try:
    while True:

        if is_paused():
            time.sleep(0.1)
            continue

        poll_tcu()

        throttle, brake = read_driver_state()
        speed_ms = speed_kph / 3.6

        # -------------------------
        # SPEED PHYSICS
        # -------------------------
        accel = (throttle / 100.0) * A_MAX
        accel -= (brake / 100.0) * B_MAX
        accel -= DRAG * speed_ms
        speed_ms = max(0.0, speed_ms + accel * dt)
        speed_kph = speed_ms * 3.6

        # -------------------------
        # RPM FROM GEARING
        # -------------------------
        gear_ratio = GEAR_RATIOS.get(current_gear, 1.0)
        overall_ratio = gear_ratio * FINAL_DRIVE
        wheel_rps = speed_ms / TIRE_CIRC_M
        rpm_from_speed = wheel_rps * 60.0 * overall_ratio

        base_idle = BASE_IDLE_RPM

        # -------------------------
        # ENGINE / MODE LOGIC
        # -------------------------
        if speed_kph > 10.0:
            # Normal driving / high-speed engine braking
            if throttle <= 2:
                mode = "ENGINE BRAKING"
                # follow wheel speed directly
                target_rpm = rpm_from_speed
            else:
                mode = "DRIVING"
                # PATCH B: add torque converter slip so RPM can flare above wheel speed
                slip = torque_converter_slip(throttle)
                target_rpm = rpm_from_speed + slip
                # never below idle
                target_rpm = max(target_rpm, base_idle)

        elif speed_kph > 3.0:
            # Transitional low-speed region
            if throttle <= 2:
                mode = "LOW-SPEED BRAKING"
                # Blend from wheel RPM to idle between 10 km/h and 3 km/h
                blend = (speed_kph - 3.0) / 7.0   # 10 → 1.0, 3 → 0.0
                blend = clamp(blend, 0.0, 1.0)
                rpm_blend = base_idle + (rpm_from_speed - base_idle) * blend
                # IMPORTANT: no max(...) here so it can actually drop to idle
                target_rpm = rpm_blend
            else:
                mode = "DRIVING"
                slip = torque_converter_slip(throttle)
                target_rpm = rpm_from_speed + slip
                target_rpm = max(target_rpm, base_idle)

        else:
            # Nearly stopped → just idle behaviour
            mode = "IDLE REGION"
            # tiny "rev" with throttle even while stationary
            target_rpm = base_idle + throttle * 10.0

        # -------------------------
        # RPM DYNAMICS
        # -------------------------
        alpha = 0.35
        rpm = rpm + alpha * (target_rpm - rpm)
        rpm = clamp(rpm, 600.0, REDLINE_RPM)

        # -------------------------
        # COOLANT
        # -------------------------
        if throttle > 10:
            cool += 0.03
        elif speed_kph > 10:
            cool += 0.01
        else:
            cool -= 0.02
        cool = clamp(cool, 60.0, 110.0)

        # send frame
        msg = build_frame(rpm, speed_kph, cool)
        bus.send(msg)

        # DEBUG PRINT EVERY LOOP
        print(
            f"G={current_gear} | mode={mode:15} | Thr={throttle:3d}% | "
            f"Speed={speed_kph:6.2f} | "
            f"rpm_from_speed={rpm_from_speed:7.1f} | "
            f"target={target_rpm:7.1f} | rpm={rpm:7.1f}"
        )

        time.sleep(dt)

except KeyboardInterrupt:
    print("Engine ECU stopped.")
