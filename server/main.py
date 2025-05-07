import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import json
import paho.mqtt.client as mqtt
import logging
import datetime
import time
from typing import List, Dict, Optional, Any, Tuple

# Import project modules
from . import config_manager
from . import positioning
from .models import DetectedBeacon, TrackerReport, TrackerState, MiniprogramConfig # Added MiniprogramConfig for type hint
from .positioning import KalmanFilter2D # Import KalmanFilter

# Configure logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# Add asyncio import if not already present globally, for create_task
import asyncio

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
# Replace single current_config with two separate config holders
miniprogram_cfg: Optional[MiniprogramConfig] = None
runtime_cfg: Optional[config_manager.ServerRuntimeConfig] = None # Use qualified name to avoid circular import if ServerRuntimeConfig is also defined here
main_event_loop: Optional[asyncio.AbstractEventLoop] = None # Added for thread-safe coroutine scheduling

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
    global runtime_cfg # Use runtime_cfg for MQTT details
    if rc == 0:
        log.info("Connected to MQTT Broker!")
        if runtime_cfg and runtime_cfg.mqtt and runtime_cfg.mqtt.topicPattern and runtime_cfg.mqtt.applicationID:
            try:
                topic = runtime_cfg.mqtt.topicPattern.format(ApplicationID=runtime_cfg.mqtt.applicationID)
                client.subscribe(topic)
                log.info(f"Subscribed to topic: {topic}")
            except KeyError as e:
                log.error(f"Error formatting MQTT topicPattern. Ensure 'ApplicationID' is a valid key: {e}")
            except Exception as e:
                log.error(f"Error during MQTT subscription: {e}")
        else:
            log.error("MQTT configuration (topicPattern or applicationID) missing in runtime_cfg. Cannot subscribe.")
    else:
        log.error(f"Failed to connect to MQTT broker, return code {rc}")

def parse_sensecap_payload(device_eui: str, payload_bytes: bytes) -> Optional[TrackerReport]:
    """
    Parses the SenseCAP-like payload (JSON string) for beacon data.
    Assumes topic provides DeviceEUI, and payload contains timestamp and beacon list.
    Payload example: {"value":[{"mac":"C3:00:00:3E:7D:DA","rssi":"-53"}, ...],"timestamp":1746522494000}
    """
    try:
        data = json.loads(payload_bytes.decode('utf-8'))
        log.debug(f"Raw SenseCAP MQTT data for {device_eui}: {data}")

        payload_timestamp = data.get("timestamp")
        if payload_timestamp is None:
            log.warning(f"Missing 'timestamp' in SenseCAP payload for {device_eui}. Using current time.")
            payload_timestamp = int(time.time() * 1000)
        else:
            try:
                payload_timestamp = int(payload_timestamp)
            except ValueError:
                log.warning(f"Invalid 'timestamp' format in SenseCAP payload for {device_eui}. Using current time.")
                payload_timestamp = int(time.time() * 1000)

        beacon_values = data.get("value")
        if not isinstance(beacon_values, list):
            log.warning(f"Missing or invalid 'value' list in SenseCAP payload for {device_eui}. No beacons to parse.")
            # Still create a report if we have a timestamp and device_eui, but with empty beacons.
            # This allows the system to know the tracker is alive.
            return TrackerReport(trackerId=device_eui, timestamp=payload_timestamp, detectedBeacons=[])

        detected_beacons_list = []
        for beacon_data in beacon_values:
            if not isinstance(beacon_data, dict):
                log.debug(f"Skipping non-dict item in 'value' list for {device_eui}: {beacon_data}")
                continue

            mac_address = beacon_data.get("mac")
            rssi_str = beacon_data.get("rssi")

            if mac_address and rssi_str is not None:
                try:
                    # Ensure MAC is uppercase for consistency
                    mac_addr_upper = str(mac_address).upper()
                    rssi_val = int(rssi_str)
                    
                    detected = DetectedBeacon(
                        macAddress=mac_addr_upper,
                        rssi=rssi_val
                        # major and minor will be None by default from Pydantic model
                    )
                    detected_beacons_list.append(detected)
                except (ValueError, TypeError) as conv_err:
                    log.warning(f"Could not convert beacon data for {device_eui}: {beacon_data} - {conv_err}")
            else:
                log.debug(f"Skipping beacon entry for {device_eui} due to missing mac or rssi: {beacon_data}")
        
        if not detected_beacons_list:
            log.info(f"No valid beacons found in SenseCAP payload for tracker {device_eui} after parsing 'value' list.")

        return TrackerReport(
            trackerId=device_eui,
            timestamp=payload_timestamp,
            detectedBeacons=detected_beacons_list
        )

    except json.JSONDecodeError:
        log.error(f"Failed to decode JSON payload for {device_eui}: {payload_bytes.decode('utf-8', errors='ignore')}")
        return None
    except Exception as e:
        # Log device_eui if available, otherwise indicate unknown
        log.error(f"Error processing SenseCAP MQTT payload for tracker '{device_eui}': {e}", exc_info=True)
        return None

