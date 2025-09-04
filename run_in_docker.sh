#!/bin/bash

# Function to handle script termination
cleanup() {
    echo "Shutting down services..."
    kill $FRONTEND_PID 2>/dev/null
    kill $BACKEND_PID 2>/dev/null
    exit 0
}

# Set up trap for cleanup on script termination
trap cleanup SIGINT SIGTERM

cd /app/web
npm run dev &
FRONTEND_PID=$!

cd /app
python -m server.main &
BACKEND_PID=$!

echo "Services started. Press Ctrl+C to stop."

wait $BACKEND_PID
echo "Services stopped. i ready to dead.."