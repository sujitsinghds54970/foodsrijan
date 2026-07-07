#!/bin/bash

# Robust Backend Startup Script
# This script ensures the backend stays running by automatically restarting on crashes

echo "=========================================="
echo "Starting Robust Backend Server"
echo "=========================================="

# Step 1: Kill any existing process on port 8000
echo "Step 1: Checking for existing processes on port 8000..."
if lsof -ti :8000 > /dev/null 2>&1; then
    echo "Found process on port 8000. Killing it..."
    lsof -ti :8000 | xargs kill -9 2>/dev/null
    echo "Process killed successfully."
else
    echo "No existing process found on port 8000."
fi

# Step 2: Wait for port to fully release
echo ""
echo "Step 2: Waiting 3 seconds for port to fully release..."
sleep 3
echo "Port should now be available."

# Step 3: Activate virtual environment
echo ""
echo "Step 3: Activating virtual environment..."
cd "$(dirname "$0")"
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "Virtual environment activated."
elif [ -d "../venv" ]; then
    source ../venv/bin/activate
    echo "Virtual environment activated from parent directory."
else
    echo "WARNING: No virtual environment found. Proceeding without activation."
fi

# Step 4: Start backend with auto-restart loop
echo ""
echo "Step 4: Starting backend with auto-restart capability..."
echo "=========================================="
echo "Backend will automatically restart if it crashes."
echo "Press Ctrl+C to stop the server permanently."
echo "=========================================="
echo ""

# Counter for tracking restarts
RESTART_COUNT=0

while true; do
    if [ $RESTART_COUNT -gt 0 ]; then
        echo ""
        echo "=========================================="
        echo "RESTART #$RESTART_COUNT"
        echo "=========================================="
    fi
    
    echo "Starting uvicorn server..."
    echo "Time: $(date)"
    echo ""
    
    # Run the backend server
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --log-level debug
    
    # If we reach here, the server has stopped/crashed
    EXIT_CODE=$?
    RESTART_COUNT=$((RESTART_COUNT + 1))
    
    echo ""
    echo "=========================================="
    echo "Backend stopped with exit code: $EXIT_CODE"
    echo "Backend crashed! Restarting in 2 seconds..."
    echo "=========================================="
    
    sleep 2
done
