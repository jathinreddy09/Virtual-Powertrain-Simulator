import can
import cantools
import sys
import time

# Set terminal title
sys.stdout.write("\033]0;DBC Dashboard\007")
sys.stdout.flush()

# Load DBC
db = cantools.database.load_file("/home/jathin/Desktop/CAN_LAB/vehicle.dbc")

bus = can.interface.Bus(channel="vcan0", bustype="socketcan")

print("DBC dashboard listening on vcan0")
print("Will decode EngineData (0x100), WheelSpeeds (0x200), GearboxData (0x300)")
print("Press Ctrl+C to stop.\n")

try:
    while True:
        msg = bus.recv(1.0)
        if msg is None:
            continue

        try:
            decoded = db.decode_message(msg.arbitration_id, msg.data)
        except KeyError:
            # Message ID not in DBC
            continue

        if msg.arbitration_id == 0x100:
            # EngineData
            print(
                f"[EngineData] RPM={decoded['RPM']:5.0f} rpm | "
                f"Speed={decoded['Speed']:3.0f} km/h | "
                f"Coolant={decoded['Coolant']:3.0f} °C"
            )

        elif msg.arbitration_id == 0x200:
            # WheelSpeeds
            print(
                f"[WheelSpeeds] FL={decoded['WheelSpeed_FL']:3.0f} km/h | "
                f"FR={decoded['WheelSpeed_FR']:3.0f} km/h | "
                f"RL={decoded['WheelSpeed_RL']:3.0f} km/h | "
                f"RR={decoded['WheelSpeed_RR']:3.0f} km/h"
            )

        elif msg.arbitration_id == 0x300:
            # GearboxData
            gear = decoded["Gear"]
            tgt = decoded["TargetGear"]
            c1 = decoded["Clutch1_Tq"]
            c2 = decoded["Clutch2_Tq"]
            oil = decoded["OilTemp"]
            shift = decoded["ShiftInProgress"]
            print(
                f"[Gearbox] Gear={gear} -> {tgt} | "
                f"C1={c1:3.0f}% C2={c2:3.0f}% | "
                f"Oil={oil:3.0f} °C | shifting={int(shift)}"
            )

except KeyboardInterrupt:
    print("\nDBC dashboard stopped.")
