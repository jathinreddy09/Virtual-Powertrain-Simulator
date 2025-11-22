#!/bin/bash
echo "Setting up vcan0..."

sudo modprobe vcan 2>/dev/null

# If vcan0 exists, delete it
if ip link show vcan0 >/dev/null 2>&1; then
    echo "vcan0 already exists... resetting..."
    sudo ip link del vcan0
fi

sudo ip link add dev vcan0 type vcan
sudo ip link set up vcan0

echo "vcan0 is ready!"
sleep 2
