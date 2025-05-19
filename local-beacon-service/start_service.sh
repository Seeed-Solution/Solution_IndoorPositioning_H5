#!/bin/bash

# Define the directory containing this script (local-beacon-service)
SCRIPT_DIR=$(dirname "$0")

echo "Starting Local Beacon Service..."

# --- Detect Platform ---
OS=$(uname -s)

if [[ "$OS" == "Linux" ]] || [[ "$OS" == "Darwin" ]]; then
    # --- Unix-like (Linux, macOS) Setup and Start ---
    cd "$SCRIPT_DIR"

    # Check if Node.js is installed
    if ! command -v node &> /dev/null
    then
        echo "Error: Node.js is not installed."
        echo "Please download and install Node.js from https://nodejs.org/."
        exit 1
    fi

    # Install dependencies if needed
    echo "Checking and installing dependencies (if necessary)..."
    npm install || {
        echo "Error: npm install failed."
        exit 1
    }
    echo "Dependencies are ready."

    # --- Start the Service (Unix-like) ---
    echo "Starting service.js..."

    # Execute the service script
    # Use exec to replace the current script process with the node process
    exec node service.js

    # The script will only reach here if exec fails
    echo "Error: node service.js failed to start."
    exit 1

elif [[ "$OS" == *"MINGW"* ]] || [[ "$OS" == *"MSYS"* ]]; then
    # Likely Git Bash or similar on Windows
    cd "$SCRIPT_DIR"

    echo "Detected Git Bash/MSYS on Windows."

    # Check if Node.js is installed (assumes node is in PATH)
    if ! command -v node &> /dev/null
    then
        echo "Error: Node.js is not installed or not in PATH."
        echo "Please download and install Node.js from https://nodejs.org/."
        exit 1
    fi

    # Install dependencies if needed
    echo "Checking and installing dependencies (if necessary)..."
    npm install || {
        echo "Error: npm install failed."
        exit 1
    }
     echo "Dependencies are ready."

    # --- Start the Service (Windows Bash) ---
    echo "Starting service.js..."

    # Execute the service script
    exec node service.js

    echo "Error: node service.js failed to start."
    exit 1

else
    # --- Other Platforms (likely native Windows Command Prompt/PowerShell) ---
    echo "This script is primarily for macOS/Linux or Git Bash/MSYS on Windows."
    echo "To run the service on native Windows Command Prompt or PowerShell:"
    echo ""
    echo "1. Open Command Prompt or PowerShell."
    echo "2. Navigate to the service directory:"
    echo "   cd ${SCRIPT_DIR}"
    echo "3. Install dependencies if you haven't already (you only need to do this once):"
    echo "   npm install"
    echo "4. Start the service:"
    echo "   node service.js"
    echo ""
    echo "Ensure Node.js is installed and in your system's PATH."
    exit 1
fi 