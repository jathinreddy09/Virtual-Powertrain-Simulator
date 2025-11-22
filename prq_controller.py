import os

STATE_FILE = "/home/jathin/Desktop/CAN_LAB/global_state.txt"

def set_state(value: str):
    value = value.strip().lower()
    with open(STATE_FILE, "w") as f:
        f.write(value)
    print(f"Global state set to: {value}")

def main():
    print("P = pause all ECUs")
    print("R = resume all ECUs")
    print("Q = quit controller")
    print()

    # Default to run
    set_state("run")

    while True:
        cmd = input("[p/r/q] > ").strip().lower()
        if cmd == "p":
            set_state("pause")
        elif cmd == "r":
            set_state("run")
        elif cmd == "q":
            print("Exiting PRQ controller.")
            break
        else:
            print("Use: p = pause, r = run, q = quit")

if __name__ == "__main__":
    main()
