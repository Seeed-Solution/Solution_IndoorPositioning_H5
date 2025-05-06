# Multi-Tracker Beacon Positioning System

This project provides a system for tracking multiple devices (trackers) indoors using iBeacon signals and visualizing their positions on a web-based map.

## Overview

The system consists of three main components:

1.  **Backend Server (`server/`)**:
    *   Built with Python and FastAPI.
    *   Receives tracker reports containing detected iBeacon signals via an HTTP API endpoint.
    *   Loads map and beacon configuration from a `config.json` file.
    *   Calculates the position of each tracker based on received signal strengths (RSSI) and configured beacon locations using trilateration.
    *   Manages the state of tracked devices (rolling 1-hour window in memory).
    *   Broadcasts tracker position updates and configuration changes to connected frontend clients via WebSockets.
    *   Serves the compiled frontend application (optional).

2.  **Web Frontend (`web/`)**:
    *   Built with Vue 3 and Vite.
    *   Connects to the backend server via WebSockets.
    *   Provides an interface to upload the `config.json` file to the backend.
    *   Displays the configured map layout and beacon locations using HTML Canvas.
    *   Visualizes the real-time positions of tracked devices on the map.
    *   Lists currently tracked devices and their status.

3.  **Miniprogram Configuration Tool (`miniprogram/`)**:
    *   A Weixin Mini Program designed to run on a mobile device.
    *   Allows users to:
        *   Upload a map layout file (`.json`).
        *   Scan for nearby iBeacons using Bluetooth.
        *   Manually add or edit iBeacon configurations (UUID, Major, Minor, TxPower).
        *   Place configured beacons onto the uploaded map by clicking.
        *   Configure the signal propagation factor (n) for distance calculation.
    *   Provides a button to export the complete map and beacon configuration as a JSON string to the clipboard, ready to be saved as `config.json` for the backend server.

## Architecture & Data Flow

```
+-------------------------+      +------------------------+      +-----------------+
| Tracker Device          | ---> | LoRaWAN Network Server | ---> | Backend Server  |
| (Sends Beacon Scans via |      | (Decodes Payload)      |      | (FastAPI)       |-----> WebSocket
| LoRaWAN)                |      +------------------------+      | - Receives Reports  |
+-------------------------+                                      | - Calculates Pos    |<---+ 
                                                                 | - Manages State     |
                                                                 | - Serves Config/API |
                                                                 +---------|---------+
                                                                           | (HTTP API)
       +-----------------------+      +------------------------+           | (Upload Config)
       | Weixin Mini Program   | ---> | User copies JSON to    | --------->|
       | (Configuration Tool)  |      | file (`config.json`)   |           |
       | - Configure Map       |      +------------------------+           |
       | - Configure Beacons   |                                           |
       | - Export Config JSON  |                                           |
       +-----------------------+                                           |
                                                                           V
                                                                 +-----------------+
                                                                 | Web Frontend    |
                                                                 | (Vue 3)         |
                                                                 | - Uploads Config|
                                                                 | - Displays Map  |
                                                                 | - Shows Trackers|
                                                                 +-----------------+
```

1.  **Configuration:** Use the Mini Program tool to define the map layout and beacon locations. Export the configuration JSON.
2.  **Upload Config:** Upload the exported `config.json` to the Backend Server via the Web Frontend.
3.  **Tracker Reports:** Trackers scan for Beacons and send reports (UUID, Major, Minor, RSSI) via LoRaWAN (or other means) to the Backend Server's `/api/tracker/report` endpoint. *(Note: The LoRaWAN decoding part is assumed to happen before the data reaches this backend)*.
4.  **Position Calculation:** The Backend calculates the tracker's position using the report data and the loaded configuration.
5.  **Visualization:** The Backend broadcasts position updates via WebSocket to the Web Frontend, which displays the trackers on the map.

## Setup

**Prerequisites:**

*   **Node.js:** Latest LTS version recommended (for Vue frontend).
*   **npm:** Comes with Node.js.
*   **Python:** 3.8+ recommended (for FastAPI backend).
*   **pip:** Comes with Python.
*   **Weixin DevTools:** For running and debugging the Mini Program configuration tool.

**1. Backend Server Setup:**

