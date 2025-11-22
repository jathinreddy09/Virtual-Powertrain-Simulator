import can
import time

bus = can.interface.Bus(channel="vcan1", bustype="socketcan")

# Mode 04
msg = can.Message(arbitration_id=0x7E0, data=[0x01,0x04,0,0,0,0,0,0], is_extended_id=False)
bus.send(msg)
print("Sent Mode 04 request...")

end = time.time() + 1
while time.time() < end:
    resp = bus.recv(0.1)
    if resp and resp.arbitration_id == 0x7E8 and resp.data[1] == 0x44:
        print("ECU confirmed: DTCs cleared!")
        break
