import pydantic

if __name__ == "__main__":
    import sys
    import os

    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, '..'))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Response, Query
from pydantic import BaseModel
from typing import List, Optional
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
import json
import paho.mqtt.client as mqtt
import logging
import datetime
import time
from typing import List, Dict, Optional, Any, Tuple
import os # Keep one os import
import random
from server.components.beacon_holder import beacon_holder
from server.dao.device_alarm_record_dao import alarm_record_dao
from server.components.uplink_collector import UplinkCollector
# from server.clients.paas_client import get_sensecap_client, initialize_sensecap_client

# Import project modules
# from . import config_manager
# from . import positioning
# from .models import ( # Grouped imports for models
#     DetectedBeacon, TrackerReport, TrackerState,
#     MiniprogramConfig, WebUIConfig,
#     WebUISettings # Import WebUISettings directly
# )
# from .positioning import KalmanFilter2D


# Import project modules
from server import config_manager
from server import positioning
from server.models import ( # Grouped imports for models
    DetectedBeacon, TrackerReport, TrackerState, WebUIBeaconConfig,
    MiniprogramConfig, WebUIConfig, DashboardConfig,
    WebUISettings # Import WebUISettings directly
)
from server.positioning import KalmanFilter2D


# Configure logging
logging.basicConfig(level=logging.INFO) # Keep level INFO for now, but will reduce specific log.info calls
log = logging.getLogger(__name__)

# Add asyncio import if not already present globally, for create_task
import asyncio

app = FastAPI()

# Define the path for the web configuration file
WEB_CONFIG_FILE_PATH = os.path.join(os.path.dirname(__file__), "web_config.json")
DASHBOARD_CONFIG_FILE_PATH = os.path.join(os.path.dirname(__file__), "dashboard_config.json")

# Path to the default test configuration file
# Assuming 'test/config2.json' is relative to the project root where server/main.py might be, or a sibling to 'server' directory.
# Adjust the path as per your actual project structure.
# If main.py is in server/, and test/ is a sibling of server/, then ../test/config2.json
DEFAULT_TEST_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "test", "config2.json")
MAP_EXAMPLE_FORMAT_PATH = os.path.join(os.path.dirname(__file__), "..", "test", "map1.json") # New path for map1.json

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
web_ui_cfg: Optional[WebUIConfig] = None # Added for web UI config
dashboard_cfg: Optional[DashboardConfig] = None
runtime_cfg: Optional[config_manager.ServerRuntimeConfig] = None # Use qualified name to avoid circular import if ServerRuntimeConfig is also defined here
main_event_loop: Optional[asyncio.AbstractEventLoop] = None # Added for thread-safe coroutine scheduling
mqtt_connection_status: str = "disconnected" # Added for live MQTT status
is_mqtt_intentionally_disconnected: bool = False # Flag for manual disconnects

tracker_states: Dict[str, TrackerState] = {} # Stores the latest state for each tracker
kalman_filters: Dict[str, KalmanFilter2D] = {} # Stores Kalman filter instance per tracker
mqtt_client: Optional[mqtt.Client] = None
beacon_map: Dict[str, WebUIBeaconConfig] = {}

allow_tracker_list: list[str] = []

# Request models for API endpoints
class TrackerListUpdateRequest(BaseModel):
    tracker_list: List[str] = []

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
## 广播当前 mqtt 状态
async def broadcast_mqtt_status():
    """Helper to broadcast the current MQTT status via WebSocket."""
    global mqtt_connection_status, main_event_loop, manager
    if main_event_loop and main_event_loop.is_running():
        # log.info(f"Broadcasting MQTT status: {mqtt_connection_status}") # Reduced verbosity
        asyncio.run_coroutine_threadsafe(
            manager.broadcast({"type": "mqtt_status_update", "data": {"status": mqtt_connection_status}}),
            main_event_loop
        )
    else:
        log.warning("Cannot broadcast MQTT status: Main event loop not available or not running.")


## mqtt client 连接配置文件中的 broker成功后, 并按要求订阅 topic
def on_connect(client, userdata, flags, rc):
    """Callback when connected to MQTT Broker."""
    global runtime_cfg, mqtt_connection_status, is_mqtt_intentionally_disconnected, main_event_loop
    if rc == 0:
        log.info("MQTT Broker: Connected!") 
        mqtt_connection_status = "connected"
        is_mqtt_intentionally_disconnected = False # Clear flag on successful connect
        # RESTORED SUBSCRIPTION LOGIC:
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
        log.error(f"MQTT Broker: Failed to connect, return code {rc}")
        # If it failed to connect, it's not "intentionally disconnected" in a way that should prevent retries if configured
        mqtt_connection_status = "error" 
    # Schedule broadcast_mqtt_status on the main event loop
    if main_event_loop and main_event_loop.is_running():
        asyncio.run_coroutine_threadsafe(broadcast_mqtt_status(), main_event_loop)
    else:
        log.warning("on_connect: Main event loop not available for broadcasting MQTT status.")

## 断开后输出日志, main eventloop 还在运行则广播 mqtt 状态
def on_disconnect(client, userdata, rc):
    """Callback for when the client disconnects from the MQTT Broker."""
    global mqtt_connection_status, is_mqtt_intentionally_disconnected, runtime_cfg, main_event_loop
    if rc == 0 and is_mqtt_intentionally_disconnected:
        log.info("MQTT Broker: Disconnected gracefully by user request.")
        mqtt_connection_status = "disconnected"
        # is_mqtt_intentionally_disconnected remains true until a connect attempt
    elif rc == 0:
        log.info("MQTT Broker: Disconnected gracefully (not by direct user request).")
        mqtt_connection_status = "disconnected"
    else:
        log.error(f"MQTT Broker: Unexpected disconnection, return code {rc}.")
        mqtt_connection_status = "error"
    
    # Schedule broadcast_mqtt_status on the main event loop
    if main_event_loop and main_event_loop.is_running():
        asyncio.run_coroutine_threadsafe(broadcast_mqtt_status(), main_event_loop)
    else:
        log.warning("on_disconnect: Main event loop not available for broadcasting MQTT status.")
    
    # Optional: Auto-reconnect logic if not intentionally disconnected and enabled in config
    # For now, Paho's default loop_start() handles some retry, but this could be more explicit.
    # if not is_mqtt_intentionally_disconnected and runtime_cfg and runtime_cfg.mqtt.enabled:
    #     log.info("Attempting to reconnect MQTT...")
    #     # Be careful with immediate retries; consider a backoff strategy
    #     # For simplicity, relying on Paho's internal or manual reconnect via UI for now.
    #     pass

