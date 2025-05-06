# Beacon Positioning - Backend Server

This FastAPI server receives tracker reports containing detected iBeacon RSSI values, calculates the tracker's position based on a provided configuration file, and broadcasts updates via WebSockets to connected clients.

## Setup

1.  **Navigate to Server Directory:**
    ```bash
    cd server
    ```
2.  **Create Virtual Environment (Recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # Linux/macOS
    # or
    # venv\Scripts\activate  # Windows
    ```
3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Running the Server

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

*   `--reload`: Automatically restarts the server on code changes (for development).
*   `--host 0.0.0.0`: Makes the server accessible on your network.
*   `--port 8000`: Specifies the port number.

The server will be running at `http://localhost:8000` (or your machine's IP address on port 8000).

## API Endpoints

*   `GET /api/config`: Retrieves the currently loaded configuration.
*   `POST /api/config`: Upload a `config.json` file (multipart/form-data) to load map and beacon settings.
*   `POST /api/tracker/report`: Endpoint where trackers (or a simulator) should send their detected beacon data (JSON payload matching `TrackerReport` model).
*   `WS /ws`: WebSocket endpoint for clients to connect and receive real-time updates (`config_update`, `initial_state`, `tracker_update`).

## Configuration (`config.json`)

The server requires a `config.json` file in the `server/` directory (or uploaded via the API) with the following structure:

```json
{
  "mapInfo": {
    "width": 20.5,         // Map width in meters
    "height": 15.0,        // Map height in meters
    "entities": [          // List of map entities (e.g., walls)
      {
        "type": "polyline",
        "points": [[0,0], [20.5,0], [20.5,15.0], [0,15.0], [0,0]],
        "closed": true,
        "color": "#333333",
        "lineWidth": 1.5
      }
      // ... more entities
    ]
  },
  "beacons": [             // List of configured iBeacons
    {
      "uuid": "FDA50693-A4E2-4FB1-AFCF-C6EB07647825",
      "major": 100,
      "minor": 1,
      "name": "BeaconNearDoor", // Optional name
      "txPower": -59,        // RSSI at 1 meter (integer)
      "x": 2.5,              // X coordinate in meters
      "y": 14.0             // Y coordinate in meters
    }
    // ... more beacons
  ],
  "settings": {            // General settings
    "signalPropagationFactor": 2.8 // Environment factor (n)
  }
}
```

This file can be generated and exported from the companion Weixin Mini Program. 