#!/bin/bash
# Setup two virtual CAN buses: vcan0 and vcan1

set -e

echo "Loading vcan module..."
sudo modprobe vcan

echo "Creating vcan0 and vcan1..."
# Ignore errors if they already exist
sudo ip link add dev vcan0 type vcan 2>/dev/null || true
sudo ip link add dev vcan1 type vcan 2>/dev/null || true

echo "Bringing interfaces up..."
sudo ip link set up vcan0
sudo ip link set up vcan1

echo
echo "vcan0 and vcan1 are up:"
ip link show vcan0
ip link show vcan1
