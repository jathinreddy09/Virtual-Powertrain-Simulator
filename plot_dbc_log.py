import matplotlib
matplotlib.use("TkAgg")

import csv
import sys
import os
import glob
import matplotlib.pyplot as plt

def find_latest_log():
    files = glob.glob("dbc_log_*.csv")
    if not files:
        print("No dbc_log_*.csv files found.")
        sys.exit(1)
    return max(files, key=os.path.getmtime)

def main():
    if len(sys.argv) > 1:
        filename = sys.argv[1]
    else:
        filename = find_latest_log()

    print(f"Loading {filename}")

    # Separate time arrays per signal (only where signal exists)
    t_rpm, rpm = [], []
    t_speed, speed = [], []
    t_fl, fl = [], []
    t_fr, fr = [], []
    t_rl, rl = [], []
    t_rr, rr = [], []

    with open(filename) as f:
        reader = csv.DictReader(f)
        t0 = None

        for row in reader:
            if row.get("timestamp", "") == "":
                continue

            ts = float(row["timestamp"])
            if t0 is None:
                t0 = ts
            t_rel = ts - t0

            def has_val(name):
                v = row.get(name, "")
                return v not in ("", None)

            # Engine signals
            if has_val("RPM"):
                t_rpm.append(t_rel)
                rpm.append(float(row["RPM"]))

            if has_val("Speed"):
                t_speed.append(t_rel)
                speed.append(float(row["Speed"]))

            # ABS / wheel speeds
            if has_val("WheelSpeed_FL"):
                t_fl.append(t_rel)
                fl.append(float(row["WheelSpeed_FL"]))

            if has_val("WheelSpeed_FR"):
                t_fr.append(t_rel)
                fr.append(float(row["WheelSpeed_FR"]))

            if has_val("WheelSpeed_RL"):
                t_rl.append(t_rel)
                rl.append(float(row["WheelSpeed_RL"]))

            if has_val("WheelSpeed_RR"):
                t_rr.append(t_rel)
                rr.append(float(row["WheelSpeed_RR"]))

    print(f"Points: RPM={len(rpm)}, Speed={len(speed)}, "
          f"FL={len(fl)}, FR={len(fr)}, RL={len(rl)}, RR={len(rr)}")

    # If nothing decoded, tell the user and exit
    if not any([rpm, speed, fl, fr, rl, rr]):
        print("No decoded signal data found in this log.")
        sys.exit(0)

    # ---- Engine plot ----
    plt.figure()
    plt.title("Engine RPM & Vehicle Speed")
    if rpm:
        plt.plot(t_rpm, rpm, label="RPM")
    if speed:
        plt.plot(t_speed, speed, label="Speed (km/h)")
    plt.xlabel("Time (s)")
    plt.legend()
    plt.grid(True)

    # ---- ABS plot ----
    plt.figure()
    plt.title("Wheel Speeds (ABS)")
    if fl:
        plt.plot(t_fl, fl, label="FL")
    if fr:
        plt.plot(t_fr, fr, label="FR")
    if rl:
        plt.plot(t_rl, rl, label="RL")
    if rr:
        plt.plot(t_rr, rr, label="RR")
    plt.xlabel("Time (s)")
    plt.ylabel("km/h")
    plt.legend()
    plt.grid(True)

    plt.show()

if __name__ == "__main__":
    main()
