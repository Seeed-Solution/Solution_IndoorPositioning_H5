#!/bin/bash

# Check and initialize configuration files if needed
echo "Checking configuration files..."

# Create json directory if it doesn't exist
mkdir -p /app/server/config/json

# Check server_runtime_config.json
if [ ! -f "/app/server/config/json/server_runtime_config.json" ]; then
    echo "Warning: server_runtime_config.json not found, using default configuration"
    cp /app/server/config/server_runtime_config_default.json /app/server/config/json/server_runtime_config.json
    echo "Default server runtime configuration copied to /app/server/config/json/server_runtime_config.json"
else
    echo "Found existing server_runtime_config.json"
fi

# Check dashboard_config.json
if [ ! -f "/app/server/config/json/dashboard_config.json" ]; then
    echo "Warning: dashboard_config.json not found, using default configuration"
    cp /app/server/config/dashboard_config_default.json /app/server/config/json/dashboard_config.json
    echo "Default dashboard configuration copied to /app/server/config/json/dashboard_config.json"
else
    echo "Found existing dashboard_config.json"
fi

echo "Configuration check completed."

# Database initialization check
echo "Checking database initialization..."


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
#python -m http.server 5173 &
uvicorn web:app --host 0.0.0.0 --port 5173 &
FRONTEND_PID=$!

cd /app
python -m server.main &
BACKEND_PID=$!

echo "Services started. Press Ctrl+C to stop."

wait $BACKEND_PID
echo "Services stopped. i ready to dead.."