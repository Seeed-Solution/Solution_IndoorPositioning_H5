import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import json
import paho.mqtt.client as mqtt
import logging
import datetime
import time
from typing import List, Dict, Optional, Any

# Import project modules
from . import config_manager
from . import positioning
from .models import ConfigData, DetectedBeacon, TrackerReport, TrackerState
from .positioning import KalmanFilter2D # Import KalmanFilter

# Configure logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

app = FastAPI()

# Mount static files (for serving the client-side HTML/JS)
# Make sure the client directory exists relative to where uvicorn is run (usually project root)
try:
    app.mount("/static", StaticFiles(directory="../client"), name="static")
except RuntimeError:
    log.warning("Static files directory '../client' not found. Serving API only.")
    # If you definitely need the static files, consider making the path absolute
    # or ensuring the server is run from the correct directory.


# --- Global State ---
current_config: Optional[ConfigData] = None
tracker_states: Dict[str, TrackerState] = {} # Stores the latest state for each tracker
kalman_filters: Dict[str, KalmanFilter2D] = {} # Stores Kalman filter instance per tracker
mqtt_client: Optional[mqtt.Client] = None

# --- WebSocket Connection Manager ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        log.info(f"WebSocket client connected: {websocket.client}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        log.info(f"WebSocket client disconnected: {websocket.client}")

    async def broadcast(self, data: dict):
        # Use json.dumps to ensure proper serialization for WebSocket
        message = json.dumps(data)
        disconnected_clients = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e: # Handles various connection errors
                log.warning(f"Could not send to WebSocket client {connection.client}: {e}. Marking for disconnect.")
                disconnected_clients.append(connection)
        # Clean up disconnected clients
        for client in disconnected_clients:
            if client in self.active_connections:
                self.active_connections.remove(client) # No need to call disconnect() again

manager = ConnectionManager()

# --- MQTT Handling ---
def on_connect(client, userdata, flags, rc):
    """Callback when connected to MQTT Broker."""
    global current_config
    if rc == 0:
        log.info("Connected to MQTT Broker!")
        # Load config to get topic details
        current_config = config_manager.get_config()
        if current_config and current_config.mqtt: # Check if MQTT config exists
            # Construct topic from config.json
            topic = current_config.mqtt.topicPattern.format(ApplicationID=current_config.mqtt.applicationID)
            client.subscribe(topic)
            log.info(f"Subscribed to topic: {topic}")
        else:
            log.error("MQTT configuration missing or invalid in config.json. Cannot subscribe.")
    else:
        log.error(f"Failed to connect to MQTT broker, return code {rc}")

def parse_chirpstack_payload(payload: bytes) -> Optional[TrackerReport]:
    """
    Parses the payload assuming a ChirpStack structure based on provided example.
    Extracts tracker ID, timestamp, and BLE scan results.
    """
    try:
        data = json.loads(payload.decode())
        log.debug(f"Raw MQTT data: {data}")

        # 1. Extract Tracker ID (prefer devEui)
        device_info = data.get("deviceInfo")
        if not device_info:
            log.warning("Missing 'deviceInfo' in payload.")
            return None
        tracker_id = device_info.get("devEui")
        if not tracker_id:
            log.warning("Missing 'devEui' in 'deviceInfo'.")
            return None
        tracker_id = str(tracker_id) # Ensure string

        # 2. Extract Timestamp (from root 'time')
        timestamp_str = data.get("time")
        timestamp_ms = int(time.time() * 1000) # Default to now
        if timestamp_str:
            try:
                # Handle potential nanoseconds by truncating
                if '.' in timestamp_str:
                     ts_parts = timestamp_str.split('.')
                     timestamp_str = ts_parts[0] + '.' + ts_parts[1][:6] # Keep only microseconds
                # Replace Z with +00:00 if necessary
                dt_obj = datetime.datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                timestamp_ms = int(dt_obj.timestamp() * 1000)
            except (ValueError, TypeError) as time_err:
                log.warning(f"Could not parse root timestamp '{timestamp_str}': {time_err}. Using current time.")
        else:
            log.warning("Missing root 'time' field in payload. Using current time.")


        # 3. Extract Beacon Data
        detected_beacons = []
        payload_object = data.get('object')
        if payload_object and isinstance(payload_object, dict) and 'messages' in payload_object:
            # messages is often a list containing one list of actual message parts
            if payload_object['messages'] and isinstance(payload_object['messages'][0], list):
                for message_part in payload_object['messages'][0]:
                    if isinstance(message_part, dict) and message_part.get('type') == "BLE Scan":
                        measurement_value = message_part.get('measurementValue')
                        if isinstance(measurement_value, list):
                            for beacon_data in measurement_value:
                                if isinstance(beacon_data, dict):
                                    mac = beacon_data.get('mac') # This is our UUID
                                    rssi_str = beacon_data.get('rssi')
                                    if mac and rssi_str is not None:
                                        try:
                                            # Ensure MAC is uppercase for consistency
                                            mac_addr = str(mac).upper()
                                            rssi = int(rssi_str)
                                            # Major/Minor are not in the example, defaults to None
                                            detected = DetectedBeacon(
                                                macAddress=mac_addr,
                                                rssi=rssi
                                            )
                                            detected_beacons.append(detected)
                                        except (ValueError, TypeError) as conv_err:
                                            log.warning(f"Could not convert beacon data for {tracker_id}: {beacon_data} - {conv_err}")
                                    else:
                                        log.debug(f"Skipping beacon entry in BLE Scan due to missing mac or rssi: {beacon_data}")
                            # Found the BLE Scan, no need to check other message parts in this list
                            break 
            else:
                 log.warning(f"'object.messages[0]' is not a list for tracker {tracker_id}")
        else:
            log.warning(f"Missing 'object' or 'object.messages' in payload for tracker {tracker_id}. Cannot find beacon data.")


        # Even if no beacons found, we got the message, return report
        if not detected_beacons:
            log.info(f"No valid BLE beacons found in payload for tracker {tracker_id}")

        return TrackerReport(
            trackerId=tracker_id,
            timestamp=timestamp_ms,
            detectedBeacons=detected_beacons
        )

    except json.JSONDecodeError:
        log.error(f"Failed to decode JSON payload: {payload.decode()}")
        return None
    except Exception as e:
        log.error(f"Error processing MQTT payload for tracker {tracker_id or 'Unknown'}: {e}", exc_info=True) # Log stack trace
        return None


