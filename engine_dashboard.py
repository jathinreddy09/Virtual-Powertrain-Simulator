import can
import sys
import select
import time
import os

STATE_FILE = "/home/jathin/Desktop/CAN_LAB/global_state.txt"
def is_paused():
    try:
        with open(STATE_FILE) as f:
            return f.read().strip().lower() == "pause"
    except FileNotFoundError:
        return False

# Set terminal title
sys.stdout.write("\033]0;Engine Dashboard\007")
sys.stdout.flush()

bus = can.interface.Bus(channel="vcan0", bustype="socketcan")

def decode(msg):
    if msg.arbitration_id != 0x100 or len(msg.data) < 4:
        return None
    d = msg.data
    rpm_raw = (d[0] << 8) | d[1]
    rpm = rpm_raw * 4
    speed = d[2]
    cool = d[3] - 40
    return rpm, speed, cool

state = {"paused": False}

def check_commands(state):
    if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
        cmd = sys.stdin.readline().strip().lower()
        if cmd == "p":
            state["paused"] = True
            print("Paused (Engine Dashboard)")
        elif cmd == "r":
            state["paused"] = False
            print("Resumed (Engine Dashboard)")
        elif cmd == "q":
            print("Quit requested (Engine Dashboard)")
            raise KeyboardInterrupt
    return state

print("Engine dashboard listening... Controls: p=pause, r=resume, q=quit (then Enter)")

try:
    while True:
        state = check_commands(state)
        if state["paused"] or is_paused():
            time.sleep(0.1)
            continue

        msg = bus.recv(0.1)
        if msg is None:
            continue

        decoded = decode(msg)
        if decoded:
            rpm, speed, cool = decoded
            print(f"RPM={rpm:5} | Speed={speed:4} km/h | Coolant={cool:4}°C")

except KeyboardInterrupt:
    print("\nEngine dashboard stopped.")
