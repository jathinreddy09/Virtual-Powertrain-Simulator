"""Master control / launcher for the virtual powertrain lab.

Entry point that can be used to:
- Bring up virtual CAN interfaces (if desired).
- Start Engine ECU, Transmission ECU, Gateway, and GUI processes.
- Coordinate the multi-ECU simulation from one place.
"""

import sys
import os

STATE_FILE = "/home/jathin/Desktop/CAN_LAB/global_state.txt"

def set_state(value: str):
    value = value.strip().lower()
    with open(STATE_FILE, "w") as f:
        f.write(value + "\n")
    print(f"Global state set to: {value.upper()}")

def main():
    print("Master Control")
    print("Commands:")
    print("  p  -> pause all ECUs/dashboards")
    print("  r  -> resume all")
    print("  q  -> quit controller")
    print()

    # Ensure file exists
    if not os.path.exists(STATE_FILE):
        set_state("run")

    while True:
        try:
            cmd = input("> ").strip().lower()
            if cmd == "p":
                set_state("pause")
            elif cmd == "r":
                set_state("run")
            elif cmd == "q":
                print("Exiting master controller.")
                break
            elif cmd == "":
                continue
            else:
                print("Unknown command. Use p / r / q.")
        except (EOFError, KeyboardInterrupt):
            print("\nExiting master controller.")
            break

if __name__ == "__main__":
    main()