## 解析从 sensecap openstream 中收到的数据
def parse_sensecap_payload(device_eui: str, measurement_id: str, payload_bytes: bytes) -> Optional[TrackerReport]:
    """
    Parses the SenseCAP-like payload (JSON string) for beacon data.
    Assumes topic provides DeviceEUI, and payload contains timestamp and beacon list.
    Payload example: {"value":[{"mac":"C3:00:00:3E:7D:DA","rssi":"-53"}, ...],"timestamp":1746522494000}
    """
    try:
        data = json.loads(payload_bytes.decode('utf-8'))
        # log.debug(f"Raw SenseCAP MQTT data for {device_eui}: {data}") # DEBUG

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

        UplinkCollector.set(dev_eui=device_eui, measurement_id='timestamp', value=payload_timestamp)
        beacon_values = None
        match measurement_id:
            case '4197':
                UplinkCollector.set(dev_eui=device_eui, measurement_id=measurement_id, value=data.get("value"))
            case '4198':
                UplinkCollector.set(dev_eui=device_eui, measurement_id=measurement_id, value=data.get("value"))
                time.sleep(1)
                altitude = UplinkCollector.get(dev_eui=device_eui, measurement_id='4197')
                longitude = data.get("value")
                if altitude and longitude:
                    loc = {
                        "alt": altitude,
                        "lon": longitude
                    }
                    loc_type = 'gps'
                    UplinkCollector.set(dev_eui=device_eui, measurement_id='loc', value=loc)
                    UplinkCollector.set(dev_eui=device_eui, measurement_id='loc_type', value=loc_type)
                    return TrackerReport(
                        trackerId=device_eui,
                        timestamp=payload_timestamp,
                        detectedBeacons=beacon_values,
                        loc=loc,
                        loc_type=loc_type
                    )
                log.error(f"illegal gps data for device{device_eui} altitude: {altitude}, longitude: {longitude}")
            case '4200':
                UplinkCollector.set(dev_eui=device_eui, measurement_id=measurement_id, value=data.get("value"))
                log.info(f'detected tracker in sos model: {device_eui}')
                return TrackerReport(
                    trackerId=device_eui,
                    timestamp=payload_timestamp,
                    sos=data.get("value")
                )
            case '5002':
                UplinkCollector.set(dev_eui=device_eui, measurement_id=measurement_id, value=data.get("value"))
                beacon_values = data.get("value")
            case '3000':
                UplinkCollector.set(dev_eui=device_eui, measurement_id=measurement_id, value=data.get("value"))

        if not beacon_values:
            return

        if not isinstance(beacon_values, list):
            log.warning(f"Missing or invalid 'value' list in SenseCAP payload for {device_eui}. No beacons to parse.")
            return TrackerReport(trackerId=device_eui, timestamp=payload_timestamp, detectedBeacons=[], loc={})

        detected_beacons_list = []
        for beacon_data in beacon_values:
            if not isinstance(beacon_data, dict):
                # log.debug(f"Skipping non-dict item in 'value' list for {device_eui}: {beacon_data}") # DEBUG
                continue

            mac_address = beacon_data.get("mac")
            rssi_str = beacon_data.get("rssi")

            if mac_address and rssi_str is not None:
                try:
                    mac_addr_upper = str(mac_address).upper()
                    rssi_val = int(rssi_str)
                    detected = DetectedBeacon(
                        macAddress=mac_addr_upper,
                        rssi=rssi_val
                    )
                    detected_beacons_list.append(detected)
                except (ValueError, TypeError) as conv_err:
                    log.warning(f"Could not convert beacon data for {device_eui}: {beacon_data} - {conv_err}")
            else:
                # log.debug(f"Skipping beacon entry for {device_eui} due to missing mac or rssi: {beacon_data}") # DEBUG
                pass # Keep it quiet

        if not detected_beacons_list:
            # log.info(f"No valid beacons found in SenseCAP payload for tracker {device_eui} after parsing 'value' list.") # Can be noisy
            pass
        return TrackerReport(
            trackerId=device_eui,
            timestamp=payload_timestamp,
            detectedBeacons=detected_beacons_list,
            locType='bluetooth',
            loc={}
        )

    except json.JSONDecodeError:
        log.error(f"Failed to decode JSON payload for {device_eui}: {payload_bytes.decode('utf-8', errors='ignore')}")
        return None
    except Exception as e:
        log.error(f"Error processing SenseCAP MQTT payload for tracker '{device_eui}': {e}", exc_info=True)
        return None

## 创建 mqtt client 连接到 broker
def _initialize_mqtt_client():
    """Creates and configures an MQTT client instance based on runtime_cfg."""
    global mqtt_client, runtime_cfg

    if not runtime_cfg or not runtime_cfg.mqtt:
        log.warning("MQTT runtime configuration not available for client initialization.")
        return None
    code = random.randint(100000, 999999)
    # runtime_cfg.mqtt.clientID.format(clientID=code)
    runtime_cfg.mqtt.clientID = runtime_cfg.mqtt.clientID.replace("{clientID}", str(code))
    mqtt_cfg = runtime_cfg.mqtt
    try:
        client_id_to_use = mqtt_cfg.clientID

        if client_id_to_use:
            new_client = mqtt.Client(client_id=client_id_to_use)
        else:
            new_client = mqtt.Client()

        if mqtt_cfg.username and mqtt_cfg.password:
            new_client.username_pw_set(mqtt_cfg.username, mqtt_cfg.password)
        
        new_client.on_connect = on_connect
        new_client.on_disconnect = on_disconnect
        new_client.on_message = on_message
        log.info(f"本次 mqtt-client: {client_id_to_use}")
        return new_client
    except Exception as e:
        log.error(f"Error initializing MQTT client: {e}", exc_info=True)
        return None

