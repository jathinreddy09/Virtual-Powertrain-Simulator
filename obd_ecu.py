import can
import sys
import time

sys.stdout.write("\033]0;OBD ECU\007")
sys.stdout.flush()

bus = can.interface.Bus(channel="vcan0", bustype="socketcan")

# Live values from Engine ECU
state = {
    "rpm": 0.0,
    "speed": 0.0,
    "coolant": 0.0,
}

# Simple DTC set (SAE-style codes)
dtcs = {"P0128", "P0300"}

def update_from_engine(msg):
    """Update live values from EngineData (0x100)."""
    if msg.arbitration_id != 0x100 or len(msg.data) < 4:
        return
    d = msg.data
    rpm_raw = (d[0] << 8) | d[1]
    state["rpm"] = rpm_raw * 4
    state["speed"] = d[2]
    state["coolant"] = d[3] - 40

def encode_dtc(code):
    """
    Encode a DTC string like 'P0301' into two bytes A,B.
    SAE J2012 style:
      A = (system_bits << 6) | (D1 << 4) | D2
      B = (D3 << 4) | D4
    where system_bits: P=0,C=1,B=2,U=3
    """
    if len(code) != 5:
        return 0x00, 0x00
    sys_char = code[0]
    d1 = int(code[1])
    d2 = int(code[2])
    d3 = int(code[3])
    d4 = int(code[4])

    sys_bits = {"P": 0, "C": 1, "B": 2, "U": 3}.get(sys_char, 0)
    A = (sys_bits << 6) | (d1 << 4) | d2
    B = (d3 << 4) | d4
    return A, B

def handle_mode01_request(msg):
    """Handle Mode 01 (current data) PID requests."""
    d = msg.data
    if len(d) < 3:
        return None

    length = d[0]
    if length < 2:
        return None

    mode_req = d[1]
    pid = d[2]
    if mode_req != 0x01:
        return None

    mode_resp = 0x40 + mode_req  # 0x41

    resp_data = [0x00] * 8
    resp_data[1] = mode_resp
    resp_data[2] = pid

    if pid == 0x0C:  # RPM
        rpm = max(0, min(int(state["rpm"]), 16383))
        rpm_raw = int(rpm * 4)  # OBD-II encoding: (A*256 + B)/4 = RPM
        A = (rpm_raw >> 8) & 0xFF
        B = rpm_raw & 0xFF
        resp_data[0] = 0x04
        resp_data[3] = A
        resp_data[4] = B

    elif pid == 0x0D:  # Speed
        spd = max(0, min(int(state["speed"]), 255))
        resp_data[0] = 0x03
        resp_data[3] = spd

    elif pid == 0x05:  # Coolant
        temp = int(state["coolant"]) + 40
        temp = max(0, min(temp, 255))
        resp_data[0] = 0x03
        resp_data[3] = temp

    else:
        return None

    return resp_data

def handle_mode03_request():
    """Mode 03: request emission-related DTCs."""
    # Response: 0x43 + list of DTCs (2 bytes each)
    resp_data = [0x00] * 8
    mode_resp = 0x43

    if not dtcs:
        # No codes stored – respond with zero DTCs
        resp_data[0] = 0x02  # length: mode only
        resp_data[1] = mode_resp
        return resp_data

    # For simplicity, only return up to 3 DTCs (fits in one frame)
    codes = list(dtcs)[:3]
    length = 2 + 2 * len(codes)  # mode + 2 bytes per DTC
    resp_data[0] = length
    resp_data[1] = mode_resp

    idx = 3
    for code in codes:
        A, B = encode_dtc(code)
        if idx >= 8:
            break
        resp_data[idx] = A
        if idx + 1 < 8:
            resp_data[idx + 1] = B
        idx += 2

    return resp_data

def handle_mode04_request():
    """Mode 04: clear DTCs."""
    dtcs.clear()
    resp_data = [0x00] * 8
    resp_data[0] = 0x02  # length: mode only
    resp_data[1] = 0x44  # response to mode 04
    return resp_data

def inject_faults():
    """Simple logic to auto-create some DTCs based on live values."""
    # Coolant below ~80°C at any reasonable speed → P0128
    if state["coolant"] < 80 and state["speed"] > 10:
        dtcs.add("P0128")

    # RPM above 2500 at low speed → P0300
    if state["rpm"] > 2500 and state["speed"] < 15:
        dtcs.add("P0300")

def handle_obd_request(msg):
    """Handle any OBD request on 0x7E0 (Mode 01, 03, 04)."""
    global dtcs

    if msg.arbitration_id != 0x7E0:
        return

    d = msg.data
    if len(d) < 2:
        return

    length = d[0]
    if length < 1:
        return

    mode_req = d[1]

    resp_data = None

    if mode_req == 0x01:
        resp_data = handle_mode01_request(msg)
    elif mode_req == 0x03:
        resp_data = handle_mode03_request()
    elif mode_req == 0x04:
        resp_data = handle_mode04_request()

    if resp_data is None:
        return

    resp = can.Message(
        arbitration_id=0x7E8,
        data=resp_data,
        is_extended_id=False,
    )
    bus.send(resp)

    print(f"OBD RESP mode 0x{mode_req:02X} data={resp_data}")

print("OBD ECU running on vcan0")
print("  Mode 01: PIDs 05,0C,0D")
print("  Mode 03: Read DTCs (P0xxx)")
print("  Mode 04: Clear DTCs")
print("Ctrl+C to stop.\n")

try:
    while True:
        msg = bus.recv(0.1)
        if msg is None:
            continue

        if msg.arbitration_id == 0x100:
            update_from_engine(msg)
           # inject_faults()

        if msg.arbitration_id == 0x7E0:
            handle_obd_request(msg)

except KeyboardInterrupt:
    print("\nOBD ECU stopped.")
