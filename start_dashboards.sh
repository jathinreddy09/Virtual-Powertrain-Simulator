#!/bin/bash
cd /home/jathin/Desktop/CAN_LAB

echo "Starting dashboards and tester (using venv)..."
echo

# Start all three in the SAME terminal (in background) so we see errors if any

./venv/bin/python3 dbc_dashboard.py &
echo " - DBC dashboard started (vcan0)"

./venv/bin/python3 gui_dashboard.py &
echo " - GUI dashboard started (vcan1 via gateway)"

./venv/bin/python3 obd_tester.py &
echo " - OBD tester started (vcan1 via gateway)"

echo
echo "If something failed, errors will be shown above."
echo "Press Enter to close this window..."
read
