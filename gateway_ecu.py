"""Gateway ECU between powertrain and diagnostic CAN buses.

This node:
- Bridges messages between PT (vcan0) and DIAG (vcan1) buses.
- Forwards OBD-style request/response frames for diagnostics.
"""

import can
import sys
import time

sys.stdout.write("\033]0;CAN Gateway\007")
sys.stdout.flush()

# Two buses: powertrain and diagnostics/tools
bus_pt = can.interface.Bus(channel="vcan0", bustype="socketcan")  # Powertrain
bus_diag = can.interface.Bus(channel="vcan1", bustype="socketcan")  # Diagnostic

print("CAN Gateway running:")
print("  vcan0 = Powertrain (Engine/ABS/Trans/OBD_ECU)")
print("  vcan1 = Diagnostic (OBD Tester / Tools)")
print()
print("Forwarding rules:")
print("  vcan0 -> vcan1 : 0x100, 0x200, 0x300, 0x7E8 (OBD response)")
print("  vcan1 -> vcan0 : 0x7E0 (OBD request)")
print("Ctrl+C to stop.\n")

def forward(msg, dst_bus, direction):
    """Forward a CAN message and log it."""
    try:
        dst_bus.send(msg)
        print(f"{direction}: ID=0x{msg.arbitration_id:03X} data={msg.data.hex().upper()}")
    except can.CanError as e:
        print(f"{direction}: failed to send 0x{msg.arbitration_id:03X}: {e}")

try:
    while True:
        # Check powertrain bus (vcan0)
        msg0 = bus_pt.recv(0.01)
        if msg0 is not None:
            aid = msg0.arbitration_id

            # EngineData, WheelSpeeds, GearboxData from PT -> DIAG
            if aid in (0x100, 0x200, 0x300):
                forward(msg0, bus_diag, "PT->DG")

            # OBD response 7E8 from PT -> DIAG
            elif aid == 0x7E8:
                forward(msg0, bus_diag, "PT->DG")

        # Check diagnostic bus (vcan1)
        msg1 = bus_diag.recv(0.01)
        if msg1 is not None:
            aid = msg1.arbitration_id

            # OBD request 7E0 from DIAG -> PT
            if aid == 0x7E0:
                forward(msg1, bus_pt, "DG->PT")

        # Small sleep to avoid 100% CPU
        time.sleep(0.001)

except KeyboardInterrupt:
    print("\nCAN Gateway stopped.")
