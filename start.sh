#!/bin/bash

# Set working directory to script location
cd "$(dirname "$0")"

echo "Starting Beacon Positioning System..."

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv .venv
    source .venv/bin/activate
    echo "Installing Python dependencies..."
    pip install -e .
else
    source .venv/bin/activate
fi

# Start backend server
echo "Starting backend server..."
uvicorn server.main:app --host 0.0.0.0 --port 8022 &
BACKEND_PID=$!

# Give backend a moment to start
sleep 2

# Navigate to the web directory and start frontend
echo "Starting frontend server..."
cd web
npm install --no-audit --no-fund --silent
npm run dev &
FRONTEND_PID=$!

# Wait for the frontend to be ready (give it some time to start)
echo "Waiting for frontend to start..."
sleep 10

# Open browser - Using chromium-browser which is common on Raspberry Pi
echo "Opening browser..."
DISPLAY=:0 chromium-browser --start-fullscreen http://localhost:5173 &
BROWSER_PID=$!

# Function to handle script termination
cleanup() {
    echo "Shutting down services..."
    kill $BROWSER_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    kill $BACKEND_PID 2>/dev/null
    exit 0
}

# Set up trap for cleanup on script termination
trap cleanup SIGINT SIGTERM

echo "System started! Press Ctrl+C to stop all services."

# Keep script running until Ctrl+C
wait 