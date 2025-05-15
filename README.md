# Beacon Positioning System

This system tracks devices using BLE beacon signals, visualizing their positions on a web-based map. It supports iBeacon-compatible devices and SenseCAP T1000 trackers. It offers two main modes:
1.  **Tracker Mode:** Server-side positioning of multiple dedicated tracker devices via MQTT.
2.  **Personal Mode:** Local device positioning on a user's machine using a dedicated local Bluetooth scanning service.

## Core Components

1.  **Backend Server (`server/`):** Python (FastAPI). Handles MQTT, calculates tracker positions, manages state, and serves the API/WebSockets for Tracker Mode.
2.  **Web Frontend (`web/`):** Vue 3 (Vite). Provides the UI for configuration, map display, and visualization for both modes.
3.  **Local Beacon Service (`local-beacon-service/`):** Node.js. Runs on the user's machine, scans local BLE beacons, and sends data to the Web Frontend via WebSocket for Personal Mode.

## Key Features

*   Real-time tracking (Tracker Mode) & local device positioning (Personal Mode).
*   Web UI for map/beacon configuration and live visualization.
*   Trilateration with Kalman filter smoothing.
*   MQTT integration for Tracker Mode.
*   WebSocket communication for live data.

## Architecture

```
Web UI (Vue 3) <--- WebSocket (Tracker Mode) --- Backend Server (FastAPI) --- MQTT --- Tracker Devices
   ^                                                  |
   |                                                  | (Serves Web UI files)
   +--- WebSocket (Personal Mode, to localhost:8081) -- Local Beacon Service (Node.js on User Machine)
```

## User Guide & Simplified Startup

This guide helps you get the system running, especially using the provided start script for a streamlined experience. For "Personal Mode" (tracking your own device), you will also need to run the Local Beacon Service.

**Prerequisites:**