async def process_tracker_report(report: TrackerReport):
    """Processes a parsed tracker report to calculate position and update state."""
    global current_config, tracker_states, kalman_filters

    if not current_config:
        log.warning("Configuration not loaded, cannot process tracker report.")
        return

    tracker_id = report.trackerId
    current_time_ms = int(time.time() * 1000)
    last_state = tracker_states.get(tracker_id)
    last_known_pos = (last_state.x, last_state.y) if last_state and last_state.x is not None and last_state.y is not None else None
    dt = (current_time_ms - last_state.last_update_time) / 1000.0 if last_state else 0.1 # Time delta in seconds

    log.info(f"Processing report for tracker: {tracker_id} with {len(report.detectedBeacons)} beacons.")

    # --- Position Calculation ---
    calculated_position = positioning.calculate_position(
        detected_beacons=report.detectedBeacons,
        config=current_config,
        last_known_position=last_known_pos # Use last known for multilateration guess
    )

    # --- Kalman Filter Update ---
    filtered_position: Optional[Tuple[float, float]] = None
    kf = kalman_filters.get(tracker_id)

    if calculated_position:
        log.info(f"Calculated position for {tracker_id}: {calculated_position}")
        if kf:
            kf.predict(dt)
            kf.update(calculated_position)
        else:
            # Initialize Kalman Filter if first valid position
            kf = KalmanFilter2D(initial_pos=calculated_position,
                                 process_variance=current_config.settings.kalmanProcessVariance,
                                 measurement_variance=current_config.settings.kalmanMeasurementVariance)
            kalman_filters[tracker_id] = kf
            log.info(f"Initialized Kalman filter for {tracker_id}")

        filtered_position = kf.get_position()
        log.info(f"Filtered position for {tracker_id}: {filtered_position}")
    elif kf:
        # If no new position calculated, just predict based on last velocity
        kf.predict(dt)
        filtered_position = kf.get_position()
        log.info(f"Position prediction (no new measurement) for {tracker_id}: {filtered_position}")
        # Optional: Check if prediction makes sense (e.g., within map bounds)

    # --- Update Tracker State ---
    new_state = TrackerState(
        trackerId=tracker_id,
        x=filtered_position[0] if filtered_position else (last_state.x if last_state else None),
        y=filtered_position[1] if filtered_position else (last_state.y if last_state else None),
        last_update_time=current_time_ms, # Server time of this update
        last_known_measurement_time=report.timestamp, # Timestamp from the LoRaWAN message
        last_detected_beacons=report.detectedBeacons
    )
    tracker_states[tracker_id] = new_state

    # --- Broadcast Update ---
    # Send only the updated tracker's state or the full state?
    # Sending full state might be simpler for client
    # Sending only update is more efficient
    update_data = {tracker_id: new_state.dict()} # Send update for this tracker
    await manager.broadcast({"type": "tracker_update", "data": update_data})
    # Or: await manager.broadcast({"type": "full_state", "data": {tid: ts.dict() for tid, ts in tracker_states.items()}})


