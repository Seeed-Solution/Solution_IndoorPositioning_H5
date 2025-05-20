# bleak_service README

This service uses Python with the `bleak` library to scan for Bluetooth Low Energy (BLE) beacons, specifically iBeacons.
It provides a WebSocket interface for clients (e.g., a web frontend) to start/stop scanning and receive beacon data.

## Features

-   BLE device scanning using `bleak`.
-   Parsing of iBeacon advertisement data (UUID, Major, Minor, TX Power).
-   WebSocket endpoint (`/ws/beacons`) for communication.
    -   Client can send `startScan` (optionally with `ignoredMacAddresses`) and `stopScan` commands.
    -   Service sends `beacon` messages with discovered beacon data.
    -   Service sends `info` and `error` messages.
-   Designed to be packaged with Nuitka for cross-platform distribution.

## How to Run (Development)

1.  **Ensure Python and dependencies are installed.**
    It's recommended to use a virtual environment.
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Windows: .venv\Scripts\activate
    pip install fastapi uvicorn websockets bleak pydantic
    ```

2.  **Navigate to the project root directory (where `pyproject.toml` or this service's parent is located).**

3.  **Start the Uvicorn server:**
    ```bash
    uvicorn bleak_service.main:app --host 0.0.0.0 --port 8081 --reload
    ```
    The WebSocket server will typically be accessible at `ws://localhost:8081/ws/beacons`.

## WebSocket API

**Endpoint:** `ws://<host>:<port>/ws/beacons`

**Client to Server Messages (JSON):**

-   **Start Scanning:**
    ```json
    {
      "command": "startScan",
      "ignoredMacAddresses": ["mac1_to_ignore", "mac2_to_ignore"]
    }
    ```
    (The `ignoredMacAddresses` field is optional)

-   **Stop Scanning:**
    ```json
    {
      "command": "stopScan"
    }
    ```

**Server to Client Messages (JSON):**

-   **Beacon Data:**
    ```json
    {
      "type": "beacon",
      "data": {
        "id": "peripheral_id_or_address", // From bleak (address)
        "address": "peripheral_address", // BLE address
        "rssi": -70,
        "localName": "OptionalLocalName",
        "txPowerAdv": -50, // Advertised TX Power (if available)
        "iBeacon": {
          "uuid": "FDA50693-A4E2-4FB1-AFCF-C6EB07647825",
          "major": 10001,
          "minor": 20002,
          "txPowerCalibrated": -59 // Calibrated TX power at 1m
        }
      }
    }
    ```

-   **Informational Message:**
    ```json
    {
      "type": "info",
      "message": "Scanning started."
    }
    ```

-   **Error Message:**
    ```json
    {
      "type": "error",
      "message": "Failed to start scanning."
    }
    ```

## Project Structure

-   `main.py`: FastAPI application, WebSocket endpoint, and command handling.
-   `ble_scanner.py`: Core BLE scanning logic, iBeacon parsing, and interaction with `bleak`.
-   `models.py` (optional): Pydantic models for structuring data.
-   `__init__.py`: Makes `bleak_service` a Python package. 