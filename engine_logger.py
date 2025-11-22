import can
import csv
import time
import sys

sys.stdout.write("\033]0;Logger\007")
sys.stdout.flush()

bus = can.interface.Bus(channel="vcan0", bustype="socketcan")

def decode(msg):
    if msg.arbitration_id != 0x100:
        return None
    d = msg.data
    rpm = ((d[0] << 8) | d[1]) * 4
    speed = d[2]
    cool = d[3] - 40
    return rpm, speed, cool

filename = f"engine_log_{int(time.time())}.csv"
print(f"Logging to {filename} ... Ctrl+C to stop")

with open(filename, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["timestamp","rpm","speed_kph","coolant_c"])

    try:
        for msg in bus:
            frame = decode(msg)
            if not frame:
                continue
            writer.writerow([time.time(), *frame])
    except KeyboardInterrupt:
        print("\nLogger stopped.")