# This is the new on_message callback
def on_message(client, userdata, msg):
    """Callback for when a PUBLISH message is received from the server."""
    global main_event_loop # Access the main event loop

    log.info(f"MQTT Message Received: Topic: {msg.topic}")
    topic_parts = msg.topic.split('/')
    if not msg.topic.startswith('/device_sensor_data/') or len(topic_parts) < 7:
        log.warning(f"Received message on unexpected or incomplete topic structure: {msg.topic}")
        return

    device_eui = topic_parts[3]
    measurement_id = topic_parts[6]

    if measurement_id != "5002":
        log.debug(f"Ignoring message for tracker {device_eui}, MeasurementID is '{measurement_id}', not '5002'.")
        return

    log.info(f"Processing beacon data for tracker {device_eui} (MeasurementID: {measurement_id})")
    report = parse_sensecap_payload(device_eui, msg.payload)

    if report:
        if main_event_loop and main_event_loop.is_running():
            asyncio.run_coroutine_threadsafe(process_tracker_report(report), main_event_loop)
        else:
            log.error("Main asyncio event loop not available or not running. Cannot schedule tracker report processing.")
    else:
        log.warning(f"Failed to parse payload or no report generated for tracker {device_eui} from topic {msg.topic}")


async def process_tracker_report(report: TrackerReport):
    """Processes a parsed tracker report to calculate position and update state."""
    # Use new global config variables
    global miniprogram_cfg, runtime_cfg, tracker_states, kalman_filters

    if not miniprogram_cfg or not miniprogram_cfg.beacons:
        log.warning("Miniprogram configuration (beacons) not loaded, cannot process tracker report.")
        return
    if not runtime_cfg:
        log.warning("Server runtime configuration not loaded, cannot process tracker report for Kalman params.")
        return

    tracker_id = report.trackerId
    current_time_ms = int(time.time() * 1000)
    last_state = tracker_states.get(tracker_id)
    last_known_pos = (last_state.x, last_state.y) if last_state and last_state.x is not None and last_state.y is not None else None
    dt = (current_time_ms - last_state.last_update_time) / 1000.0 if last_state else 0.1

    log.info(f"Processing report for {tracker_id} with {len(report.detectedBeacons)} beacons.")

    calculated_position = positioning.calculate_position(
        detected_beacons=report.detectedBeacons,
        miniprogram_config=miniprogram_cfg, # Pass the whole miniprogram_cfg
        # signal_propagation_factor is inside miniprogram_cfg.settings
    )

    filtered_position: Optional[Tuple[float, float]] = None
    kf = kalman_filters.get(tracker_id)

    if calculated_position:
        log.info(f"Calculated position for {tracker_id}: {calculated_position}")
        if kf:
            kf.predict(dt)
            kf.update(calculated_position)
        else:
            kf = KalmanFilter2D(
                initial_pos=calculated_position,
                process_variance=runtime_cfg.kalman.processVariance,
                measurement_variance=runtime_cfg.kalman.measurementVariance
            )
            kalman_filters[tracker_id] = kf
            log.info(f"Initialized Kalman filter for {tracker_id} with PV:{runtime_cfg.kalman.processVariance}, MV:{runtime_cfg.kalman.measurementVariance}")
        
        filtered_position = kf.get_position()
        log.info(f"Filtered position for {tracker_id}: {filtered_position}")
    elif kf:
        kf.predict(dt)
        filtered_position = kf.get_position()
        log.info(f"Position prediction (no new measurement) for {tracker_id}: {filtered_position}")

    new_state = TrackerState(
        trackerId=tracker_id,
        x=filtered_position[0] if filtered_position else (last_state.x if last_state else None),
        y=filtered_position[1] if filtered_position else (last_state.y if last_state else None),
        last_update_time=current_time_ms,
        last_known_measurement_time=report.timestamp,
        last_detected_beacons=report.detectedBeacons
    )
    tracker_states[tracker_id] = new_state

    update_data = {tracker_id: new_state.model_dump()} # Use model_dump for Pydantic v2+
    await manager.broadcast({"type": "tracker_update", "data": update_data})

