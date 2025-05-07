# Multi-Tracker Beacon Positioning System

This project provides a system for tracking multiple devices (trackers) indoors using beacon signals (primarily iBeacon or MAC-address based like SenseCAP) and visualizing their positions on a web-based map.

## Overview

The system consists of three main components:

1.  **Backend Server (`server/`)**:
    *   Built with Python and FastAPI.
    *   Receives tracker beacon data via an MQTT subscription (specifically configured for SenseCAP format with MeasurementID "5002").
    *   Manages two primary configuration files:
        *   `server/miniprogram_config.json`: For map layout, beacon definitions (including MAC addresses), and signal propagation settings. Typically sourced from the miniprogram tool and uploaded via the web UI.
        *   `server/server_runtime_config.json`: For MQTT broker details, backend server port, and Kalman filter parameters. Managed via the web UI or manually on the server.
    *   Calculates the position of each tracker based on received signal strengths (RSSI) and configured beacon locations (matching by MAC address) using trilateration.
    *   Employs a Kalman filter for smoothing calculated positions.
    *   Manages the state of tracked devices.
    *   Broadcasts tracker position updates and configuration changes to connected frontend clients via WebSockets.
    *   Provides API endpoints for configuration management and MQTT control.

2.  **Web Frontend (`web/`)**:
    *   Built with Vue 3 and Vite.
    *   Connects to the backend server via WebSockets for real-time updates.
    *   Provides an interface to:
        *   Load the "Map & Beacon Configuration" (`miniprogram_config.json`) by pasting JSON.
        *   View and edit "Server Runtime Configuration" (MQTT, Server Port, Kalman params).
        *   Manually connect/disconnect the MQTT client.
    *   Displays the configured map layout and beacon locations using HTML Canvas.
    *   Visualizes the real-time positions of tracked devices on the map.
    *   Lists currently tracked devices and their status.

3.  **Miniprogram Configuration Tool (`miniprogram/`)**:
    *   A Weixin Mini Program designed to run on a mobile device.
    *   Allows users to:
        *   Upload a map layout.
        *   Scan for nearby iBeacons or manually input beacon details (including MAC addresses).
        *   Place configured beacons onto the uploaded map.
        *   Configure the signal propagation factor (n).
    *   Exports the complete map and beacon configuration as a JSON string, ready to be pasted into the Web Frontend.

## Architecture & Data Flow

```
+--------------------------+     +-------------------------+      +-----------------+
| Tracker Device           | --> | MQTT Broker             | M--> | Backend Server  |
| (e.g., SenseCAP T1000)   |     | (e.g., Seeed's SenseCAP | Q--> | (FastAPI)       |-----> WebSocket
| - Scans Beacons          |     |  OpenStream, or other)  | T--> | - Receives Reports  |
| - Publishes to MQTT topic|     +-------------------------+ T    | - Calculates Pos    |<---+ (Frontend UI)
+--------------------------+                                     | - Manages State     |
                                                                 | - Serves Config/API |
                                                                 +---------|---------+
                                                                           | (HTTP API for Config)
       +-----------------------+      +------------------------+           |
       | Weixin Mini Program   | ---> | User copies JSON to    | --------->|
       | (Configuration Tool)  |      | Web UI Paste Area      |           |
       | - Configure Map       |      +------------------------+           |
       | - Configure Beacons   |                                           |
       | - Export Config JSON  |                                           |
       +-----------------------+                                           V
                                                                 +-----------------+
                                                                 | Web Frontend    |
                                                                 | (Vue 3)         |
                                                                 | - Config Mgmt   |
                                                                 | - Displays Map  |
                                                                 | - Shows Trackers|
                                                                 +-----------------+\
```

1.  **Configuration:**
    *   **Map & Beacons:** Use the Mini Program tool to define the map layout and beacon locations/MAC addresses. Export the configuration JSON.
    *   **Server Runtime:** In the Web Frontend, navigate to "Show Settings" to configure MQTT broker details, server port, and Kalman parameters. This creates/updates `server/server_runtime_config.json`.
