# Multi-Tracker Beacon Positioning System (Version 0.1)

This project provides a system for real-time indoor tracking of multiple devices (trackers) using Bluetooth Low Energy (BLE) beacon signals. It visualizes their calculated positions on a dynamic, web-based map. It is designed to work with iBeacon-compatible devices and has specific support for SenseCAP T1000 trackers by matching MAC addresses and parsing their MQTT data format.

## Overview: What Does This Project Do?

The primary goal of this system is to determine and display the location of multiple trackers within a defined indoor area. It achieves this by:

1.  **Receiving Beacon Data:** A backend server listens to an MQTT broker for messages containing beacon scan data from tracker devices (e.g., RSSI, beacon identifiers).
2.  **Configuration (Web-Based):**
    *   **Map & Beacons (Initial Creation & Management):** Users define the physical layout of the indoor space and the precise locations (x, y coordinates) of reference beacons using the **"Map & Beacon Configuration" view** in the web UI. This configuration also includes beacon MAC addresses (crucial for trackers like SenseCAP) and their signal characteristics (TxPower). This tool allows users to create a configuration from scratch, import an existing one, edit it, and then export it as a JSON file.
    *   **"Tracker Mode Configuration" view:** Users import a configuration JSON (typically created or refined in the "Map & Beacon Configuration" view) here. This action updates the main server-side map & beacon settings (stored in `server/web_config.json`) that the backend uses for live tracking.
    *   **"Personal Mode Configuration" view:** Users import a configuration JSON here for in-browser positioning. This configuration is stored locally in the browser.
    *   **Server & MQTT:** Users configure MQTT broker details and server operational parameters via the "Tracker Mode Configuration" view, which hosts the server settings panel. This updates `server/server_runtime_config.json`.
3.  **Position Calculation:** The backend server uses the received signal strength (RSSI) from multiple beacons and their known locations (from `server/web_config.json`) to calculate the tracker's position.
4.  **Position Smoothing:** A Kalman filter is applied to smooth the calculated positions, reducing jitter and improving accuracy.
5.  **Real-time Visualization:**
    *   **Tracker Mode:** The "Tracker Mode Configuration" view in the web frontend displays the map, beacon locations, and the live, smoothed positions of all active trackers. Tracker movements can also be visualized as trails.
    *   **Personal Mode:** The "Personal Mode Configuration" view displays the map and the calculated position of the local device using Web Bluetooth for beacon scanning.
6.  **Data Communication:** The backend communicates with the frontend using WebSockets for real-time updates in Tracker Mode.

The system is composed of three main components:
*   **Backend Server (`server/`):** Python (FastAPI) based, handles MQTT, position calculation, state management, and serves the API and WebSocket.
*   **Web Frontend (`web/`):** Vue 3 and Vite based, provides the user interface for all configuration tasks, map display, and tracker/local device visualization through dedicated views.
    *   **Map & Beacon Configuration:** Allows users to create/import, visually edit (place beacons, define map parameters), and export the complete map and beacon setup as a JSON file. This replaces the previous Miniprogram functionality.
    *   **Tracker Mode Configuration:** For managing server-side tracking, importing the map/beacon setup for the server, and configuring server runtime settings (MQTT, etc.).
    *   **Personal Mode Configuration:** For managing local, in-browser positioning using Web Bluetooth, and importing the map/beacon setup for this mode.