def setup_mqtt():
    """Initializes and connects the MQTT client using runtime_cfg."""
    global mqtt_client, runtime_cfg 

    if not runtime_cfg or not runtime_cfg.mqtt or not runtime_cfg.mqtt.enabled:
        log.info("MQTT is not configured or not enabled in runtime_cfg. Skipping MQTT setup.")
        return
    
    mqtt_cfg = runtime_cfg.mqtt
    if not mqtt_cfg.brokerHost:
        log.warning("MQTT brokerHost not configured in runtime_cfg. Skipping MQTT setup.")
        return

    try:
        client_id_to_use = mqtt_cfg.clientID # From model, handles AliasChoices
        if client_id_to_use:
            log.info(f"Using MQTT ClientID: {client_id_to_use}")
            mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id=client_id_to_use)
        else:
            log.info("MQTT ClientID not configured, Paho will generate one.")
            mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)

        if mqtt_cfg.username and mqtt_cfg.password:
            mqtt_client.username_pw_set(mqtt_cfg.username, mqtt_cfg.password)
            log.info(f"MQTT using username: {mqtt_cfg.username}")
        
        mqtt_client.on_connect = on_connect
        mqtt_client.on_message = on_message

        mqtt_client.connect(mqtt_cfg.brokerHost, mqtt_cfg.brokerPort, 60)
        mqtt_client.loop_start()
        log.info(f"MQTT client connecting to {mqtt_cfg.brokerHost}:{mqtt_cfg.brokerPort}...")
    except Exception as e:
        log.error(f"Error setting up MQTT client: {e}", exc_info=True)
        mqtt_client = None

# --- FastAPI Event Handlers ---
@app.on_event("startup")
async def startup_event():
    """Runs on application startup. Loads both configurations and sets up MQTT."""
    global miniprogram_cfg, runtime_cfg, main_event_loop
    
    # Capture the running event loop for thread-safe calls from MQTT callback
    main_event_loop = asyncio.get_running_loop()
    
    log.info("Application startup: Loading configurations...")
    
    # Load configurations using the config_manager (which caches them)
    miniprogram_cfg = config_manager.get_miniprogram_config()
    runtime_cfg = config_manager.get_server_runtime_config()

    if not miniprogram_cfg:
        log.warning("Miniprogram configuration could not be loaded. Features depending on map/beacons may fail.")
    if not runtime_cfg:
        log.error("Server runtime configuration could not be loaded. MQTT and server settings might be missing. Critical error.")
        # Potentially exit or prevent MQTT setup if runtime_cfg is vital
    else:
        # Setup MQTT if enabled in the loaded runtime_cfg
        if runtime_cfg.mqtt and runtime_cfg.mqtt.enabled and runtime_cfg.mqtt.brokerHost:
            log.info("Proceeding with MQTT setup based on runtime configuration.")
            setup_mqtt()
        elif runtime_cfg.mqtt and not runtime_cfg.mqtt.enabled:
            log.info("MQTT client is disabled in server_runtime_config.json.")
        else:
            log.warning("MQTT brokerHost not configured or MQTT config section missing in server_runtime_config.json. Skipping MQTT setup.")
            
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

