#!/bin/bash

# VaidyaVihar Backend Monitor Script
# Automatically restarts the backend if it crashes

cd "$(dirname "$0")"

echo "🔄 Starting Backend Monitor (Auto-Restart Enabled)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Counter for restart attempts
RESTART_COUNT=0
MAX_RESTARTS=10

while [ $RESTART_COUNT -lt $MAX_RESTARTS ]; do
    echo "🚀 Starting backend (Attempt $((RESTART_COUNT + 1))/$MAX_RESTARTS)..."
    echo "⏰ $(date)"
    echo ""
    
    # Run the backend
    bash start_backend.sh
    
    EXIT_CODE=$?
    RESTART_COUNT=$((RESTART_COUNT + 1))
    
    if [ $EXIT_CODE -eq 0 ]; then
        echo "✅ Backend stopped gracefully (Ctrl+C)"
        break
    else
        echo ""
        echo "⚠️  Backend crashed! Restarting in 3 seconds..."
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        sleep 3
    fi
done

if [ $RESTART_COUNT -ge $MAX_RESTARTS ]; then
    echo ""
    echo "❌ Maximum restart attempts ($MAX_RESTARTS) reached!"
    echo "❌ Backend is failing to start. Please check the logs and fix the issue."
    echo "📝 Check: backend.log"
fi