*   ~~**Miniprogram Configuration Tool (`miniprogram/`):** A Weixin (WeChat) Mini Program for easy initial map and beacon setup on a mobile device. This tool allows you to:~~ (This component has been replaced by the Web Frontend's "Map & Beacon Configuration" view)
    *   ~~Upload a map image.~~
    *   ~~Scan for nearby iBeacons (via specified UUIDs for iOS, or general scan for Android).~~
    *   ~~Manually input beacon details.~~
    *   ~~**Crucially, for each beacon, you must ensure the "MAC Address / Device ID" field is correctly populated.**~~
        *   ~~For Android-scanned beacons, this might be pre-filled.~~
        *   ~~**For beacons found via iOS scans (which do not provide MAC addresses) or those added manually, you MUST enter the beacon's actual MAC address (or a unique identifier that your backend will use for matching, especially for trackers like SenseCAP).** This is vital for the backend to correctly identify which physical beacon corresponds to the signals received from trackers.~~
    *   ~~Place beacons on the map (x, y coordinates).~~
    *   ~~Configure the signal propagation factor (n).~~
    *   ~~Export the entire configuration as a JSON string.~~

## Key Features in v0.1

*   Real-time tracking of multiple devices.
*   Support for iBeacon-like signals and MAC-address based beacon identification (e.g., SenseCAP).
*   Web-based UI for configuration and visualization.
*   Trilateration-based positioning with Kalman filter smoothing.
*   Configurable map layouts and beacon placements via a Miniprogram tool or JSON paste.
*   MQTT integration for receiving tracker data.
*   WebSocket communication for live updates to the frontend.
*   Display of tracker movement trails on the map (toggleable).

## Quick Demonstration

Here's a glimpse of the system in action:

**1. Configuring Beacons with the Miniprogram Tool:**

This shows a brief example of how the Weixin Miniprogram tool is used to set up beacon locations and parameters.

![Demonstration of Miniprogram beacon configuration](assets/miniprogram_example.gif)

**2. Live Tracking on the Web Interface:**

This demonstrates the web application displaying live tracker movements on the configured map.

![Demonstration of live tracking on the web interface](assets/web_example.gif)

## Architecture & Data Flow

```
+--------------------------+     +-------------------------+      +-----------------+
| Tracker Device           | --> | MQTT Broker             | M--> | Backend Server  |
| (e.g., SenseCAP T1000)   |     | (e.g., Seeed's SenseCAP | Q--> | (FastAPI)       |-----> WebSocket
| - Scans Beacons          |     |  OpenStream, or other)  | T--> | - Reads web_config.json |
| - Publishes to MQTT topic|     +-------------------------+ T    | - Calculates Pos    |<---+ (Web UI - Tracker Mode)
+--------------------------+                                     | - Manages State     |
                                                                 | - Serves Config/API |
                                                                 +---------|---------+
                                                                           | (HTTP API for Config)
                                                                           |
                                        Web UI (Vue 3) --------------------+
                                        - "Map & Beacon Configuration" (Create/Edit/Export JSON)
                                        - Imports JSON to "Tracker Mode" (updates server/web_config.json)
                                        - Imports JSON to "Personal Mode" (local browser storage)
```

**Data Flow Summary:**
1.  **Configuration (All Web-Based):**
    *   **Master Map & Beacons JSON:** Use the **"Map & Beacon Configuration" view** in the Web UI to create a new map and beacon setup from scratch, or import an existing JSON to view, edit (define map layout, beacon locations, MAC addresses, etc.), and then export a refined master configuration JSON.
    *   **Web UI - Tracker Mode Configuration:** Import the desired map & beacon JSON (typically from the step above). This action updates the server's `web_config.json` file. This view also provides access to the server runtime settings panel (MQTT, port, Kalman) which updates `server/server_runtime_config.json`.
    *   **Web UI - Personal Mode Configuration:** Import a map & beacon JSON. This configuration is saved in the browser's local storage for local device positioning.
2.  **Connect MQTT:** In the "Tracker Mode Configuration" view, after ensuring server runtime settings are correct, the system connects to MQTT (usually on server start if enabled, or via UI interactions if manual connection is offered).
3.  **Tracker Data Transmission:** Trackers publish beacon scan data (MAC addresses, RSSI) to the MQTT topic.
4.  **Position Calculation & Smoothing:** The Backend (using `web_config.json` for beacon/map data) calculates the tracker's position and applies a Kalman filter.
5.  **Visualization:**
    *   **Tracker Mode:** The Backend broadcasts position and state updates via WebSocket to the "Tracker Mode Configuration" view, which displays trackers on the map.
    *   **Personal Mode:** Uses Web Bluetooth and in-browser calculations, displaying the local device's position.

## Setup: Getting Started

Follow these steps to set up and run the system.

**Prerequisites:**

*   **Node.js:** Latest LTS version (e.g., 18.x, 20.x) recommended for the Vue frontend. Download from [nodejs.org](https://nodejs.org/).
*   **npm:** Included with Node.js.
*   **Python:** Version 3.10 or newer is recommended. Download from [python.org](https://www.python.org/).
*   **uv (Recommended) or pip:** For Python package management.
    *   `uv` is a fast Python package installer and resolver. Installation instructions: [uv documentation](https://github.com/astral-sh/uv#installation).
    *   `pip` is the standard Python package installer, usually included with Python.
*   ~~**Weixin Developer Tools:** Required for running and debugging the Miniprogram configuration tool (`miniprogram/`). Download from the official WeChat developer site.~~ (No longer required as Miniprogram is replaced by Web UI)

**Important Note for iOS Beacon Scanning:** ~~To specify which iBeacon UUIDs the Miniprogram should scan for on iOS devices, you need to edit the `miniprogram/config/ble_scan_config.js` file. This file allows you to list multiple UUIDs. Example content:~~
~~`javascript~~~
~~// miniprogram/config/ble_scan_config.js~~
~~const iOSScanUUIDs = [~~
~~  '74278BDA-B644-4520-8F0C-720EAF059935', // Default/Example UUID~~
~~  // 'YOUR-OTHER-BEACON-UUID-HERE' ~~
~~];~~
~~module.exports = { iOSScanUUIDs: iOSScanUUIDs };~~
~~`~~~
~~Make sure to add the UUIDs of the beacons you intend to use.~~ (This is no longer applicable as beacon configuration, including any necessary UUID definitions for scanning in Personal Mode via Web Bluetooth, would be handled within the Web UI or the imported JSON configuration itself.)

**1. Backend Server Setup (Python):**

```bash
# 0. If you use uv, you can directly run the program without setup since uv will take charge of installing the requirement
# uv run uvicorn server.main:app --host 0.0.0.0 --port 8022

# 1. Navigate to the project root directory
# Example: cd /path/to/your/beacon_posistion_r1000

# 2. Create and activate a virtual environment (highly recommended)
python -m venv .venv

# On Linux/macOS:
source .venv/bin/activate

# On Windows (Command Prompt/PowerShell):
# .venv\\Scripts\\activate

# 3. Install Python dependencies:
# Using uv (recommended):
uv pip install -r server/requirements.txt 
# Or, if requirements.txt is outdated or for a cleaner install from project metadata:
# uv pip install .

# Using pip:
pip install -r server/requirements.txt
# Or, if requirements.txt is outdated or for a cleaner install from project metadata:
# pip install . 
# (Ensure your pip is upgraded: pip install --upgrade pip)
```
Note: The project uses `pyproject.toml` to define dependencies. `uv pip install .` or `pip install .` will use this file. `server/requirements.txt` should ideally be generated from `pyproject.toml`. An `__init__.py` file in the `server/` directory makes it a Python package.

**2. Web Frontend Setup (Vue.js):**

```bash
# 1. Navigate to the web directory
cd web

# 2. Install Node.js dependencies
npm install

# 3. (For Development) The frontend uses Vite. 
#    A proxy is configured in `web/vite.config.js` to forward API (`/api`) 
#    and WebSocket (`/ws`) requests to the backend during development.
```

**3. Miniprogram Tool Setup (Weixin/WeChat):**

*   ~~Open Weixin Developer Tools.~~
*   ~~Click "Import Project."~~
*   ~~Select the `miniprogram/` directory from this project.~~
*   ~~Assign an AppID (you can use a test AppID if you don\'t have a registered Mini Program).~~
*   ~~The Mini Program allows you to upload a map image, scan for nearby iBeacons, manually input beacon details (including MAC addresses for non-iBeacon devices like SenseCAP), place beacons on the map, and configure the signal propagation factor (n).~~

## Configuration Files

The backend relies on two main JSON configuration files located in the `server/` directory:

1.  **`server/web_config.json`** (Formerly `miniprogram_config.json` in terms of primary map/beacon data for the server)
    *   **Purpose:** Defines the map layout, beacon locations (x, y coordinates), beacon identifiers (MAC address, display name, TxPower/reference RSSI), and the signal propagation factor (n) **for server-side tracker positioning**.
    *   **Source:** This file is created or updated when a user imports a valid configuration JSON through the **"Tracker Mode Configuration" view** in the Web Frontend. The JSON itself is typically first created or refined in the **"Map & Beacon Configuration" view** in the Web UI.
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
              "uuid": "74278BDA-B644-4520-8F0C-720EAF059935", // May not be used by server if matching by MAC
              "major": 10001, // May not be used
              "minor": 19641, // May not be used
              "x": 2.5,
              "y": 3.0,
              "txPower": -59, // Reference RSSI at 1m
              "displayName": "Entrance Beacon",
              "macAddress": "C3:00:00:3E:7D:DA" // CRITICAL: Must be the actual MAC or unique ID for backend matching.
            }
            // ... more beacons
          ],
          "settings": {
            "signalPropagationFactor": 2.5
            // other general settings from the config file might be stored here
          }
        }
        ```

2.  **`server/server_runtime_config.json`**
    *   **Purpose:** Defines MQTT broker connection details, the backend server port, and Kalman filter parameters.
    *   **Source:** Managed via the "Server Runtime Configuration" panel, accessed from the **"Tracker Mode Configuration" view** in the Web Frontend UI. It can also be created/edited manually on the server before the first run.
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
            "clientID": "beacon_pos_sys_client_01", // Optional, but recommended for uniqueness
            "enabled": true // Note: Manual connection via UI is still primary trigger
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

**Using the One-Click Start Script (Recommended for Raspberry Pi / Linux):**

A `start.sh` script is provided for easy startup of all components (backend, frontend, and browser). This is particularly useful for headless setups or Raspberry Pi deployments.

To use it:
1.  Make sure the script is executable: `chmod +x start.sh`
2.  Run the script from the project root directory: `./start.sh`

The script will:
*   Create a Python virtual environment (`.venv`) if it doesn't exist and install dependencies.
*   Start the backend server.
*   Install frontend dependencies (`npm install` in the `web` directory).
*   Start the frontend development server.
*   Attempt to open Chromium in fullscreen mode to `http://localhost:5173` (common for Raspberry Pi).
*   Provide a cleanup function to stop all services when you press `Ctrl+C`.

**Manual Startup Steps:**

1.  **Prepare Initial Configuration (Web UI):**
    *   Use the **Web UI's "Map & Beacon Configuration" view** to create your map and define beacon locations (ensure MAC addresses are correct, etc.). Export this as a JSON file. This file will be used for import into the "Tracker Mode Configuration" and/or "Personal Mode Configuration" views.
    *   **Server Runtime Config:** Ensure `server/server_runtime_config.json` exists and is correctly configured with your MQTT broker details and desired server port. You can create this file manually based on the example above, or configure it via the UI after starting the server and frontend.

2.  **Start Backend Server:**
    *   Navigate to the project root directory.
    *   Activate your Python virtual environment (e.g., `source .venv/bin/activate`).
    *   Run the Uvicorn server:
    ```bash
    # IMPORTANT: Run WITHOUT --reload for stable MQTT and WebSocket operation.
    # Replace <your_configured_port> with the port in server_runtime_config.json (default 8022).
    uvicorn server.main:app --host 0.0.0.0 --port <your_configured_port>
    
    # Example using default port 8022:
    # uvicorn server.main:app --host 0.0.0.0 --port 8022

    # Or directly run with uv
    # uv run uvicorn server.main:app --host 0.0.0.0 --port 8022
    ```
    *   **Note on `--reload`**: Using Uvicorn\'s `--reload` flag can interfere with the Paho MQTT client\'s threading and WebSocket stability. For reliable operation, especially when using MQTT features, **run the server without `--reload`**. If you make backend code changes, a manual server restart is necessary.

3.  **Start Frontend Development Server:**
    *   Navigate to the `web/` directory.
    *   Run the Vite development server:
    ```bash
    cd web
    npm run dev
    ```
    *   Access the frontend in your browser, typically at `http://localhost:5173` (Vite will show the exact URL in the terminal).

4.  **Initial Setup via Web UI:**
    *   Open the Web Frontend in your browser (e.g., `http://localhost:5173`).
    *   Navigate to **"Tracker Mode Configuration"**:
        *   If `server_runtime_config.json` was not pre-configured, click the "Configure Server (MQTT, etc.)" button, fill in your MQTT broker details, server port, and Kalman filter parameters, then save. The server will create/update the file.
        *   Click "Import Configuration & Update Server (JSON)", select the JSON file you prepared (e.g., from the "Map & Beacon Configuration" view). This will send the configuration to the server (updating `server/web_config.json`) and also store it for this mode's display. The map and beacons should appear.
        *   The system should attempt to connect to MQTT based on the server runtime settings. Status indicators for WebSocket and MQTT will be shown.
    *   Navigate to **"Map & Beacon Configuration"**: 
        *   Here you can create a new configuration from scratch, or import a JSON file (e.g., one you previously exported or from another source), edit it in detail (manage beacons, edit map entities if that feature is developed, adjust general settings), and then "Export Configuration to Clipboard/File". This exported JSON can then be used in "Tracker Mode" or "Personal Mode".
    *   Navigate to **"Personal Mode Configuration"**: 
        *   Click "Import Master Configuration (JSON)" and select a prepared configuration file. This saves the configuration for local, in-browser positioning.
        *   Click "Start Local Positioning" to begin scanning for beacons using your device's Bluetooth (if available and supported by the browser for beacon scanning).

5.  **View Results:**
    *   **Tracker Mode:** If trackers are publishing data to the configured MQTT topic, they should appear on the live map and in the trackers list within the "Tracker Mode Configuration" view.
    *   **Personal Mode:** If local positioning is started and beacons are detected, your device's calculated position will be shown on the map in the "Personal Mode Configuration" view.

## Key Functionality & Files (for Developers)

*   **MQTT Data Parsing:** `server/main.py` (function `parse_sensecap_payload`) handles incoming SenseCAP MQTT messages. The `on_message` callback filters for `MeasurementID == "5002"`.
*   **Positioning Logic:** `server/positioning.py` contains distance calculation (RSSI to distance) and trilateration algorithms. Beacon matching relies on MAC addresses from `miniprogram_config.json`.
*   **Kalman Filter:** `server/positioning.py` (class `KalmanFilter2D`) provides 2D position smoothing.
*   **Configuration Management:** `server/config_manager.py` loads and saves the two primary JSON configuration files.
*   **State Management & WebSockets:** `server/main.py` (class `ConnectionManager` and `tracker_states` dictionary) manages tracker states and broadcasts updates via WebSockets.
*   **Frontend UI Components:**
    *   `web/src/views/MasterConfigView.vue`: "Map & Beacon Configuration" view for creating/editing/exporting full configurations.
    *   `web/src/views/PersonalModeConfigView.vue`: "Personal Mode Configuration" view for local device positioning.
    *   `web/src/views/TrackerModeConfigView.vue`: "Tracker Mode Configuration" view for server-side tracking, MQTT/server settings, and live tracker display.
    *   `web/src/components/configuration/BeaconManagerTab.vue`, `MapEditorTab.vue`, `GeneralSettingsTab.vue`: Child components used within `MasterConfigView.vue`.
    *   `web/src/components/ServerSettings.vue`: Modal for MQTT and server runtime settings.
    *   `web/src/components/MapView.vue`: Component for displaying the map and trackers (used in Tracker Mode).