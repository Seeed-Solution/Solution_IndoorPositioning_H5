# Local Beacon Service (Node.js)

This directory contains the Node.js service responsible for scanning local Bluetooth Low Energy (BLE) beacons and relaying their information via a WebSocket connection. This enables local device positioning without relying on a centralized MQTT server.

## Project Structure

-   `service.js`: The main application file. It sets up a WebSocket server, uses the `@abandonware/noble` library to scan for BLE beacons, and handles communication with connected clients (typically the web frontend).
-   `package.json`: Defines project metadata, dependencies (`@abandonware/noble`, `ws`, `express`), and npm scripts.
-   `start_service.sh`: A shell script to manage the startup of this service, potentially including environment setup or specific run commands.
-   `node_modules/`: Contains installed npm packages (dependencies).

## How to Run

There are a few ways to run this service:

1.  **Using the dedicated shell script (Recommended for typical use):**
    This script might handle specific environment configurations or operational parameters.
    ```bash
    cd /path/to/beacon_posistion_r1000/local-beacon-service
    bash ./start_service.sh
    ```
    (Note: Use `bash` explicitly if you encounter shell compatibility issues with `zsh` or others.)

2.  **Using npm (from the `local-beacon-service` directory):**
    First, ensure dependencies are installed:
    ```bash
    cd /path/to/beacon_posistion_r1000/local-beacon-service
    npm install
    ```
    Then, start the service:
    ```bash
    npm start
    ```

3.  **Directly with Node.js (from the `local-beacon-service` directory):**
    After installing dependencies as above:
    ```bash
    node service.js
    ```

The service typically listens for WebSocket connections on `ws://localhost:8081` (verify in `service.js` if different).

## How to Modify / Develop

1.  **Beacon Scanning Logic**: Modifications to how BLE beacons are detected, filtered, or processed are primarily done in `service.js`. This involves interacting with the `@abandonware/noble` API.
2.  **WebSocket Communication**: Changes to the messages sent or received via WebSocket are handled in `service.js`. This includes defining message types (`beacon`, `info`, `error`) and their payloads.
3.  **Dependencies**: If new Node.js packages are needed, add them to `package.json` using `npm install <package-name> --save`.
4.  **Configuration**: The service might have hardcoded configurations (like the WebSocket port). If these need to be dynamic, consider environment variables or a simple configuration file.

## Communication Protocol (WebSocket)

The service communicates with clients over WebSocket using JSON messages.

**Server to Client Messages:**

-   **Beacon Data:**
    ```json
    {
      "type": "beacon",
      "data": {
        "id": "<peripheral_uuid_or_mac>", // Unique identifier for the beacon device
        "rssi": -75, // Received Signal Strength Indicator
        "iBeacon": { // Present if the beacon is an iBeacon
          "uuid": "fda50693-a4e2-4fb1-afcf-c6eb07647825",
          "major": 10001,
          "minor": 19641,
          "txPowerCalibrated": -59 // Calibrated TX power at 1 meter
        },
        // Potentially other beacon type data (e.g., Eddystone)
      }
    }
    ```
-   **Status/Info Messages:**
    ```json
    {
      "type": "info",
      "message": "Scanning started."
    }
    ```
    Common messages include: "Scanning started.", "Scanning stopped.", "Bluetooth adapter powered on.", etc.

-   **Error Messages:**
    ```json
    {
      "type": "error",
      "message": "Failed to access Bluetooth adapter. Ensure it is enabled and permissions are granted."
    }
    ```

**Client to Server Messages:**

-   **Start Scan Command:**
    ```json
    {
      "command": "startScan",
      "ignoredMacAddresses": [] // Optional: array of MAC addresses to ignore
    }
    ```
-   **Stop Scan Command:**
    ```json
    {
      "command": "stopScan"
    }
    ```

## Dependencies

-   `@abandonware/noble`: For BLE communication and beacon scanning.
-   `ws`: WebSocket server implementation.
-   `express`: Though listed, its usage in `service.js` should be verified; it might be minimal or for future expansion (e.g., an HTTP health check endpoint). If not actively used for core WebSocket functionality, its role might be secondary. 