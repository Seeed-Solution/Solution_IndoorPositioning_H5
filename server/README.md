# Backend Server (Python FastAPI)

This directory contains the Python FastAPI backend server for the Indoor Positioning System.

## Project Structure

-   `main.py`: The main FastAPI application file. Contains API endpoint definitions, request handling, and core server logic.
-   `models.py`: Defines Pydantic models used for request/response data validation and serialization. Key models include `MasterConfig`, `MqttServerConfig`, `TrackerData`, etc.
-   `config_manager.py`: Handles loading, saving, and managing various server configurations (e.g., `server_runtime_config.json`, `web_config.json`).
-   `state.py`: Manages the runtime state of the server, such as connected trackers, MQTT client status, and cached configurations.
-   `positioning.py`: Contains algorithms and logic related to position calculation (if any server-side positioning is performed, or for utility functions).
-   `server_runtime_config.json`: Stores runtime configurations for the server, often related to MQTT, master beacon lists, etc. Can be modified via API endpoints.
-   `web_config.json`: Configuration specific to the web frontend's needs, served via an API.
-   `miniprogram_config.json`: Configuration specific to a WeChat miniprogram (if used), served via an API.
-   `requirements.txt`: Lists Python package dependencies (though dependencies are managed by `pyproject.toml` at the root for editable installs).
-   `__init__.py`: Makes the `server` directory a Python package.

## How to Run

The server is typically started as part of the main `start.sh` script in the project root. However, for standalone development:

1.  **Navigate to the project root directory:**
    ```bash
    cd /path/to/beacon_posistion_r1000
    ```
2.  **Ensure Python virtual environment is set up and activated:**
    If not already done by `start.sh`:
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```
3.  **Install dependencies:**
    The project uses an editable install with `pip install -e .` from the root, which installs dependencies listed in `pyproject.toml`. If you only need to run the server and dependencies are already installed in the `.venv`:
    ```bash
    pip install -r server/requirements.txt # May be a subset, pyproject.toml is source of truth
    ```
    It's generally recommended to use the root `pip install -e .` after activating the venv.

4.  **Start the Uvicorn server:**
    From the project root directory:
    ```bash
    uvicorn server.main:app --host 0.0.0.0 --port 8022 --reload
    ```
    The server will typically be accessible at `http://localhost:8022`.

## How to Modify / Develop

1.  **Endpoints**: New API endpoints are added in `main.py`. Follow FastAPI conventions for path operations (e.g., `@app.get("/path")`, `@app.post("/path")`).
2.  **Data Models**: Define or modify Pydantic models in `models.py` for request and response bodies. This ensures data validation and clear API contracts.
3.  **Configuration**:
    -   To add new server-side settings that need to be persisted, consider adding them to `server_runtime_config.json` and update `config_manager.py` and relevant Pydantic models.
    -   Frontend-specific configurations that the server provides should go into `web_config.json`.
4.  **State Management**: If you need to track new runtime information (e.g., status of a new service component), update `state.py`.
5.  **Business Logic**: Implement new features or modify existing logic within `main.py` or by creating new modules and importing them. For example, complex calculations related to positioning might be in `positioning.py`.

## Key Data Structures

-   **`MasterConfig` (`models.py`)**: Represents the overall configuration including map details, beacon definitions, and general settings.
    ```json
    // Example structure (refer to models.py for exact fields)
    {
      "map": { "name": "Floor Plan 1", "image": "data:image/png;base64,...", "width": 1000, "height": 800, "origin": {"x":0,"y":0}, "ppm": 10, "entities":[] },
      "beacons": [ { "deviceId": "beacon1", "uuid": "...", "major":1, "minor":1, "x":10,"y":20,"txPower":-59, "name":"B1" } ],
      "settings": { "showTrackerId": true }
    }
    ```
-   **`MqttServerConfig` (`models.py`)**: Defines parameters for connecting to an MQTT broker if the server acts as an MQTT client.
    ```json
    // Example structure
    {
      "host": "mqtt.example.com",
      "port": 1883,
      "username": "user",
      "password": "password", // Will be masked when sent to client
      "topic_pattern": "trackers/+/position",
      "enabled": true,
      "live_mqtt_status": "connected" // Dynamically added
    }
    ```
-   **`TrackerData` (`models.py`)**: Represents the data received for a single tracker, typically via MQTT or HTTP.
    ```json
    // Example structure
    {
      "trackerId": "tracker01",
      "x": 12.34,
      "y": 56.78,
      "timestamp": 1678886400000,
      "accuracy": 0.5,
      "zone": "Zone A"
    }
    ```

## API Endpoints

Refer to the FastAPI documentation generated at `/docs` (e.g., `http://localhost:8022/docs`) when the server is running for a live, interactive API specification.

Key conceptual endpoints include:
-   `/api/master-config`: GET/POST for the main map and beacon configuration.
-   `/api/server-runtime-config`: GET/POST for MQTT server settings and other runtime states.
-   `/api/trackers`: GET for current tracker data.
-   `/api/ws/trackers`: WebSocket endpoint for real-time tracker updates.
-   `/api/default-test-config`: GET to retrieve a default test configuration.
-   `/api/map-example-format`: GET to retrieve an example map format. 