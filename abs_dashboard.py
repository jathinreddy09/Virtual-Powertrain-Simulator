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
sys.stdout.write("\033]0;ABS Dashboard\007")
sys.stdout.flush()

bus = can.interface.Bus(channel="vcan0", bustype="socketcan")

def decode_abs(msg):
    if msg.arbitration_id != 0x200 or len(msg.data) < 4:
        return None
    d = msg.data
    fl = d[0]
    fr = d[1]
    rl = d[2]
    rr = d[3]
    return fl, fr, rl, rr

state = {"paused": False}

def check_commands(state):
    if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
        cmd = sys.stdin.readline().strip().lower()
        if cmd == "p":
            state["paused"] = True
            print("Paused (ABS Dashboard)")
        elif cmd == "r":
            state["paused"] = False
            print("Resumed (ABS Dashboard)")
        elif cmd == "q":
            print("Quit requested (ABS Dashboard)")
            raise KeyboardInterrupt
    return state

print("ABS dashboard listening... Controls: p=pause, r=resume, q=quit (then Enter)")
try:
    while True:
        state = check_commands(state)
        if state["paused"] or is_paused():
            time.sleep(0.1)
            continue

        msg = bus.recv(0.1)
        if msg is None:
            continue

        parsed = decode_abs(msg)
        if parsed:
            fl, fr, rl, rr = parsed
            print(
                f"FL={fl:3} km/h | FR={fr:3} km/h | "
                f"RL={rl:3} km/h | RR={rr:3} km/h"
            )

except KeyboardInterrupt:
    print("\nABS dashboard stopped.")