```bash
# Navigate to the server directory
cd server

# Create and activate a virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or: venv\Scripts\activate # Windows

# Install Python dependencies
pip install -r requirements.txt

# Note: The server needs a valid `config.json`. Either place one manually
# in the `server/` directory or upload it via the web frontend later.
# An empty placeholder {} exists initially.
```

**2. Web Frontend Setup:**

```bash
# Navigate to the web directory
cd web

# Install Node.js dependencies
npm install
```

**3. Miniprogram Tool Setup:**

*   Open Weixin DevTools.
*   Import Project -> Select the `miniprogram/` directory within your project folder.
*   Fill in your AppID if necessary.
*   The DevTools should recognize it as a Mini Program project.

## Running the System

1.  **Start Backend Server:**
    ```bash
    cd server
    # Activate virtual env if not already active
    # source venv/bin/activate
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
    ```
    The backend API will be available at `http://localhost:8000`.

2.  **Start Frontend Dev Server:**
    ```bash
    cd web
    npm run dev
    ```
    The frontend will likely be available at `http://localhost:5173` (check terminal output).

3.  **Configure via Mini Program:**
    *   Run the Mini Program in Weixin DevTools or on a device.
    *   Navigate to the "配置" (Config) tab.
    *   Use the "地图配置" (Map Config) and "Beacon配置" (Beacon Config) sections to set up your environment.
    *   Go to "通用设置" (Common Settings), optionally adjust the signal factor, and click "导出配置到剪贴板" (Export Config to Clipboard).

4.  **Upload Configuration to Backend:**
    *   Paste the copied JSON data from the clipboard into a new text file.
    *   Save this file as `config.json`.
    *   Open the Web Frontend (e.g., `http://localhost:5173`) in your browser.
    *   Use the "Choose File" button to select your `config.json`.
    *   Click "Upload Config". The map and beacons should appear.

5.  **Send Tracker Data:**
    *   Trackers need to send POST requests to `http://<your_backend_ip>:8000/api/tracker/report`.
    *   The request body must be JSON matching the `TrackerReport` model (see `server/models.py`).
    *   **Example using `curl`:**
        ```bash
        curl -X POST http://localhost:8000/api/tracker/report \
        -H "Content-Type: application/json" \
        -d '{
              "trackerId": "tracker_sim_01",
              "timestamp": '$(date +%s000)',
              "detectedBeacons": [
                { "uuid": "FDA50693-A4E2-4FB1-AFCF-C6EB07647825", "major": 100, "minor": 1, "rssi": -65 },
                { "uuid": "FDA50693-A4E2-4FB1-AFCF-C6EB07647825", "major": 100, "minor": 2, "rssi": -72 },
                { "uuid": "FDA50693-A4E2-4FB1-AFCF-C6EB07647825", "major": 100, "minor": 3, "rssi": -68 }
              ]
            }'
        ```
        *(Replace beacon details with your actual configured beacons and observed RSSI values)*

6.  **View Results:** Observe the tracker icons appearing and moving on the map in the Web Frontend.

## Key Files & Configuration

*   **`server/config.json`**: Defines the map layout and beacon positions. Essential for backend operation.
*   **`server/models.py`**: Defines Pydantic models for API data (`ConfigData`, `TrackerReport`, `TrackerState`). Check `TrackerReport` for the expected input format.
*   **`server/positioning.py`**: Contains the core distance calculation and trilateration logic.
*   **`miniprogram/pages/config/config.js`**: Contains the `exportConfig` function responsible for generating the `config.json` output.
*   **`web/src/App.vue`**: Main component for the frontend UI, WebSocket handling, and map interaction.
*   **`web/src/components/MapView.vue`**: Component responsible for rendering the map canvas.

## Further Development

*   **LoRaWAN Payload Parsing:** Adapt the `/api/tracker/report` endpoint in `server/main.py` to parse the actual data format received from your LoRaWAN Network Server.
*   **Positioning Algorithm:** Replace the basic trilateration in `server/positioning.py` with a more robust multilateration algorithm (e.g., Least Squares) for improved accuracy, especially with >3 beacons.
*   **Kalman Filter:** Re-integrate a Kalman filter (or similar) in the backend (`server/positioning.py`, `server/state.py`) to smooth tracker movements.
*   **Error Handling:** Enhance error handling and reporting in both backend and frontend.
*   **Deployment:** Adapt backend (e.g., using Gunicorn) and frontend (build static files) for production deployment. 