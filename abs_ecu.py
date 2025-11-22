import can
import time
import sys
import random
import os
import cantools

# Set terminal title
sys.stdout.write("\033]0;ABS ECU\007")
sys.stdout.flush()

bus = can.interface.Bus(channel="vcan0", bustype="socketcan")

STATE_FILE = "/home/jathin/Desktop/CAN_LAB/global_state.txt"
DB_PATH = "/home/jathin/Desktop/CAN_LAB/vehicle.dbc"
db = cantools.database.load_file(DB_PATH)

def clamp(v, lo, hi):
    return max(lo, min(v, hi))

def is_paused():
    try:
        with open(STATE_FILE) as f:
            return f.read().strip().lower() == "pause"
    except FileNotFoundError:
        return False

def build_abs_frame(fl, fr, rl, rr):
    data = [
        clamp(int(fl), 0, 255),
        clamp(int(fr), 0, 255),
        clamp(int(rl), 0, 255),
        clamp(int(rr), 0, 255),
        0, 0, 0, 0,
    ]
    return can.Message(
        arbitration_id=0x200,
        data=data,
        is_extended_id=False,
    )

print("ABS ECU running, event-driven on EngineData (0x100) via DBC.")
print("Each EngineData frame → one ABS frame.")
print("Ctrl+C to stop.\n")

try:
    while True:
        if is_paused():
            time.sleep(0.1)
            continue

        # Block until any frame comes
        msg = bus.recv(1.0)
        if msg is None:
            continue

        # Only react to EngineData (0x100)
        if msg.arbitration_id != 0x100:
            continue

        # Decode engine speed directly from bytes to avoid any DBC mismatch
        d = msg.data
        if len(d) < 3:
            continue

        rpm_raw = (d[0] << 8) | d[1]
        rpm = rpm_raw * 4          # same as engine_ecu
        veh_speed = float(d[2])    # km/h, straight from engine_ecu

        # Per-wheel noise around vehicle speed
        fl = veh_speed + random.uniform(-1.0, 1.0)
        fr = veh_speed + random.uniform(-1.0, 1.0)
        rl = veh_speed + random.uniform(-1.5, 1.5)
        rr = veh_speed + random.uniform(-1.5, 1.5)

        fl = clamp(fl, 0.0, 250.0)
        fr = clamp(fr, 0.0, 250.0)
        rl = clamp(rl, 0.0, 250.0)
        rr = clamp(rr, 0.0, 250.0)

        msg_out = build_abs_frame(fl, fr, rl, rr)
        bus.send(msg_out)

        print(
            f"Engine Speed={veh_speed:5.1f} km/h | "
            f"FL={fl:5.1f} FR={fr:5.1f} RL={rl:5.1f} RR={rr:5.1f}"
        )

except KeyboardInterrupt:
    print("\nABS ECU stopped.")
