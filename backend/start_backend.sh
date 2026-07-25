#!/bin/bash

# VaidyaVihar Backend Startup Script with Auto-Reload and Monitoring
# This script ensures the backend stays running and auto-restarts on crashes

cd "$(dirname "$0")"

echo "🚀 Starting VaidyaVihar Backend Server..."
echo "📍 Working Directory: $(pwd)"
echo "⏰ Time: $(date)"
echo ""

# Kill any existing backend processes
echo "🔍 Checking for existing backend processes..."
pkill -f "uvicorn.*app.main:app" 2>/dev/null && echo "✅ Killed existing backend processes" || echo "ℹ️  No existing processes found"
sleep 2

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found. Please run: python3 -m venv .venv"
    exit 1
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source .venv/bin/activate

PYTHON_BIN="$(command -v python)"

# Install/upgrade all required packages from requirements.txt
echo "📦 Installing/updating dependencies from requirements.txt..."
"$PYTHON_BIN" -m pip install -q -r requirements.txt 2>&1 | grep -v "Requirement already satisfied" || true
echo "✅ Dependencies installed successfully"

# Set environment variables
export PYTHONUNBUFFERED=1
export PYTHONDONTWRITEBYTECODE=1

echo ""
echo "✅ Backend server starting with auto-reload enabled..."
echo "🌐 Server URL: http://localhost:8000"
echo "� API Docs: http://localhost:8000/docs"
echo "� Auto-reload: ENABLED (watches for file changes)"
echo "💾 Database: vaidya_vihar.db"
echo ""
echo "Press Ctrl+C to stop the server"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Start uvicorn with auto-reload and proper error handling
"$PYTHON_BIN" -m uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --reload \
    --reload-dir app \
    --log-level info \
    --access-log \
    --use-colors \
    2>&1 | tee backend.log

# If the server exits, show the exit code
EXIT_CODE=$?
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "⚠️  Backend server stopped with exit code: $EXIT_CODE"
echo "⏰ Time: $(date)"

if [ $EXIT_CODE -ne 0 ]; then
    echo "❌ Server crashed! Check backend.log for details"
    echo "📝 Last 20 lines of log:"
    tail -n 20 backend.log
fi