## 实际的 mqtt 连接函数, 除了初始化 mqtt client 还负责日志记录, 连接状态管理
def _connect_mqtt_client():
    """Attempts to connect the global mqtt_client to the broker."""
    global mqtt_client, runtime_cfg, mqtt_connection_status, is_mqtt_intentionally_disconnected, main_event_loop

    if not runtime_cfg or not runtime_cfg.mqtt or not mqtt_client:
        log.warning("MQTT client or configuration not ready for connection.")
        if runtime_cfg and runtime_cfg.mqtt and not mqtt_client:
             # log.info("Attempting to re-initialize MQTT client...") # Can be noisy
             mqtt_client = _initialize_mqtt_client()
             if not mqtt_client:
                  mqtt_connection_status = "error"
                  if main_event_loop and main_event_loop.is_running():
                      asyncio.run_coroutine_threadsafe(broadcast_mqtt_status(), main_event_loop)
                  else:
                      log.warning("_connect_mqtt_client: Main event loop not available for broadcasting MQTT status after init fail.")
                  return False # Failed to initialize
        else:
            return False # Not ready

    mqtt_cfg = runtime_cfg.mqtt
    if not mqtt_cfg.brokerHost:
        log.warning("MQTT brokerHost not configured. Cannot connect.")
        mqtt_connection_status = "misconfigured"
        if main_event_loop and main_event_loop.is_running():
            asyncio.run_coroutine_threadsafe(broadcast_mqtt_status(), main_event_loop)
        else:
            log.warning("_connect_mqtt_client: Main event loop not available for broadcasting MQTT status for misconfig.")
        return False

    if mqtt_connection_status == "connected" or mqtt_connection_status == "connecting":
        # log.info(f"MQTT client already {mqtt_connection_status}. No action needed.") # Can be noisy
        return True

    try:
        # log.info(f"Attempting to connect MQTT client to {mqtt_cfg.brokerHost}...") # Reduced verbosity
        is_mqtt_intentionally_disconnected = False # Clear flag before attempting connection
        mqtt_connection_status = "connecting"
        if main_event_loop and main_event_loop.is_running():
            asyncio.run_coroutine_threadsafe(broadcast_mqtt_status(), main_event_loop)
        else:
            log.warning("_connect_mqtt_client: Main event loop not available for broadcasting MQTT status for connecting.")
        
        mqtt_client.connect_async(mqtt_cfg.brokerHost, mqtt_cfg.brokerPort, 60)
        mqtt_client.loop_start() # loop_start is non-blocking and handles reconnects.
        # Status will be updated by on_connect or on_disconnect callbacks
        return True
    except Exception as e:
        log.error(f"Error during MQTT connect_async or loop_start: {e}", exc_info=True)
        mqtt_connection_status = "error"
        if main_event_loop and main_event_loop.is_running():
            asyncio.run_coroutine_threadsafe(broadcast_mqtt_status(), main_event_loop)
        else:
            log.warning("_connect_mqtt_client: Main event loop not available for broadcasting MQTT status on error.")
        return False

def disconnect_mqtt_client(broadcast=True):
    """Disconnects the MQTT client."""
    global mqtt_client, mqtt_connection_status, is_mqtt_intentionally_disconnected, main_event_loop
    is_mqtt_intentionally_disconnected = True
    if mqtt_client:
        try:
            # log.info("Disconnecting MQTT client...") # Reduced verbosity
            # Stop the loop first to prevent immediate auto-reconnect attempts by Paho
            # Paho's disconnect might also trigger on_disconnect, where status is set.
            mqtt_client.loop_stop() 
            mqtt_client.disconnect() 
            # on_disconnect should handle setting status to "disconnected" and broadcasting
            # However, ensure status is set if on_disconnect isn't triggered as expected
            if mqtt_connection_status != "disconnected":
                 mqtt_connection_status = "disconnected"
                 if broadcast:
                    if main_event_loop and main_event_loop.is_running():
                        asyncio.run_coroutine_threadsafe(broadcast_mqtt_status(), main_event_loop)
                    else:
                        log.warning("disconnect_mqtt_client: Main event loop not available for broadcasting MQTT status for intentionally disconnected.")
            # log.info("MQTT client disconnect initiated.") # Reduced verbosity

        except Exception as e:
            log.error(f"Error disconnecting MQTT client: {e}", exc_info=True)
            mqtt_connection_status = "error" # Or keep as is if disconnect failed partially
            if broadcast:
                if main_event_loop and main_event_loop.is_running():
                    asyncio.run_coroutine_threadsafe(broadcast_mqtt_status(), main_event_loop)
                else:
                    log.warning("disconnect_mqtt_client: Main event loop not available for broadcasting MQTT status on error.")      
    else:
        log.info("MQTT client not initialized, cannot disconnect.")
        mqtt_connection_status = "disconnected" # Already effectively disconnected
        if broadcast:
            if main_event_loop and main_event_loop.is_running():
                asyncio.run_coroutine_threadsafe(broadcast_mqtt_status(), main_event_loop)
            else:
                log.warning("disconnect_mqtt_client: Main event loop not available for broadcasting MQTT status for not initialized.")

## 检查配置并连接 mqtt broker
def setup_mqtt(force_reconnect: bool = False):
    """Initializes and connects the MQTT client if enabled in runtime_cfg."""
    global mqtt_client, runtime_cfg, mqtt_connection_status, main_event_loop, is_mqtt_intentionally_disconnected

    # Ensure runtime_cfg is loaded
    if not runtime_cfg:
        log.warning("Server runtime configuration not loaded. Cannot setup MQTT.")
        mqtt_connection_status = "misconfigured"
        if main_event_loop and main_event_loop.is_running():
            asyncio.run_coroutine_threadsafe(broadcast_mqtt_status(), main_event_loop)
        else:
            log.warning("setup_mqtt: Main event loop not available for broadcasting MQTT status for no runtime_cfg.")
        return

    if not runtime_cfg.mqtt:
        log.info("MQTT configuration section missing. Skipping MQTT setup.")
        mqtt_connection_status = "disabled" # No MQTT config means disabled / not configured
        if main_event_loop and main_event_loop.is_running():
            asyncio.run_coroutine_threadsafe(broadcast_mqtt_status(), main_event_loop)
        else:
            log.warning("setup_mqtt: Main event loop not available for broadcasting MQTT status for no mqtt_cfg.")
        return
        
    # log.info(f"MQTT setup called. Proceeding with setup for {runtime_cfg.mqtt.brokerHost if runtime_cfg.mqtt.brokerHost else 'No Broker Host'}.") # Can be noisy

    if is_mqtt_intentionally_disconnected and not force_reconnect:
        log.info("MQTT was intentionally disconnected. Not reconnecting automatically unless forced.")
        # Ensure status reflects this if it's not already 'disconnected'
        if mqtt_connection_status != "disconnected":
            mqtt_connection_status = "disconnected"
            if main_event_loop and main_event_loop.is_running():
                asyncio.run_coroutine_threadsafe(broadcast_mqtt_status(), main_event_loop)
            else:
                log.warning("setup_mqtt: Main event loop not available for broadcasting MQTT status for intentionally disconnected.")
        return

    if not mqtt_client:
        mqtt_client = _initialize_mqtt_client()
        if not mqtt_client:
            mqtt_connection_status = "error" # Failed to initialize
            if main_event_loop and main_event_loop.is_running():
                asyncio.run_coroutine_threadsafe(broadcast_mqtt_status(), main_event_loop)
            else:
                log.warning("setup_mqtt: Main event loop not available for broadcasting MQTT status after init fail.")
            return
    
    # Attempt to connect
    _connect_mqtt_client()