*   **Node.js:** LTS version (e.g., 18.x, 20.x). Download from [nodejs.org](https://nodejs.org/). (Needed for the web frontend and Local Beacon Service)
*   **Python:** 3.10+. Download from [python.org](https://www.python.org/).
*   **uv:** A fast Python package installer. Installation: `curl -LsSf https://astral.sh/uv/install.sh | sh` or see [uv documentation](https://github.com/astral-sh/uv#installation).
*   **Bluetooth Adapter:** On your computer (for Personal Mode).

**1. One-Click Start (`start.sh` - Recommended for most users):**

   The `start.sh` script (located in the project root) is designed to automate the setup and startup of the Backend Server and Web Frontend.

   ```bash
   # Navigate to the project root directory
   cd /path/to/beacon_posistion_r1000

   # Make the script executable (if needed)
   chmod +x start.sh

   # Run the script
   ./start.sh
   ```
   This script typically:
   *   Sets up a Python virtual environment and installs dependencies using `uv` or `pip`.
   *   Starts the backend server (e.g., `uvicorn server.main:app`).
   *   Installs frontend dependencies (`npm install`) and starts the frontend development server (`npm run dev`).
   *   May attempt to open a browser to the web application.
   *   Press `Ctrl+C` in the terminal where `start.sh` is running to stop all services managed by it.

**2. Run the Local Beacon Service (Required for Personal Mode):**

   This service uses your computer's Bluetooth. It needs to be run separately if you intend to use Personal Mode.

   ```bash
   # Navigate to the local-beacon-service directory
   cd /path/to/beacon_posistion_r1000/local-beacon-service

   # Run the start script (installs dependencies if needed)
   # On Linux/macOS:
   chmod +x start_service.sh
   ./start_service.sh
   # On Windows (using Git Bash):
   # ./start_service.sh
   # For native Windows CMD/PowerShell (follow script instructions or):
   # npm install # Run once
   # node service.js
   ```
   The service will be available at `ws://localhost:8081`.

**3. Using the Web Application:**

   *   Access the main web application (this might be hosted, or run locally by a developer).
   *   **"Map & Beacon Configuration" view:**
      *   Create/Import a map and beacon setup (JSON). Define map, place beacons, ensure MAC addresses & TxPower are correct. Export this "master configuration" JSON.
   *   **"Personal Mode Configuration" view:**
      *   Import the master configuration JSON.
      *   Ensure the Local Beacon Service (Step 2) is running.
      *   Click "Start Local Positioning". Your device's position should appear on the map.
   *   **"Tracker Mode Configuration" view (for tracking other devices via a central server):**
      *   Import a master configuration JSON (updates the central server).
      *   Configure server/MQTT settings if necessary. Trackers will appear on the map if publishing data.

## Developer Guide

This guide is for setting up the development environment.

**Prerequisites:**

*   **Node.js:** LTS version (e.g., 18.x, 20.x).
*   **npm:** (Included with Node.js).
*   **Python:** 3.10+
*   **uv (Recommended) or pip:** For Python packages.

**1. Backend Server Setup (`server/`):**

   ```bash
   cd /path/to/beacon_posistion_r1000
   python -m venv .venv
   source .venv/bin/activate # On Linux/macOS. For Windows: .venv\Scripts\activate
   uv pip install -r server/requirements.txt # Or: pip install -r server/requirements.txt
   ```

**2. Web Frontend Setup (`web/`):**

   ```bash
   cd /path/to/beacon_posistion_r1000/web
   npm install
   ```

**3. Local Beacon Service Setup (`local-beacon-service/`):**

   ```bash
   cd /path/to/beacon_posistion_r1000/local-beacon-service
   npm install
   ```

**4. Configuration Files (Backend - Tracker Mode):**

   Located in `server/`:\
   *   `web_config.json`: Map/beacon layout for server-side positioning. Updated via UI import in "Tracker Mode".
   *   `server_runtime_config.json`: MQTT, server port, Kalman parameters. Managed via UI or manual edit.

**5. Running the System (Development):**

   Run each component in a separate terminal.

   **a. Backend Server (Recommended: `uv run`):**
      ```bash
      # In project root. Assumes 'uv' is installed and Python environment is set up
      # (e.g., by running start.sh once, or by manual venv activation).
      # Replace <port> with port from server_runtime_config.json (e.g., 8022, 8000).
      # 'uv run' will manage the execution within the project's environment.
      uv run uvicorn server.main:app --host 0.0.0.0 --port <port>
      # Note: Avoid Uvicorn's --reload for stable MQTT/WebSocket. Restart manually if needed.
      ```

   **b. Frontend Development Server:**
      ```bash
      cd web
      npm run dev 
      # Access at http://localhost:5173 (or as shown by Vite)
      ```

   **c. Local Beacon Service (for testing Personal Mode):**
      ```bash
      cd local-beacon-service
      node service.js # Or ./start_service.sh
      ```
   
   **d. Initial Setup via Web UI (Development):**
      *   Open the Web Frontend (e.g., `http://localhost:5173`).
      *   **"Tracker Mode Configuration"**: Configure server runtime settings, import map/beacon JSON.
      *   **"Map & Beacon Configuration"**: Create/edit/export master JSON configurations.
      *   **"Personal Mode Configuration"**: Import master JSON, start local positioning (ensure local service is running).

## Key Files & Logic (for Developers)

*   **MQTT Parsing:** `server/main.py` (`parse_sensecap_payload`)
*   **Positioning:** `server/positioning.py`
*   **Kalman Filter:** `server/positioning.py` (`KalmanFilter2D`)
*   **Config Management:** `server/config_manager.py`
*   **WebSockets (Tracker Mode):** `server/main.py`
*   **Local Beacon Scanning (Personal Mode):** `local-beacon-service/service.js`
*   **UI Views:** `web/src/views/` (MasterConfigView, PersonalModeConfigView, TrackerModeConfigView)
*   **Map Component:** `web/src/components/MapView.vue`

