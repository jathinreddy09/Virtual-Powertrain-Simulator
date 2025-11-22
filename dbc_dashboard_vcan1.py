import can
import cantools
import sys
import time

# Set terminal title
sys.stdout.write("\033]0;DBC Dashboard (vcan1)\007")
sys.stdout.flush()

# Load DBC
DBC_PATH = "/home/jathin/Desktop/CAN_LAB/vehicle.dbc"
db = cantools.database.load_file(DBC_PATH)

# Use vcan1 (diagnostic side)
bus = can.interface.Bus(channel="vcan1", bustype="socketcan")

print("DBC Dashboard (vcan1)")
print("Listening for EngineData (0x100), WheelSpeeds (0x200), GearboxData (0x300)")
print("Ctrl+C to stop.\n")

try:
    while True:
        msg = bus.recv(1.0)
        if msg is None:
            continue

        try:
            decoded = db.decode_message(msg.arbitration_id, msg.data)
        except Exception:
            continue

        if msg.arbitration_id == 0x100:
            print(
                f"[Engine] RPM={decoded['RPM']:5.0f} | "
                f"Speed={decoded['Speed']:3.0f} km/h | "
                f"Coolant={decoded['Coolant']:3.0f} °C"
            )

        elif msg.arbitration_id == 0x200:
            print(
                f"[Wheels] FL={decoded['WheelSpeed_FL']:3.0f} | "
                f"FR={decoded['WheelSpeed_FR']:3.0f} | "
                f"RL={decoded['WheelSpeed_RL']:3.0f} | "
                f"RR={decoded['WheelSpeed_RR']:3.0f}"
            )

        elif msg.arbitration_id == 0x300:
            print(
                f"[Gearbox] Gear={decoded['Gear']} -> {decoded['TargetGear']} | "
                f"C1={decoded['Clutch1_Tq']:3.0f}% | "
                f"C2={decoded['Clutch2_Tq']:3.0f}% | "
                f"Oil={decoded['OilTemp']:3.0f} °C | "
                f"Shift={int(decoded['ShiftInProgress'])}"
            )

except KeyboardInterrupt:
    print("\nDashboard stopped.")
