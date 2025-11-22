#!/bin/bash

cd /home/jathin/Desktop/CAN_LAB

# Start dual VCAN (ignore errors if already exist)
sudo ip link add vcan0 type vcan 2>/dev/null
sudo ip link set vcan0 up
sudo ip link add vcan1 type vcan 2>/dev/null
sudo ip link set vcan1 up
echo "VCAN buses ready (vcan0, vcan1)."

# Engine ECU
x-terminal-emulator -e "bash -c './venv/bin/python3 engine_ecu.py; bash'" &

# ABS ECU
x-terminal-emulator -e "bash -c './venv/bin/python3 abs_ecu.py; bash'" &

# Transmission ECU
x-terminal-emulator -e "bash -c './venv/bin/python3 trans_ecu.py; bash'" &

# OBD ECU
x-terminal-emulator -e "bash -c './venv/bin/python3 obd_ecu.py; bash'" &

# CAN Gateway
x-terminal-emulator -e "bash -c './venv/bin/python3 gateway_ecu.py; bash'" &

echo
echo "All ECUs started."
echo "Press Enter to close..."
read
