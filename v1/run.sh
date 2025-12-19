#!/bin/bash

# Traffic analysis pipeline
# Collects data for specified duration, then analyzes

DURATION_HOURS=1
DURATION_SECONDS=$((DURATION_HOURS * 3600))

echo "Starting traffic detection for ${DURATION_HOURS} hour(s)..."
echo "Press Ctrl+C to stop early"
echo ""

# Run detection in background and get its PID
python3 detect_cars.py &
DETECT_PID=$!

# Wait for specified duration or until user interrupts
sleep $DURATION_SECONDS &
SLEEP_PID=$!

# Handle Ctrl+C
trap "kill $SLEEP_PID 2>/dev/null; kill $DETECT_PID 2>/dev/null; echo 'Interrupted by user'" INT

# Wait for either sleep to finish or detection to end
wait $SLEEP_PID 2>/dev/null
SLEEP_EXIT=$?

# If sleep completed, stop detection
if [ $SLEEP_EXIT -eq 0 ]; then
    echo ""
    echo "Time's up! Stopping detection..."
    kill $DETECT_PID 2>/dev/null
    wait $DETECT_PID 2>/dev/null
fi

echo ""
echo "Detection complete"
echo ""

# Find the most recent CSV file
LATEST_CSV=$(ls -t traffic_data_*.csv 2>/dev/null | head -1)

if [ -z "$LATEST_CSV" ]; then
    echo "Error: No CSV file found"
    exit 1
fi

echo "Found data file: $LATEST_CSV"
echo ""
echo "="
echo "ANALYSIS"
echo "="
echo ""

# Run analysis
python3 analyze.py "$LATEST_CSV"

echo ""
echo "Complete"