def on_message(client, userdata, msg):
    """Callback when an MQTT message is received."""
    log.info(f"Received message on topic {msg.topic}: {msg.payload[:150]}...") # Log beginning of payload

    # Run parsing and processing in an async task to avoid blocking MQTT loop?
    # For now, process directly. If it becomes slow, use asyncio.create_task
    report = parse_chirpstack_payload(msg.payload)
    if report:
        # Need to run the async processing function
        # This is tricky as on_message is not async.
        # Best practice would involve an async queue or running an event loop
        # For simplicity here, let's try running it directly if the FastAPI loop is available
        try:
            import asyncio
            asyncio.create_task(process_tracker_report(report))
        except RuntimeError: # No running event loop
             log.error("No running asyncio event loop to schedule tracker processing.")
        except Exception as e:
             log.error(f"Error scheduling tracker processing task: {e}")

    # --- Old beacon_data logic removed ---


def setup_mqtt():
    """Sets up and connects the MQTT client."""
    global mqtt_client, current_config
    if not current_config or not current_config.mqtt:
        log.error("MQTT configuration not loaded. Cannot setup MQTT client.")
        return

    mqtt_conf = current_config.mqtt
    client_id = f"beacon_position_server_{datetime.datetime.now().timestamp()}" # Unique client ID
    mqtt_client = mqtt.Client(client_id=client_id)
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message

    if mqtt_conf.username and mqtt_conf.password:
        mqtt_client.username_pw_set(mqtt_conf.username, mqtt_conf.password)
        log.info("MQTT username/password set.")

    try:
        log.info(f"Connecting to MQTT broker at {mqtt_conf.brokerHost}:{mqtt_conf.brokerPort}")
        mqtt_client.connect(mqtt_conf.brokerHost, mqtt_conf.brokerPort, 60)
        mqtt_client.loop_start() # Start network loop in background thread
    except ConnectionRefusedError:
        log.error(f"Connection refused by MQTT broker {mqtt_conf.brokerHost}:{mqtt_conf.brokerPort}.")
    except Exception as e:
        log.error(f"Could not connect to MQTT broker. Error: {e}", exc_info=True)

# --- FastAPI Event Handlers ---
@app.on_event("startup")
async def startup_event():
    """Runs on application startup."""
    global current_config
    log.info("Application startup...")
    current_config = config_manager.load_config()
    if not current_config:
        log.warning("Failed to load configuration on startup. Check config.json.")
        # Decide if the app should exit or continue without config
    else:
        log.info("Configuration loaded.")
        # Setup MQTT only if config is loaded successfully
        setup_mqtt()
    log.info("Application startup complete.")

@app.on_event("shutdown")
async def shutdown_event():
    """Runs on application shutdown."""
    global mqtt_client
    log.info("Application shutdown...")
    if mqtt_client and mqtt_client.is_connected():
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
        log.info("MQTT client disconnected.")
    log.info("Application shutdown complete.")

# --- API Endpoints ---
@app.get("/")
async def read_root():
    """Serves the main client HTML page."""
    # Ensure the path is correct relative to where the server is run
    client_html_path = "../client/index.html"
    # Check if file exists? Better handled by StaticFiles mount, but good practice.
    import os
    if os.path.exists(client_html_path):
         return FileResponse(client_html_path)
    else:
         log.error(f"Client HTML file not found at expected path: {client_html_path}")
         # Return a simple message or raise 404
         # raise HTTPException(status_code=404, detail="Client frontend not found")
         return {"message": "Backend running. Client frontend not found."}


@app.get("/api/config")
async def get_api_config():
    """Returns the current backend configuration."""
    if current_config:
        return current_config
    else:
        # Maybe try reloading? Or just return error.
        raise HTTPException(status_code=503, detail="Configuration not loaded")

@app.get("/api/trackers")
async def get_trackers():
    """Returns the current state of all known trackers."""
    return tracker_states

# --- WebSocket Endpoint ---
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Handles WebSocket connections."""
    await manager.connect(websocket)
    try:
        # Send initial state upon connection?
        initial_state = {tid: ts.dict() for tid, ts in tracker_states.items()}
        await websocket.send_json({"type": "initial_state", "data": initial_state})

        while True:
            # Keep connection alive, wait for messages (though we mostly broadcast)
            # You could add handling for client->server messages here if needed
            data = await websocket.receive_text()
            log.debug(f"Received message from WebSocket client {websocket.client}: {data}")
            # Example: client could request resync
            if data == "request_sync":
                 full_state = {tid: ts.dict() for tid, ts in tracker_states.items()}
                 await websocket.send_json({"type": "full_state", "data": full_state})

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        log.error(f"WebSocket error for client {websocket.client}: {e}", exc_info=True)
        manager.disconnect(websocket) # Ensure disconnect on error

# --- Main Execution ---
if __name__ == "__main__":
    # Load config sync first for host/port
    temp_config = config_manager.load_config()
    server_port = 8000 # Default
    if temp_config and temp_config.server and temp_config.server.port:
        server_port = temp_config.server.port

    log.info(f"Starting Uvicorn server on host 0.0.0.0 port {server_port}")
    uvicorn.run(app, host="0.0.0.0", port=server_port) 