# This is the new on_message callback
## 接收并处理的入口(仅处理 beacon 定位信息)
def on_message(client, userdata, msg):
    """Callback for when a PUBLISH message is received from the server."""
    global main_event_loop # Access the main event loop

    # log.info(f"MQTT Message Received: Topic: {msg.topic}") # Can be very noisy
    topic_parts = msg.topic.split('/')
    if not msg.topic.startswith('/device_sensor_data/') or len(topic_parts) < 7:
        log.warning(f"Received message on unexpected or incomplete topic structure: {msg.topic}")
        return
    device_eui = topic_parts[3]
    measurement_id = topic_parts[6]
    # if measurement_id != "5002":
    #     # log.debug(f"Ignoring message for tracker {device_eui}, MeasurementID is '{measurement_id}', not '5002'.") # DEBUG
    #     return

    if device_eui not in allow_tracker_list:
        return

    # log.info(f"Processing beacon data for tracker {device_eui} (MeasurementID: {measurement_id})") # Can be noisy
    report = parse_sensecap_payload(device_eui, measurement_id, msg.payload)
    if report:
        if main_event_loop and main_event_loop.is_running():
            asyncio.run_coroutine_threadsafe(process_tracker_report(report), main_event_loop)
        else:
            log.error("Main asyncio event loop not available or not running. Cannot schedule tracker report processing.")
    else:
        log.warning(f"Failed to parse payload or no report generated for tracker {device_eui} from topic {msg.topic}")


## 计算定位结果
async def process_tracker_report(report: TrackerReport):
    """Processes a parsed tracker report to calculate position and update state."""
    # Use new global config variables
    global web_ui_cfg, runtime_cfg, tracker_states, kalman_filters, dashboard_cfg

    if not web_ui_cfg or not web_ui_cfg.beacons:
        log.warning("Web UI configuration (beacons) not loaded, cannot process tracker report.")
        return
    if not runtime_cfg:
        log.warning("Server runtime configuration not loaded, cannot process tracker report for Kalman params.")
        return

    if report.locType == "gps":
        tracker_data_payload = {
            "trackerId": report.trackerId,
            "timestamp": report.timestamp,
            "position": report.loc,
            "locType": report.locType,
            "sos": report.sos
        }
        tracker_id = report.trackerId
        await manager.broadcast({
            "type": "tracker_update",
            "data": {tracker_id: tracker_data_payload}
        })
        return

    if report.sos != 2 and tracker_states.get(report.trackerId, None):
        log.info(f'broadcast tracker sos event: {report.trackerId}')
        await manager.broadcast({
            "type": "tracker_sos",
            "data": {report.trackerId: {
                "timestamp": report.timestamp,
                "sos": report.sos
            }}
        })

        time.sleep(2)
        now_loc_type = UplinkCollector.get(dev_eui=report.trackerId, measurement_id='loc_type')

        # 检查设备SOS状态是否发生变化
        previous_sos = tracker_states.get(report.trackerId, {}).get('sos', 2)
        current_sos = report.sos
        
        # 如果状态发生变化，创建告警记录
        if previous_sos != current_sos and current_sos != 2:  # 排除未知状态
            # 更新设备SOS状态映射
            tracker_states.get(report.trackerId, {}).sos = current_sos
            
            # 确定使用的定位信息和类型
            alarm_loc = UplinkCollector.get(dev_eui=report.trackerId, measurement_id='loc', default_value=None)
            pos_type = UplinkCollector.get(dev_eui=report.trackerId, measurement_id='loc_type')
            if not alarm_loc:
                alarm_loc = {}
            if not pos_type:
                pos_type = 'unknown'

            
            # 创建告警记录
            try:
                # 将timestamp从毫秒转换为datetime对象
                from datetime import datetime
                alarm_time = datetime.fromtimestamp(report.timestamp / 1000.0)
                
                # 获取设备当前所在的地图
                current_tracker_state = tracker_states.get(report.trackerId)
                map_name = current_tracker_state.map if current_tracker_state and current_tracker_state.map else None
                
                alarm_record_dao.create_record(
                    dev_eui=report.trackerId, 
                    loc=alarm_loc, 
                    pos_type=pos_type, 
                    alarm_time=alarm_time,
                    sos=current_sos,
                    map_name=map_name
                )
                
                log.info(f"设备 {report.trackerId} SOS状态变化: {previous_sos} -> {current_sos}，已创建告警记录")
            except Exception as e:
                log.error(f"创建告警记录失败: {e}")
        else:
            # 如果状态没有变化，仍需更新映射以跟踪当前状态
            tracker_states.get(report.trackerId, {}).sos = current_sos
        return

    log.info(f"开始进行蓝牙定位计算: eui=>{report.trackerId}")
    tracker_id = report.trackerId
    current_time_ms = int(time.time() * 1000)
    last_state = tracker_states.get(tracker_id)
    last_known_pos = (last_state.x, last_state.y) if last_state and last_state.x is not None and last_state.y is not None else None
    dt = (current_time_ms - last_state.last_update_time) / 1000.0 if last_state else 0.1

    # Prepare position history from last state
    current_position_history = list(last_state.position_history) if last_state and last_state.position_history else []

    # log.info(f"Processing report for {tracker_id} with {len(report.detectedBeacons)} beacons.") # Can be noisy

    calculated_position = positioning.calculate_position(
        detected_beacons=report.detectedBeacons,
        miniprogram_config=web_ui_cfg,
        device_id=tracker_id
        # signal_propagation_factor is inside web_ui_cfg.settings
    )


    filtered_position: Optional[Tuple[float, float]] = None
    kf = kalman_filters.get(tracker_id)

    if calculated_position:
        # log.info(f"Calculated position for {tracker_id}: {calculated_position}") # Can be noisy
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
            # log.info(f"Initialized Kalman filter for {tracker_id} with PV:{runtime_cfg.kalman.processVariance}, MV:{runtime_cfg.kalman.measurementVariance}") # Can be noisy

        filtered_position = kf.get_position()
        # log.info(f"Filtered position for {tracker_id}: {filtered_position}") # Can be noisy
        
        # Add new position to history
        if filtered_position:
            current_position_history.append((filtered_position[0], filtered_position[1], current_time_ms))

    elif kf: # No new calculation, but KF might have predicted
        kf.predict(dt)
        filtered_position = kf.get_position()
        # log.info(f"Position prediction (no new measurement) for {tracker_id}: {filtered_position}") # Can be noisy
        # Optionally, decide if predicted-only positions should go into history.
        # For now, let's assume only measurement-updated or KF-initialized positions go to history via the block above.
        # If you want to add predicted positions too, uncomment and adjust:
        # if filtered_position:
        #     current_position_history.append((filtered_position[0], filtered_position[1], current_time_ms))

    # Prune history to last 30 minutes (30 * 60 * 1000 ms)
    history_time_window_ms = 30 * 60 * 1000
    cutoff_time_ms = current_time_ms - history_time_window_ms
    current_position_history = [p for p in current_position_history if p[2] >= cutoff_time_ms]

    log.info(f"device({tracker_id}) 最终定位: ${current_position_history}") # Can be noisy
    new_state = TrackerState(
        trackerId=tracker_id,
        x=filtered_position[0] if filtered_position else (last_state.x if last_state else None),
        y=filtered_position[1] if filtered_position else (last_state.y if last_state else None),
        last_update_time=current_time_ms,
        last_known_measurement_time=report.timestamp,
        last_detected_beacons=report.detectedBeacons,
        position_history=current_position_history,
        map=calculated_position[2]
    )
    tracker_states[tracker_id] = new_state

    # Prepare data for WebSocket broadcast
    position_payload = None
    if new_state.x is not None and new_state.y is not None:
        position_payload = {"x": new_state.x, "y": new_state.y}
        # Add accuracy if available and needed by frontend, e.g.:
        # if kf and hasattr(kf, 'get_accuracy_somehow'): 
        #    position_payload['accuracy'] = kf.get_accuracy_somehow()

    # Construct the data payload for the specific tracker_id

    UplinkCollector.set(dev_eui=tracker_id, measurement_id='loc', value=position_payload)
    UplinkCollector.set(dev_eui=tracker_id, measurement_id='loc_type', value='bluetooth')
    enriched_detected_beacons = []
    if new_state.last_detected_beacons and web_ui_cfg and web_ui_cfg.beacons:
        configured_beacons_map = {b.macAddress: b for b in web_ui_cfg.beacons if b.macAddress} # Create a map for quick lookup by MAC
        for detected_b in new_state.last_detected_beacons:
            enriched_b_data = detected_b.model_dump() # Start with macAddress, rssi, etc. from DetectedBeacon
            configured_b = configured_beacons_map.get(detected_b.macAddress)
            if configured_b:
                enriched_b_data['txPower'] = configured_b.txPower
                enriched_b_data['name'] = configured_b.displayName
                enriched_b_data['configured_x'] = configured_b.x
                enriched_b_data['configured_y'] = configured_b.y
            else:
                # If no matching configured beacon by MAC, fill with None or defaults for consistency if needed
                enriched_b_data['txPower'] = None 
                enriched_b_data['name'] = 'Unknown Beacon'
                enriched_b_data['configured_x'] = None
                enriched_b_data['configured_y'] = None
            enriched_detected_beacons.append(enriched_b_data)
    else:
        # Fallback if no web_ui_cfg.beacons or no detected_beacons, send basic detected beacon info
        enriched_detected_beacons = [b.model_dump() for b in new_state.last_detected_beacons] if new_state.last_detected_beacons else []

    tracker_data_payload = {
        "trackerId": new_state.trackerId,
        "timestamp": new_state.last_update_time, 
        "position": position_payload, 
        "last_detected_beacons": enriched_detected_beacons, # Use the enriched list
        "position_history": new_state.position_history,
        "map": calculated_position[2],
        "sos": report.sos
    }

    await manager.broadcast({
        "type": "tracker_update", 
        "data": {tracker_id: tracker_data_payload}
    })