2.  **Load Map & Beacon Config:** In the Web Frontend, paste the JSON exported from the Mini Program into the "Map & Beacon Configuration" section. This updates `server/miniprogram_config.json`.
3.  **Connect MQTT:** In the Web Frontend, click "Connect MQTT". The backend will subscribe to the topic defined in `server_runtime_config.json`.
4.  **Tracker Data:** Trackers (e.g., SenseCAP devices) publish beacon scan data (MAC addresses, RSSI) to the configured MQTT topic. The backend specifically listens for messages with `MeasurementID == "5002"` from SenseCAP devices.
5.  **Position Calculation:** The Backend calculates the tracker's position using the received data and the loaded configurations.
6.  **Visualization:** The Backend broadcasts position updates via WebSocket to the Web Frontend, which displays the trackers on the map.

## Setup

**Prerequisites:**

*   **Node.js:** Latest LTS version recommended (for Vue frontend).
*   **npm:** Comes with Node.js.
*   **Python:** 3.10+ recommended.
*   **uv:** (Recommended Python package manager) or `pip`.
*   **Weixin DevTools:** For running and debugging the Mini Program configuration tool.

**1. Backend Server Setup:**

```bash
# Navigate to the project root directory
# cd /path/to/your/beacon_posistion_r1000

# Create and activate a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# or: .venv\\Scripts\\activate # Windows

# Install Python dependencies using uv (or pip)
uv pip install -r requirements.txt 
# If requirements.txt is not up-to-date, you might need to install from pyproject.toml:
# uv pip install . 
```
An `__init__.py` file in the `server/` directory makes it a Python package.

**2. Web Frontend Setup:**

```bash
# Navigate to the web directory
cd web

# Install Node.js dependencies
npm install
```
The frontend uses a Vite proxy (configured in `web/vite.config.js`) to forward API (`/api`) and WebSocket (`/ws`) requests to the backend during development.

**3. Miniprogram Tool Setup:**

*   Open Weixin DevTools.
*   Import Project -> Select the `miniprogram/` directory.
*   The Mini Program allows configuration of map, beacons (including MAC addresses for non-iBeacon SenseCAP compatibility), and signal propagation factor.

## Configuration Files

The backend relies on two main JSON configuration files located in the `server/` directory:

1.  **`server/miniprogram_config.json`**
    *   **Purpose:** Defines the map layout, beacon locations (x, y coordinates), beacon identifiers (MAC address, display name, TxPower/reference RSSI), and the signal propagation factor (n).
    *   **Source:** Generated by the **Miniprogram Configuration Tool** and then pasted into the "Map & Beacon Configuration" section of the **Web Frontend UI**.
    *   **Example Snippet (conceptual):**
        ```json
        {
          "map": {
            "name": "Sample Map",
            "width": 20.0,
            "height": 15.0,
            // ... other map properties ...
            "entities": [ /* wall polylines, etc. */ ]
          },
          "beacons": [
            {
              "deviceId": "MBeaco1",
              "displayName": "Entrance Beacon",
              "macAddress": "C3:00:00:3E:7D:DA", // Crucial for matching SenseCAP data
              "x": 2.5,
              "y": 3.0,
              "txPower": -59 // Reference RSSI at 1m
            }
            // ... more beacons
          ],
          "settings": {
            "signalPropagationFactor": 2.5
          }
        }
        ```
    *   A full example template can be viewed in the Web Frontend UI when loading the configuration.

2.  **`server/server_runtime_config.json`**
    *   **Purpose:** Defines MQTT broker connection details, the backend server port, and Kalman filter parameters.
    *   **Source:** Managed via the "Server Runtime Configuration" panel in the **Web Frontend UI**, or can be created/edited manually on the server.
    *   **Example Structure:**
        ```json
        {
          "mqtt": {
            "brokerHost": "sensecap-openstream.seeed.cc",
            "brokerPort": 1883,
            "username": "org-YOUR_ORG_ID",
            "password": "YOUR_MQTT_PASSWORD",
            "applicationID": "YOUR_SEEED_ORG_ID", // Used in the topic pattern
            "topicPattern": "/device_sensor_data/{ApplicationID}/+/+/+/+", // For SenseCAP
            "clientID": "beacon_positioning_system_client_123", // Optional, but recommended
            "enabled": true // Note: This currently only indicates if config is present; manual connection is required via UI.
          },
          "server": {
            "port": 8000 // Port for the FastAPI backend
          },
          "kalman": {
            "processVariance": 1.0,
            "measurementVariance": 10.0
          }
        }
        ```

