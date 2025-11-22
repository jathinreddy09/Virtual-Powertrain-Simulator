import can
import cantools
import csv
import time
import sys

# Set terminal title
sys.stdout.write("\033]0;DBC Logger\007")
sys.stdout.flush()

# Load the DBC database
db = cantools.database.load_file("vehicle.dbc")

# Open CAN bus
bus = can.interface.Bus(channel="vcan0", bustype="socketcan")

# Output file name with timestamp
timestamp_str = time.strftime("%Y%m%d_%H%M%S")
filename = f"dbc_log_{timestamp_str}.csv"

print(f"DBC logger started on vcan0")
print(f"Logging decoded signals to {filename}")
print("Press Ctrl+C to stop.\n")

# Define all signals we care about from the DBC
signal_fields = [
    "RPM",
    "Speed",
    "Coolant",
    "WheelSpeed_FL",
    "WheelSpeed_FR",
    "WheelSpeed_RL",
    "WheelSpeed_RR",
    "Gear",
    "TargetGear",
    "Clutch1_Tq",
    "Clutch2_Tq",
    "OilTemp",
    "ShiftInProgress",
]

# CSV header fields
fieldnames = [
    "timestamp",
    "can_id",
    "name",
    "dlc",
    "raw_data",
] + signal_fields

with open(filename, "w", newline="") as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()

    try:
        while True:
            msg = bus.recv(1.0)
            if msg is None:
                continue

            row = {
                "timestamp": time.time(),
                "can_id": hex(msg.arbitration_id),
                "name": "",
                "dlc": msg.dlc,
                "raw_data": msg.data.hex().upper(),
            }

            try:
                # Find DBC message definition
                msg_def = db.get_message_by_frame_id(msg.arbitration_id)
                decoded = db.decode_message(msg.arbitration_id, msg.data)
                row["name"] = msg_def.name

                # Fill known signal fields; leave others blank
                for sig in signal_fields:
                    row[sig] = decoded.get(sig, "")

            except (KeyError, cantools.database.errors.DecodeError):
                # Message not in DBC or bad decode; log raw only
                pass

            writer.writerow(row)

    except KeyboardInterrupt:
        print("\nDBC logger stopped.")
        print(f"Log saved to {filename}")