# --- Configuration Loading for Web UI ---
def load_web_ui_config() -> Optional[WebUIConfig]:
    global web_ui_cfg, beacon_map
    if not os.path.exists(WEB_CONFIG_FILE_PATH):
        log.info(f"Web UI configuration file not found at {WEB_CONFIG_FILE_PATH}. Initializing with defaults.")
        # Initialize with default if file doesn't exist
        default_settings = WebUISettings() # Use direct model name
        web_ui_cfg = WebUIConfig(map=None, beacons=[], settings=default_settings)
        save_web_ui_config(web_ui_cfg) # Save the initial default config
        return web_ui_cfg
    try:
        with open(WEB_CONFIG_FILE_PATH, 'r') as f:
            data = json.load(f)
            web_ui_cfg = WebUIConfig(**data)
            log.info(f"Web UI configuration loaded successfully from {WEB_CONFIG_FILE_PATH}.")
            # if web_ui_cfg and len(web_ui_cfg.beacons):
            #     for beacon in web_ui_cfg.beacons:
            #         if not beacon.map:
            #             beacon = web_ui_cfg.map.name
            #         beacon_map[beacon.macAddress] = beacon
            return web_ui_cfg
    except FileNotFoundError:
        log.warning(f"Web UI configuration file not found at {WEB_CONFIG_FILE_PATH} during load attempt. This should have been handled by prior check.")
        return None # Should not happen if check above is correct
    except json.JSONDecodeError as e:
        log.error(f"Error decoding JSON from Web UI config file {WEB_CONFIG_FILE_PATH}: {e}")
        return None
    except Exception as e:
        log.error(f"Failed to load Web UI configuration from {WEB_CONFIG_FILE_PATH}: {e}", exc_info=True)
        return None

def load_dashboard_config() -> Optional[DashboardConfig]:
    global dashboard_cfg, beacon_map
    if not os.path.exists(DASHBOARD_CONFIG_FILE_PATH):
        log.info(f"Dashboard configuration file not found at {DASHBOARD_CONFIG_FILE_PATH}. Initializing with defaults.")
        dashboard_cfg = DashboardConfig(maps=[])
        # save_web_ui_config(dashboard_cfg) # Save the initial default config
        return dashboard_cfg
    try:
        with open(DASHBOARD_CONFIG_FILE_PATH, 'r') as f:
            data = json.load(f)
            dashboard_cfg = DashboardConfig(**data)
            log.info(f"Dashboard configuration loaded successfully from {DASHBOARD_CONFIG_FILE_PATH}.")
            beacon_holder.update_by_dashboard_config(dashboard_cfg)
            return dashboard_cfg
    except FileNotFoundError:
        log.warning(f"Dashboard configuration file not found at {DASHBOARD_CONFIG_FILE_PATH} during load attempt. This should have been handled by prior check.")
        return None # Should not happen if check above is correct
    except json.JSONDecodeError as e:
        log.error(f"Error decoding JSON from Dashboard config file {DASHBOARD_CONFIG_FILE_PATH}: {e}")
        return None
    except Exception as e:
        log.error(f"Failed to load Dashboard configuration from {DASHBOARD_CONFIG_FILE_PATH}: {e}", exc_info=True)
        return None

def save_web_ui_config(config_data: WebUIConfig) -> bool:
    try:
        with open(WEB_CONFIG_FILE_PATH, 'w') as f:
            json.dump(config_data.model_dump(mode='json'), f, indent=4)
        log.info(f"Web UI configuration saved successfully to {WEB_CONFIG_FILE_PATH}.")
        return True
    except Exception as e:
        log.error(f"Failed to save Web UI configuration to {WEB_CONFIG_FILE_PATH}: {e}", exc_info=True)
        return False