@app.post("/api/config/upload", status_code=200)
async def upload_miniprogram_config(config_content: MiniprogramConfig, response: Response):
    """Receives miniprogram config JSON, saves it, and reloads.
       The request body should be the JSON content matching MiniprogramConfig model.
    """
    global miniprogram_cfg
    log.info("Received request to upload miniprogram configuration.")
    try:
        # config_content is already parsed by FastAPI into MiniprogramConfig model
        if config_manager.save_miniprogram_config(config_content):
            miniprogram_cfg = config_manager.get_miniprogram_config() # Reload and update global cache
            log.info("Miniprogram configuration uploaded and reloaded successfully.")
            # Broadcast update to WebSocket clients
            await manager.broadcast({"type": "config_update", "data": miniprogram_cfg.model_dump() if miniprogram_cfg else {}})
            return {"message": "Miniprogram configuration uploaded successfully."}
        else:
            raise HTTPException(status_code=500, detail="Failed to save miniprogram configuration.")
    except Exception as e: # Catch any other unexpected errors
        log.error(f"Error processing uploaded miniprogram config: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"Invalid configuration data: {e}")

@app.get("/api/config", response_model=Optional[MiniprogramConfig])
async def get_api_miniprogram_config():
    """Returns the current miniprogram-specific configuration (map, beacons, basic settings)."""
    global miniprogram_cfg
    if miniprogram_cfg:
        return miniprogram_cfg
    else:
        # Consider if 503 is right, or if it should return an empty object or 404
        # depending on whether a missing config is a server error or resource not found.
        log.warning("/api/config called but miniprogram_cfg is not loaded.")
        raise HTTPException(status_code=503, detail="Miniprogram configuration not loaded.")

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
        initial_state = {tid: ts.model_dump() for tid, ts in tracker_states.items()}
        await websocket.send_json({"type": "initial_state", "data": initial_state})

        while True:
            # Keep connection alive, wait for messages (though we mostly broadcast)
            # You could add handling for client->server messages here if needed
            data = await websocket.receive_text()
            log.debug(f"Received message from WebSocket client {websocket.client}: {data}")
            # Example: client could request resync
            if data == "request_sync":
                 full_state = {tid: ts.model_dump() for tid, ts in tracker_states.items()}
                 await websocket.send_json({"type": "full_state", "data": full_state})

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        log.error(f"WebSocket error for client {websocket.client}: {e}", exc_info=True)
        manager.disconnect(websocket) # Ensure disconnect on error

# --- Main Execution ---
if __name__ == "__main__":
    # Load runtime config first for server port
    # config_manager loads both on import, so we can get it directly.
    rt_cfg = config_manager.get_server_runtime_config()
    server_port = 8000 # Default
    if rt_cfg and rt_cfg.server and rt_cfg.server.port:
        server_port = rt_cfg.server.port
    else:
        log.warning(f"Could not load server port from runtime config. Using default {server_port}.")
        # Fallback if server_runtime_config.json is missing or malformed for port.

    log.info(f"Starting Uvicorn server on host 0.0.0.0 port {server_port}")
    # Uvicorn should be run from project root: uvicorn server.main:app --reload
    uvicorn.run(app, host="0.0.0.0", port=server_port) 