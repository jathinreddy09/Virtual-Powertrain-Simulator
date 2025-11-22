import can
import sys
import time

sys.stdout.write("\033]0;OBD Tester\007")
sys.stdout.flush()

# NOTE: on gateway setup, this should be vcan1
bus = can.interface.Bus(channel="vcan1", bustype="socketcan")

def send_pid(pid):
    data = [0x02, 0x01, pid, 0, 0, 0, 0, 0]
    msg = can.Message(arbitration_id=0x7E0, data=data, is_extended_id=False)
    bus.send(msg)

def wait_for_pid_response(pid, timeout=0.5):
    end_time = time.time() + timeout
    while time.time() < end_time:
        msg = bus.recv(0.05)
        if msg is None:
            continue
        if msg.arbitration_id != 0x7E8:
            continue
        d = msg.data
        if len(d) < 3:
            continue
        if d[1] != 0x41 or d[2] != pid:
            continue
        return d
    return None

def decode_pid(pid, data):
    if pid == 0x0C:  # RPM
        A = data[3]
        B = data[4]
        rpm = ((A * 256) + B) / 4
        return f"{rpm:.0f} rpm"
    if pid == 0x0D:
        spd = data[3]
        return f"{spd} km/h"
    if pid == 0x05:
        temp = data[3] - 40
        return f"{temp} °C"
    return f"raw={data}"

def send_mode03():
    data = [0x01, 0x03, 0, 0, 0, 0, 0, 0]
    msg = can.Message(arbitration_id=0x7E0, data=data, is_extended_id=False)
    bus.send(msg)

def send_mode04():
    data = [0x01, 0x04, 0, 0, 0, 0, 0, 0]
    msg = can.Message(arbitration_id=0x7E0, data=data, is_extended_id=False)
    bus.send(msg)

def wait_for_mode03_response(timeout=0.5):
    end_time = time.time() + timeout
    while time.time() < end_time:
        msg = bus.recv(0.05)
        if msg is None:
            continue
        if msg.arbitration_id != 0x7E8:
            continue
        d = msg.data
        if len(d) < 2:
            continue
        if d[1] != 0x43:
            continue
        return d
    return None

def wait_for_mode04_response(timeout=0.5):
    end_time = time.time() + timeout
    while time.time() < end_time:
        msg = bus.recv(0.05)
        if msg is None:
            continue
        if msg.arbitration_id != 0x7E8:
            continue
        d = msg.data
        if len(d) < 2:
            continue
        if d[1] != 0x44:
            continue
        return d
    return None

def decode_dtcs(data):
    """Decode DTC bytes from a Mode 03 response."""
    if len(data) < 3:
        return []
    length = data[0]
    # no codes
    if length <= 2:
        return []

    dtcs = []
    # DTC bytes start at index 3
    bytes_left = length - 2
    idx = 3
    while bytes_left >= 2 and idx + 1 < len(data):
        A = data[idx]
        B = data[idx + 1]
        if A == 0 and B == 0:
            break

        sys_bits = (A >> 6) & 0x03
        d1 = (A >> 4) & 0x03
        d2 = A & 0x0F
        d3 = (B >> 4) & 0x0F
        d4 = B & 0x0F

        sys_char = {0: "P", 1: "C", 2: "B", 3: "U"}.get(sys_bits, "P")
        code = f"{sys_char}{d1}{d2}{d3}{d4}"
        dtcs.append(code)

        idx += 2
        bytes_left -= 2

    return dtcs

print("Simple OBD-II tester on vcan1 (via gateway)")
print("Polling: PIDs 0C (RPM), 0D (Speed), 05 (Coolant)")
print("Every few cycles: Mode 03 (DTCs). Ctrl+C to stop.\n")

cycle = 0

try:
    while True:
        results = {}

        for pid in (0x0C, 0x0D, 0x05):
            send_pid(pid)
            resp = wait_for_pid_response(pid)
            if resp is None:
                results[pid] = "No resp"
            else:
                results[pid] = decode_pid(pid, resp)

        line = (
            f"RPM: {results[0x0C]:>10} | "
            f"Speed: {results[0x0D]:>10} | "
            f"Coolant: {results[0x05]:>8}"
        )
        print(line)

        # Every 5 cycles, query DTCs
        cycle += 1
        if cycle % 5 == 0:
            send_mode03()
            resp = wait_for_mode03_response()
            if resp is not None:
                codes = decode_dtcs(resp)
                if codes:
                    print("  DTCs:", ", ".join(codes))
                else:
                    print("  DTCs: none")

        time.sleep(1.0)

except KeyboardInterrupt:
    print("\nOBD tester stopped.")