# --- FastAPI Event Handlers ---
@app.on_event("startup")
async def startup_event():
    """Runs on application startup. Loads both configurations and sets up MQTT."""
    global miniprogram_cfg, runtime_cfg, main_event_loop, web_ui_cfg
    
    # Capture the running event loop for thread-safe calls from MQTT callback
    main_event_loop = asyncio.get_running_loop()
    
    log.info("Server startup sequence initiated.")
    
    # Load server runtime configuration first as it might be needed by other components
    runtime_cfg = config_manager.load_server_runtime_config()
    if not runtime_cfg:
        log.error("Critical: Server runtime configuration could not be loaded. MQTT and other services might not start.")
        # Depending on desired behavior, could raise an exception or proceed with limited functionality
    else:
        log.info(f"Server runtime configuration loaded. MQTT enabled: {runtime_cfg.mqtt.enabled}")

    # Load miniprogram configuration
    miniprogram_cfg = config_manager.load_miniprogram_config()
    if not miniprogram_cfg:
        log.warning("Miniprogram configuration (map_beacon_config.json) not found or failed to load. Positioning may be affected.")
    else:
        # log.info("Miniprogram configuration (map_beacon_config.json) loaded.") # Reduced verbosity
        pass

    # Load Web UI configuration
    web_ui_cfg = load_web_ui_config() # This will create a default if not found
    if not web_ui_cfg:
        log.warning("Web UI configuration (web_config.json) not found or failed to load. Web UI may not function as expected initially.")
    else:
        # log.info("Web UI configuration (web_config.json) loaded/initialized.") # Reduced verbosity
        pass

    if runtime_cfg and runtime_cfg.mqtt.enabled:
        setup_mqtt() # Initialize and connect MQTT client
    else:
        log.info("MQTT client is disabled in server runtime configuration. Skipping MQTT setup.")
        global mqtt_connection_status
        mqtt_connection_status = "disabled"
        await broadcast_mqtt_status() # Inform clients that MQTT is disabled
    
    log.info("Server startup complete.")

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
    # log.info("Received request to upload miniprogram configuration.") # Reduced verbosity
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


@app.post("/api/test/push_sos")
async def push_sos(report: TrackerReport):

    report.timestamp = int(time.time()) * 1000
    if main_event_loop and main_event_loop.is_running():
        asyncio.run_coroutine_threadsafe(process_tracker_report(report), main_event_loop)

# @app.get("/api/test")
# async def api_test():
#     # return alarm_record_dao.create_record(dev_eui='2CF7F1C0530004AD', loc={'x': 11, 'y': 22}, pos_type='bluetooth')
#
#     print(pydantic.json(alarm_record_dao.get_records_by_dev_eui(dev_eui='2CF7F1C0530004AD')))

