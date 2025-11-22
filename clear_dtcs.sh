#!/bin/bash
cd /home/jathin/Desktop/CAN_LAB

# Use venv Python to avoid cantools issues
./venv/bin/python3 - << 'EOF'
import can
import time

bus = can.interface.Bus(channel="vcan1", bustype="socketcan")

# Mode 04 = Clear DTCs
msg = can.Message(arbitration_id=0x7E0,
                  data=[0x01,0x04,0,0,0,0,0,0],
                  is_extended_id=False)

print("Sending Mode 04 (Clear DTCs)...")
bus.send(msg)

# Wait for ECU confirmation (0x7E8 with .data[1] == 0x44)
end = time.time() + 1
cleared = False
while time.time() < end:
    resp = bus.recv(0.1)
    if not resp:
        continue
    if resp.arbitration_id == 0x7E8 and resp.data[1] == 0x44:
        print("ECU response: DTCs cleared!")
        cleared = True
        break

if not cleared:
    print("No response from ECU (gateway running? obd_ecu running?)")

print("\nPress Enter to close...")
input()
EOF

