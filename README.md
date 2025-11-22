# Virtual Powertrain CAN Simulation

This project is a **multi-ECU virtual powertrain simulation** built around a CAN bus architecture.
It is designed to mimic an engine ECU, transmission ECU, and dashboard cluster communicating over
CAN (using SocketCAN / virtual CAN), with simple driver inputs and engine/vehicle dynamics models.

> Built on Debian with Python, `python-can`, and `cantools`, targeting automotive electronics,
> diagnostics, and HIL-style experimentation.

---

## Features

- **Engine ECU simulation**
  - Models RPM, torque, throttle response, fuel cut, and basic protection logic.
  - Publishes engine state (RPM, throttle, torque, load) on a **powertrain CAN bus**.
- **Transmission ECU simulation**
  - Calculates gear, shift logic, and engine braking behavior from vehicle speed & throttle.
  - Commands target RPM for the engine ECU based on gear and mode (DRIVE / SPORT / MANUAL).
- **Gateway ECU**
  - Bridges powertrain CAN and diagnostic CAN (e.g. PT <-> OBD / vcan1).
  - Handles forwarding of OBD-like request / response frames.
- **GUI dashboard**
  - Visualizes live RPM, speed, gear, throttle, and mode.
  - Useful for tuning control logic and debugging CAN traffic.
- **Master control script**
  - Convenience launcher to spin up all ECUs and the dashboard together.
- **Shell helpers**
  - Scripts to bring up virtual CAN interfaces and start individual ECUs on demand.

---

## Repository Layout

```text
CAN_LAB/
├── engine_ecu.py        # Engine ECU model + CAN node
├── trans_ecu.py         # Transmission ECU model + CAN node
├── gui_dashboard.py     # Tkinter / GUI cluster visualizing live signals
├── gateway_ecu.py       # CAN gateway between PT and diagnostic buses
├── master_control.py    # Orchestrator to start/monitor ECUs
├── *.dbc                # CAN database files for powertrain & diagnostics
├── start_*.sh           # Helper scripts for launching components
├── docs/
│   └── ARCHITECTURE.md  # System architecture diagram & explanation
├── venv/                # Local virtual environment (ignored in git)
└── README.md
```

> Note: The `venv/` directory is only kept in this archive for completeness.
> In a real GitHub repo, it should be excluded via `.gitignore`.

---

## System Architecture

The project uses **multiple CAN buses** and ECUs:

- **Engine ECU (`engine_ecu.py`)**
  - Subscribes to PT control messages (e.g., target RPM, gear, mode).
  - Publishes engine state frames (RPM, torque, load) on the PT bus.
- **Transmission ECU (`trans_ecu.py`)**
  - Computes shift decisions from vehicle speed + throttle.
  - Sends target RPM + gear to Engine ECU over PT bus.
- **Gateway ECU (`gateway_ecu.py`)**
  - Bridges PT bus and diagnostic bus.
  - Forwards OBD-style requests (0x7E0/0x7E8) between tools and engine ECU.
- **GUI Dashboard (`gui_dashboard.py`)**
  - Listens to PT bus and renders a live dashboard.

See `docs/ARCHITECTURE.md` for a mermaid diagram and more detail.

---

## Getting Started

### 1. Environment

- OS: Debian / Ubuntu (SocketCAN supported)
- Python: 3.x
- Recommended: create and use a virtual environment instead of committing `venv/`.

Install core dependencies:

```bash
pip install python-can cantools
```

### 2. Setup virtual CAN

Example (adapt to your naming):

```bash
# Create two virtual CAN interfaces
sudo modprobe vcan
sudo ip link add dev vcan0 type vcan
sudo ip link add dev vcan1 type vcan
sudo ip link set up vcan0
sudo ip link set up vcan1
```

- `vcan0` – powertrain bus (PT)
- `vcan1` – diagnostic bus (OBD / tester)

### 3. Run components

In separate terminals, from the `CAN_LAB` directory:

```bash
# Terminal 1 – Engine ECU
python engine_ecu.py

# Terminal 2 – Transmission ECU
python trans_ecu.py

# Terminal 3 – Gateway ECU
python gateway_ecu.py

# Terminal 4 – GUI Dashboard
python gui_dashboard.py
```

Or use the helper shell scripts (e.g., `start_engine_ecu.sh`, `start_trans_ecu.sh`, etc.).

---

## What This Demonstrates (for Portfolio / Resume)

- **Automotive networking (CAN bus)**
  - Designing arbitration IDs, message layouts, and multi-bus topologies.
  - Using `python-can` and `cantools` with DBC files to encode/decode signals.
- **Embedded-style control logic**
  - Implementing engine and transmission behavior (RPM targets, engine braking, shift maps).
  - Experimenting with different drive / sport modes and downshift strategies.
- **Diagnostics & gateways**
  - Simulating an OBD/diagnostic path using a gateway ECU and a second CAN bus.
- **Tooling & observability**
  - Live dashboard for visualizing CAN signals.
  - Separation into multiple ECUs to mirror production powertrain architectures.

Suggested resume bullet (example):

> Built a multi-ECU virtual powertrain simulation (Engine ECU, TCU, gateway, GUI cluster)
> using Python, SocketCAN, and DBC files to model RPM/torque, shift logic, and OBD-style
> diagnostics over a dual-CAN architecture.

---

## Future Ideas

- Add a more realistic engine model (bore, stroke, compression ratio, torque curve).
- Implement simple vehicle longitudinal dynamics (mass, drag, grade).
- Add OBD-II PIDs and fault code simulation.
- Log CAN traffic to file and replay for testing.
- Export this entire project as a teaching lab for CAN & powertrain controls.