@app.get("/api/list_alarm")
async def list_device_alarms(
    device_eui: str = Query(..., description="设备EUI"),
    page: int = Query(1, ge=1, description="页码，从1开始"),
    page_size: int = Query(20, ge=1, le=100, description="每页记录数，最大100"),
    map_name: Optional[str] = Query(None, description="地图名称，可选筛选条件")
):
    """
    查询设备报警记录，支持分页和地图筛选

    Parameters:
    - device_eui: 设备EUI (必填)
    - page: 页码，从1开始 (默认1)
    - page_size: 每页记录数，最大100 (默认20)
    - map_name: 地图名称，可选筛选条件

    Returns:
    - records: 报警记录列表
    - total: 总记录数
    - page: 当前页码
    - page_size: 每页记录数
    - total_pages: 总页数
    """
    try:
        records, total = alarm_record_dao.get_records_by_dev_eui(
            dev_eui=device_eui,
            page=page,
            page_size=page_size,
            map_name=map_name
        )

        total_pages = (total + page_size - 1) // page_size  # 计算总页数

        return {
            "code": 200,
            "message": "查询成功",
            "data": {
                "records": [record.to_dict() for record in records],
                "pagination": {
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": total_pages
                }
            }
        }

    except Exception as e:
        log.error(f"查询设备报警记录失败: device_eui={device_eui}, error={e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@app.get("/api/trackers")
async def get_trackers():
    """Returns the current state of all known trackers."""
    return tracker_states

@app.get("/api/server-runtime-config", response_model=Optional[config_manager.ServerRuntimeConfig])
async def get_api_server_runtime_config():
    global runtime_cfg, mqtt_connection_status # Ensure mqtt_connection_status is accessible
    # Ensure runtime_cfg is loaded
    if runtime_cfg is None:
        config_manager.load_server_runtime_config() # Attempt to load if not already loaded by startup
    
    if runtime_cfg:
        # Create a copy to avoid modifying the global cache directly with transient status
        config_to_send = runtime_cfg.model_copy(deep=True)
        if config_to_send.mqtt:
            config_to_send.mqtt.live_mqtt_status = mqtt_connection_status
            # Mask password before sending to client
            if config_to_send.mqtt.password:
                 config_to_send.mqtt.password = config_manager.PASSWORD_PLACEHOLDER
        return config_to_send
    return None

@app.post("/api/server-runtime-config", status_code=200)
async def update_api_server_runtime_config(config_payload: config_manager.ServerRuntimeConfig):
    global runtime_cfg, mqtt_client, mqtt_connection_status, is_mqtt_intentionally_disconnected, main_event_loop
    try:
        # log.info("Received request to update server runtime configuration.") # Reduced verbosity
        
        # Determine if MQTT settings that require a reconnect have changed
        mqtt_reconnect_needed = False
        if runtime_cfg and runtime_cfg.mqtt and config_payload.mqtt:
            if (
                runtime_cfg.mqtt.brokerHost != config_payload.mqtt.brokerHost or
                runtime_cfg.mqtt.brokerPort != config_payload.mqtt.brokerPort or
                runtime_cfg.mqtt.username != config_payload.mqtt.username or
                (config_payload.mqtt.password != config_manager.PASSWORD_PLACEHOLDER and 
                 config_payload.mqtt.password is not None and # Ensure new password is not None
                 runtime_cfg.mqtt.password != config_payload.mqtt.password) or # This comparison is tricky due to placeholder
                runtime_cfg.mqtt.clientID != config_payload.mqtt.clientID or
                runtime_cfg.mqtt.applicationID != config_payload.mqtt.applicationID or # If appID changes, topic changes
                runtime_cfg.mqtt.topicPattern != config_payload.mqtt.topicPattern # If topic pattern changes
            ):
                mqtt_reconnect_needed = True
            
            # If MQTT is being enabled and was previously disabled or misconfigured, or if it was intentionally disconnected
            if config_payload.mqtt.enabled and not runtime_cfg.mqtt.enabled:
                mqtt_reconnect_needed = True
            elif config_payload.mqtt.enabled and is_mqtt_intentionally_disconnected:
                 mqtt_reconnect_needed = True # If user enables it again after manual disconnect

        # Save the new configuration (this handles the password placeholder logic internally)
        success, new_cfg = config_manager.save_server_runtime_config(config_payload)
        if success and new_cfg:
            runtime_cfg = new_cfg # Update global runtime_cfg with the effectively saved one
            log.info("Server runtime configuration updated successfully.")

            # Handle MQTT client based on changes
            if config_payload.mqtt:
                # If MQTT settings are present in payload, but it's marked as not enabled (e.g. checkbox was there and unchecked)
                # OR if the intention is to disable (though we removed the explicit 'enabled' flag check for disconnection here.
                # For now, removing the direct 'enabled' flag check for disconnection here.
                # Disconnection will be handled by manual API call or if essential config (like broker) is removed.
                # if not config_payload.mqtt.enabled: <--- REMOVED THIS CONDITION
                # Consider if removing broker host should trigger disconnect if connected
                if not config_payload.mqtt.brokerHost and (mqtt_connection_status == "connected" or mqtt_connection_status == "connecting"):
                    log.info("MQTT broker host removed from config. Disconnecting client.")
                    disconnect_mqtt_client()
                    mqtt_connection_status = "misconfigured" # Mark as misconfigured
                    if main_event_loop and main_event_loop.is_running():
                         asyncio.run_coroutine_threadsafe(broadcast_mqtt_status(), main_event_loop)
                elif mqtt_reconnect_needed:
                    log.info("MQTT configuration changed that requires reconnect. Reconnecting...")
                    # Disconnect existing client before reconnecting with new settings
                    if mqtt_client and (mqtt_connection_status == "connected" or mqtt_connection_status == "connecting"):
                        disconnect_mqtt_client(broadcast=False) # Disconnect silently first
                    
                    # Re-initialize and connect. setup_mqtt will use the new runtime_cfg.
                    is_mqtt_intentionally_disconnected = False # Clear this flag as we intend to connect
                    setup_mqtt(force_reconnect=True) 
                else:
                    # log.info("MQTT settings updated, but no immediate reconnect needed (e.g. only Kalman params changed or MQTT already aligned).") # Reduced verbosity
                    pass
            return {"message": "Server runtime configuration updated successfully."}
        else:
            log.error("Failed to save server runtime configuration to file.")
            raise HTTPException(status_code=500, detail="Failed to save server runtime configuration.")
    except Exception as e:
        log.error(f"Error updating server runtime config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/mqtt-status")
async def get_mqtt_connection_status():
    return {"status": mqtt_connection_status}

@app.post("/api/mqtt/connect", status_code=200)
async def api_mqtt_connect():
    global runtime_cfg, mqtt_connection_status, is_mqtt_intentionally_disconnected, main_event_loop
    # log.info("API call to connect MQTT.") # Reduced verbosity
    
    # Reload runtime_cfg to ensure latest settings are used for connection attempt
    current_runtime_cfg = config_manager.load_server_runtime_config()
    if not current_runtime_cfg or not current_runtime_cfg.mqtt:
        log.warning("MQTT Connect API: Runtime configuration or MQTT section not found.")
        raise HTTPException(status_code=400, detail="MQTT configuration not available.")
    
    runtime_cfg = current_runtime_cfg # Update global runtime_cfg

    if not runtime_cfg.mqtt.enabled:
        log.info("MQTT Connect API: MQTT is disabled in configuration. Cannot connect manually unless enabled first.")
        # We could choose to enable it here, but for now, require it to be enabled in config first.
        # return {"message": "MQTT is disabled in configuration. Please enable it first in Server Runtime Configuration then try connecting."}
        raise HTTPException(status_code=400, detail="MQTT is disabled in configuration. Enable it via settings first.")

    is_mqtt_intentionally_disconnected = False # User intends to connect
    
    # Attempt to setup/connect. setup_mqtt handles initialization if needed.
    setup_mqtt(force_reconnect=True) # Force reconnect will bypass the is_mqtt_intentionally_disconnected check within setup_mqtt

    # setup_mqtt and its chain will update mqtt_connection_status and broadcast.
    # The status returned here might be "connecting" or the result of the attempt.
    # Give a slight delay for connection attempt to progress before returning status
    await asyncio.sleep(0.1) # Small delay
    return {"message": "MQTT connection process initiated.", "current_status": mqtt_connection_status}

@app.post("/api/mqtt/disconnect", status_code=200)
async def api_mqtt_disconnect():
    global mqtt_connection_status
    # log.info("API call to disconnect MQTT.") # Reduced verbosity
    disconnect_mqtt_client() # This function sets is_mqtt_intentionally_disconnected = True
    # Give a slight delay for disconnection to reflect
    await asyncio.sleep(0.1) 
    return {"message": "MQTT disconnect process initiated.", "current_status": mqtt_connection_status}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Handles WebSocket connections."""
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # log.info(f"WebSocket received: {data}") # Can be noisy
            try:
                message = json.loads(data)
                command = message.get("command")

                if command == "startScan":
                    log.info("Start scan command received.")
                    # TODO: Implement actual Bluetooth scanning logic here
                    # For now, send a confirmation that scan started.
                    await manager.broadcast({"type": "info", "message": "Scanning started."})
                elif command == "stopScan":
                    log.info("Stop scan command received.")
                    # TODO: Implement logic to stop Bluetooth scanning here
                    # For now, send a confirmation that scan stopped.
                    await manager.broadcast({"type": "info", "message": "Scanning stopped."})
                elif message.get("action") == "request_initial_data": # Example action, kept for now
                    # Send initial data if needed
                    await manager.broadcast({"type": "initial_data", "payload": "some_initial_state"})
                else:
                    log.warning(f"Unknown command/action received: {message}")
                    await manager.broadcast({"type": "error", "message": "Unknown command"})

            except json.JSONDecodeError:
                log.error(f"Error decoding JSON from WebSocket: {data}")
                await manager.broadcast({"type": "error", "message": "Error decoding JSON"})

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        log.error(f"WebSocket error for client {websocket.client}: {e}", exc_info=True)
        manager.disconnect(websocket) # Ensure disconnect on error

# --- Web UI Configuration Endpoints ---
@app.post("/api/configuration/web", status_code=200)
async def upload_web_ui_config(config_content: WebUIConfig, response: Response):
    global web_ui_cfg
    try:
        if save_web_ui_config(config_content):
            web_ui_cfg = config_content # Update in-memory cache
            # log.info("Web UI configuration successfully received and saved.") # Reduced verbosity
            return {"message": "Web UI configuration saved successfully."}
        else:
            raise HTTPException(status_code=500, detail="Failed to save Web UI configuration to file.")
    except Exception as e:
        log.error(f"Error processing uploaded Web UI configuration: {e}", exc_info=True)
        # It's good practice to re-raise HTTPException or return a proper error response
        raise HTTPException(status_code=500, detail=f"Internal server error while saving Web UI configuration: {str(e)}")

@app.get("/api/configuration/web", response_model=Optional[WebUIConfig])
async def get_web_ui_config():
    global web_ui_cfg
    # Ensure it's loaded on first request if not already by startup (though startup should handle it)
    if web_ui_cfg is None:
        # log.info("Web UI config not in memory, attempting to load from file for GET request.") # Reduced verbosity
        load_web_ui_config() # Attempt to load it if somehow missed by startup or cleared
    
    if web_ui_cfg:
        return web_ui_cfg
    else:
        log.warning("GET /api/configuration/web: No Web UI configuration available after load attempt.")
        return WebUIConfig(map=None, beacons=[], settings=WebUISettings()) # Use direct model name


@app.get("/api/configuration/dashboard", response_model=Optional[DashboardConfig])
async def get_dashboard_config():
    global dashboard_cfg
    # Ensure it's loaded on first request if not already by startup (though startup should handle it)
    if dashboard_cfg is None:
        # log.info("Web UI config not in memory, attempting to load from file for GET request.") # Reduced verbosity
        load_dashboard_config()  # Attempt to load it if somehow missed by startup or cleared

    if dashboard_cfg:
        return dashboard_cfg
    else:
        log.warning("GET /api/configuration/dashboard: No Dashboard configuration available after load attempt.")
        return DashboardConfig(maps=None)  # Use direct model name

@app.get("/api/default-test-config")
async def get_default_test_config():
    if not os.path.exists(DEFAULT_TEST_CONFIG_PATH):
        log.error(f"Default test config file not found at: {DEFAULT_TEST_CONFIG_PATH}")
        raise HTTPException(status_code=404, detail="Default test configuration file not found.")
    try:
        with open(DEFAULT_TEST_CONFIG_PATH, 'r') as f:
            config_content = f.read()
        # Return as plain text, as the frontend expects to parse it as JSON string
        return PlainTextResponse(content=config_content)
    except Exception as e:
        log.error(f"Error reading default test config file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to read default test configuration: {str(e)}")

@app.get("/api/map-example-format") # New endpoint
async def get_map_example_format():
    if not os.path.exists(MAP_EXAMPLE_FORMAT_PATH):
        log.error(f"Map example format file not found at: {MAP_EXAMPLE_FORMAT_PATH}")
        raise HTTPException(status_code=404, detail="Map example format file not found.")
    try:
        with open(MAP_EXAMPLE_FORMAT_PATH, 'r') as f:
            config_content = f.read()
        return PlainTextResponse(content=config_content)
    except Exception as e:
        log.error(f"Error reading map example format file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to read map example format: {str(e)}")

@app.post("/api/allow_tracker-list", status_code=200)
async def update_allow_tracker_list(request: TrackerListUpdateRequest):
    """更新tracker_list配置"""
    global runtime_cfg
    
    try:
        # 验证tracker_list中的每个项目都是有效字符串
        if not isinstance(request.tracker_list, list):
            raise HTTPException(status_code=400, detail="tracker_list must be a list")
        
        for item in request.tracker_list:
            if not isinstance(item, str):
                raise HTTPException(status_code=400, detail="All items in tracker_list must be strings")
            if len(item.strip()) == 0:
                raise HTTPException(status_code=400, detail="tracker_list items cannot be empty strings")
        
        # 加载当前配置
        current_cfg = config_manager.load_server_runtime_config()
        if not current_cfg:
            raise HTTPException(status_code=500, detail="Cannot load server runtime configuration")
        
        # 更新tracker_list，转为大写
        current_cfg.tracker_list = [item.strip().upper() for item in request.tracker_list]
        
        # 保存配置
        success, new_cfg = config_manager.save_server_runtime_config(current_cfg)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to save tracker_list configuration")
        
        # 更新全局配置
        runtime_cfg = new_cfg
        
        log.info(f"tracker_list updated successfully. New list: {current_cfg.tracker_list}")
        
        return {
            "success": True, 
            "message": "tracker_list updated successfully", 
            "tracker_list": current_cfg.tracker_list
        }
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error updating tracker_list: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/allow_tracker-list")
async def get_allow_tracker_list():
    """获取当前的tracker_list配置"""
    try:
        current_cfg = config_manager.load_server_runtime_config()
        if not current_cfg:
            return {"tracker_list": []}
        
        return {"tracker_list": [item.upper() for item in current_cfg.tracker_list]}
        
    except Exception as e:
        log.error(f"Error getting tracker_list: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/list_paas_device")
async def get_paas_devices():
    """获取PaaS平台设备列表"""
    try:
        # 获取当前配置中的PaaS认证信息
        current_cfg = config_manager.load_server_runtime_config()
        if not current_cfg or not current_cfg.paas_api_id or not current_cfg.paas_api_key:
            raise HTTPException(status_code=400, detail="PaaS API credentials not configured")
        
        # 动态导入paas_client以避免循环导入
        from server.clients.paas_client import initialize_paas_client, get_paas_client
        
        # 初始化PaaS客户端
        host = getattr(current_cfg, 'paas_host', 'https://sensecap.seeed.cc/openapi')  # 使用配置中的host或默认值
        username = current_cfg.paas_api_id
        password = current_cfg.paas_api_key
        
        if not initialize_paas_client(host, username, password):
            raise HTTPException(status_code=500, detail="Failed to initialize PaaS client")
        
        client = get_paas_client()
        if not client:
            raise HTTPException(status_code=500, detail="PaaS client not available")
        
        # 获取设备列表
        devices = client.list_devices(device_type=2)
        if devices is None:
            raise HTTPException(status_code=500, detail="Failed to retrieve devices from PaaS")
        
        # 转换为字典格式返回
        device_list = [device.to_dict() for device in devices]
        
        return {
            "success": True,
            "data": device_list,
            "count": len(device_list)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error getting PaaS devices: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

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

    allow_tracker_list = rt_cfg.tracker_list
    log.info(f"Starting Uvicorn server on host 0.0.0.0 port {server_port}")
    load_dashboard_config()
    load_web_ui_config()
    # Uvicorn should be run from project root: uvicorn server.main:app --reload
    uvicorn.run(app, host="0.0.0.0", port=server_port) 