## Running the System

1.  **Prepare Configuration Files:**
    *   Ensure `server/server_runtime_config.json` exists and is correctly configured with your MQTT broker details and desired server port. You can do this via the UI once the server is running, or create it manually first.
    *   Have your map & beacon configuration JSON (from the miniprogram tool) ready to paste into the UI.

2.  **Start Backend Server:**
    ```bash
    # Navigate to the project root directory
    # Activate virtual env: source .venv/bin/activate

    # IMPORTANT: Run WITHOUT --reload for stable MQTT and WebSocket operation
    uvicorn server.main:app --host 0.0.0.0 --port <your_configured_port>
    # Example: uvicorn server.main:app --host 0.0.0.0 --port 8000
    ```
    *   **Note on `--reload`**: Due to interactions between the Paho MQTT client's threading model and Uvicorn's auto-reloader, using the `--reload` flag can cause WebSocket connections to drop and MQTT client state to become inconsistent. For stable operation, especially when testing MQTT features, **run the server without `--reload`**. For backend code changes, a manual restart is necessary.

3.  **Start Frontend Development Server:**
    ```bash
    cd web
    npm run dev
    ```
    Access the frontend at `http://localhost:5173` (or the port specified by Vite in the terminal).

4.  **Initial Setup via Web UI:**
    *   Open the Web Frontend in your browser.
    *   If `server_runtime_config.json` was not pre-configured, click "Show Settings", fill in your MQTT broker details, server port, and Kalman parameters, then save.
    *   In the "Map & Beacon Configuration" panel, click "Load Config via Paste", paste the JSON from your miniprogram tool, and submit. The map and beacons should appear.
    *   In the top panel, click "Connect MQTT" to establish the connection to your MQTT broker.

5.  **View Results:**
    *   If trackers are publishing data to the configured MQTT topic (and matching `MeasurementID "5002"` for SenseCAP), they should appear on the live map and in the trackers list.

## Key Functionality & Files

*   **MQTT Data Parsing:** `server/main.py` includes `parse_sensecap_payload` for handling incoming SenseCAP MQTT messages. The `on_message` callback filters for `MeasurementID "5002"`.
*   **Positioning:** `server/positioning.py` contains distance calculation and trilateration. Beacons are matched using MAC addresses.
*   **Configuration Management:** `server/config_manager.py` handles loading and saving of the two JSON configuration files.
*   **State Management & WebSockets:** `server/main.py` manages tracker states and uses `ConnectionManager` for broadcasting updates.
*   **Frontend UI Components:**
    *   `web/src/App.vue`: Main application shell, WebSocket handling, MQTT controls, and overall layout.
    *   `web/src/components/MapView.vue`: Renders the map and trackers.
    *   `web/src/components/ServerSettings.vue`: UI for managing `server_runtime_config.json`.

## Troubleshooting

*   **WebSocket Disconnects / MQTT Status Not Updating:** If using `uvicorn` with `--reload`, this is the most likely cause. Run the backend server without the `--reload` flag.
*   **`NameError` or `AttributeError` in Backend:** Ensure all helper functions (like `parse_sensecap_payload`) are correctly defined and that constants (like `PASSWORD_PLACEHOLDER`) are present in their respective modules.
*   **Frontend Not Loading Data / API Errors:** Check the browser's developer console for JavaScript errors or network errors (404s, CORS issues if proxy is misconfigured). Ensure the Vite proxy in `web/vite.config.js` is correctly forwarding `/api` and `/ws` requests to your backend's host and port.
*   **MQTT Connection Issues:** Double-check all MQTT settings in `server_runtime_config.json` (broker host, port, credentials, client ID, topic, ApplicationID). Verify connectivity to the broker with another MQTT tool if unsure.
*   **No Trackers Appearing:**
    *   Confirm MQTT is connected via the UI.
    *   Ensure trackers are publishing to the correct topic and `ApplicationID` as configured.
    *   For SenseCAP, verify data is under `MeasurementID "5002"`.
    *   Check that beacon MAC addresses in your `miniprogram_config.json` match those being sent by the trackers.
    *   Review backend logs for errors during message parsing or position calculation. 