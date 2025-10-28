import uvicorn
from fastapi import (
    FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Response,
    Query, Request, Depends
)
from pydantic import BaseModel
from fastapi.responses import FileResponse, PlainTextResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import json
import paho.mqtt.client as mqtt
import logging
import time
from typing import List, Dict, Optional, Tuple
import os  # Keep one os import
import random
import hashlib
import base64
from server.components.beacon_holder import beacon_holder
from server.components.device_holder import device_holder
from server.components.websocket_holder import websocket_holder
from server.dao.device_alarm_record_dao import alarm_record_dao
from server.dao.group_dao import group_dao
from server.dao.device_dao import device_dao
from server.components.event_manager import event_manager

from server.components.session_holder import session_holder

from server.handler import uplink_consumer as uplink_consumer
from server.handler import offline_handler as device_offline_checker
from server.handler import event_trigger as event_trigger

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
from server.config import config_manager
from server.models import (  # Grouped imports for models
    DetectedBeacon, TrackerReport, TrackerState, WebUIBeaconConfig,
    MiniprogramConfig, WebUIConfig, DashboardConfig, MqttServerConfig,
    PartialServerRuntimeConfig, PasswordChangeRequest,
    LoginRequest,  # Import WebUISettings directly
    UserSessionInfo, GroupCreateRequest, GroupUpdateRequest, GroupListItem,
    DeviceUpdateRequest, DeviceListItem, DeviceSearchRequest,
    DeviceBatchUpdateGroupRequest, TrackerInfo, TrackerStateQueryRequest,
    EventTriggerCreateRequest, EventTriggerUpdateRequest, EventTriggerListItem
)
from server.positioning import KalmanFilter2D

# Configure logging
logging.basicConfig(level=logging.INFO)  # Keep level INFO for now, but will reduce specific log.info calls
log = logging.getLogger(__name__)

# Add asyncio import if not already present globally, for create_task
import asyncio

cors_origins = [
    "*"
]

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define the path for the web configuration file
WEB_CONFIG_FILE_PATH = os.path.join(os.path.dirname(__file__), "config/web_config.json")


DEFAULT_TEST_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "test", "config2.json")
MAP_EXAMPLE_FORMAT_PATH = os.path.join(os.path.dirname(__file__), "config/map-example-format.json")  # Path to map example format in server directory

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
dashboard_cfg: Optional[DashboardConfig] = None
runtime_cfg: Optional[
    config_manager.ServerRuntimeConfig] = None  # Use qualified name to avoid circular import if ServerRuntimeConfig is also defined here
main_event_loop: Optional[asyncio.AbstractEventLoop] = None  # Added for thread-safe coroutine scheduling
mqtt_connection_status: str = "disconnected"  # Added for live MQTT status
is_mqtt_intentionally_disconnected: bool = False  # Flag for manual disconnects
shutdown_flag: bool = False  # Flag for graceful shutdown


mqtt_clients: Dict[str, Optional[mqtt.Client]] = {}  # Multiple MQTT clients for different data sources
mqtt_connection_statuses: Dict[str, str] = {}  # Connection status for each data source
beacon_map: Dict[str, WebUIBeaconConfig] = {}

allow_tracker_list: list[str] = []


# Request models for API endpoints
class TrackerListUpdateRequest(BaseModel):
    tracker_list: List[str] = []


# --- WebSocket Authentication Functions ---
def _parse_basic_auth(auth_header: str) -> Optional[Tuple[str, str]]:
    """解析HTTP Basic Authentication头部，返回(username, password)或None"""
    try:
        if not auth_header.startswith('Basic '):
            return None
        
        # 移除'Basic '前缀并解码base64
        encoded_credentials = auth_header[6:]
        decoded_bytes = base64.b64decode(encoded_credentials)
        decoded_str = decoded_bytes.decode('utf-8')
        
        # 分割用户名和密码
        if ':' not in decoded_str:
            return None
            
        username, password = decoded_str.split(':', 1)
        return (username, password)
    except Exception as e:
        logging.warning(f"Error parsing Basic Auth header: {e}")
        return None

def _verify_basic_auth(username: str, password: str) -> bool:
    """验证Basic Auth凭据是否与runtime_config中的配置匹配"""
    global runtime_cfg
    if not runtime_cfg:
        return False
    return runtime_cfg.username == username and runtime_cfg.password == password

async def websocket_auth_handler(websocket: WebSocket) -> bool:
    await websocket.accept()
    return True
    """WebSocket认证处理器"""
    # 首先检查cookie认证
    # session_token = websocket.cookies.get("session_token")
    # session_token = websocket.headers.get("session_token")
    # if session_token and len(session_token) > 0 and session_holder.get(session_token):
    #     logging.info(f"ws-session: {session_token}")
    #     await websocket.accept()
    #     log.info(f"WebSocket client connected via session: {websocket.client}")
    #     return True
    #
    # # 检查Authorization头部的Basic Auth
    # auth_header = websocket.headers.get("Authorization")
    # if auth_header:
    #     credentials = _parse_basic_auth(auth_header)
    #     if credentials:
    #         username, password = credentials
    #         if _verify_basic_auth(username, password):
    #             logging.info(f"ws-basic-auth: {username}")
    #             await websocket.accept()
    #             log.info(f"WebSocket client connected via Basic Auth: {websocket.client}")
    #             return True
    #         else:
    #             logging.warning(f"WebSocket Basic Auth failed for user: {username}")
    #     else:
    #         logging.warning("WebSocket received invalid Authorization header format")
    #
    # # 认证失败，关闭连接
    # logging.warning(f"WebSocket connection rejected - no valid authentication: {websocket.client}")
    # await websocket.close(code=1008, reason="Authentication required")
    # return False


# --- MQTT Handling ---
## 广播当前 mqtt 状态
async def broadcast_mqtt_status():
    """Helper to broadcast the current MQTT status via WebSocket."""
    global mqtt_connection_statuses, main_event_loop, manager
    if main_event_loop and main_event_loop.is_running():
        # log.info(f"Broadcasting MQTT status: {mqtt_connection_statuses}") # Reduced verbosity
        asyncio.run_coroutine_threadsafe(
            websocket_holder.broadcast({"type": "mqtt_status_update", "data": {"statuses": mqtt_connection_statuses}}),
            main_event_loop
        )
    else:
        log.warning("Cannot broadcast MQTT status: Main event loop not available or not running.")


## mqtt client 连接配置文件中的 broker成功后, 并按要求订阅 topic
def on_connect(client, userdata, flags, rc):
    """Callback when connected to MQTT Broker."""
    global runtime_cfg, mqtt_connection_statuses, is_mqtt_intentionally_disconnected, main_event_loop
    
    # Get the data source type from userdata (we'll set this when creating the client)
    source_type = userdata.get('source_type', 'unknown') if userdata else 'unknown'
    
    if rc == 0:
        log.info(f"MQTT Broker: Connected to {source_type}!")
        mqtt_connection_statuses[source_type] = "connected"
        is_mqtt_intentionally_disconnected = False  # Clear flag on successful connect
        
        # Subscribe based on source type
        if runtime_cfg:
            mqtt_config = None
            if source_type == 'sensecap' and hasattr(runtime_cfg, 'sensecapOpenStream'):
                mqtt_config = runtime_cfg.sensecapOpenStream
            elif source_type == 'chirpstack' and hasattr(runtime_cfg, 'chirpStackMqtt'):
                mqtt_config = runtime_cfg.chirpStackMqtt
            
            if mqtt_config and mqtt_config.topicPattern and mqtt_config.applicationID:
                try:
                    topic = mqtt_config.topicPattern.format(ApplicationID=mqtt_config.applicationID)
                    client.subscribe(topic)
                    log.info(f"Subscribed to {source_type} topic: {topic}")
                except KeyError as e:
                    log.error(f"Error formatting {source_type} MQTT topicPattern. Ensure 'ApplicationID' is a valid key: {e}")
                except Exception as e:
                    log.error(f"Error during {source_type} MQTT subscription: {e}")
            else:
                log.error(f"{source_type} MQTT configuration (topicPattern or applicationID) missing in runtime_cfg. Cannot subscribe.")
    else:
        log.error(f"MQTT Broker: Failed to connect to {source_type}, return code {rc}")
        mqtt_connection_statuses[source_type] = "error"
        
    if main_event_loop and main_event_loop.is_running():
        asyncio.run_coroutine_threadsafe(broadcast_mqtt_status(), main_event_loop)
    else:
        log.warning("on_connect: Main event loop not available for broadcasting MQTT status.")


## 断开后输出日志, main eventloop 还在运行则广播 mqtt 状态
def on_disconnect(client, userdata, rc):
    """Callback for when the client disconnects from the MQTT Broker."""
    global mqtt_connection_statuses, is_mqtt_intentionally_disconnected, runtime_cfg, main_event_loop
    
    # Get the data source type from userdata
    source_type = userdata.get('source_type', 'unknown') if userdata else 'unknown'
    
    if rc == 0 and is_mqtt_intentionally_disconnected:
        log.info(f"MQTT Broker: Disconnected gracefully from {source_type} by user request.")
        mqtt_connection_statuses[source_type] = "disconnected"
    elif rc == 0:
        log.info(f"MQTT Broker: Disconnected gracefully from {source_type} (not by direct user request).")
        mqtt_connection_statuses[source_type] = "disconnected"
    else:
        log.error(f"MQTT Broker: Unexpected disconnection from {source_type}, return code {rc}.")
        mqtt_connection_statuses[source_type] = "error"

    # Schedule broadcast_mqtt_status on the main event loop
    if main_event_loop and main_event_loop.is_running():
        asyncio.run_coroutine_threadsafe(broadcast_mqtt_status(), main_event_loop)
    else:
        log.warning("on_disconnect: Main event loop not available for broadcasting MQTT status.")


## 创建 mqtt client 连接到 broker
def _initialize_mqtt_client(source_type: str, mqtt_config: MqttServerConfig):
    """Creates and configures an MQTT client instance for a specific data source."""
    if not mqtt_config:
        log.warning(f"MQTT configuration not available for {source_type} client initialization.")
        return None
        
    code = random.randint(100000, 999999)
    if not mqtt_config.clientID:
        mqtt_config.clientID = "client-{clientID}"
    client_id = mqtt_config.clientID.replace("{clientID}", str(code)) if mqtt_config.clientID else f"{source_type}_client_{code}"
    
    try:
        new_client = mqtt.Client(client_id=client_id)

        if mqtt_config.username and mqtt_config.password:
            new_client.username_pw_set(mqtt_config.username, mqtt_config.password)

        # Set userdata to identify the source type in callbacks
        new_client.user_data_set({"source_type": source_type})
        
        new_client.on_connect = on_connect
        new_client.on_disconnect = on_disconnect
        new_client.on_message = on_message
        
        log.info(f"Initialized {source_type} MQTT client: {client_id}")
        return new_client
    except Exception as e:
        log.error(f"Error initializing {source_type} MQTT client: {e}", exc_info=True)
        return None


## 初始化所有 MQTT 客户端
def _initialize_all_mqtt_clients():
    """Initialize MQTT clients for all configured data sources."""
    global mqtt_clients, runtime_cfg
    
    if not runtime_cfg:
        log.warning("Runtime configuration not available for MQTT client initialization.")
        return
    
    # Initialize SenseCAP OpenStream client
    if hasattr(runtime_cfg, 'sensecapOpenStream') and runtime_cfg.sensecapOpenStream.enabled:
        sensecap_client = _initialize_mqtt_client('sensecap', runtime_cfg.sensecapOpenStream)
        if sensecap_client:
            mqtt_clients['sensecap'] = sensecap_client
        else:
            mqtt_clients['sensecap'] = None
    
    # Initialize ChirpStack client  
    if hasattr(runtime_cfg, 'chirpStackMqtt') and runtime_cfg.chirpStackMqtt.enabled:
        chirpstack_client = _initialize_mqtt_client('chirpstack', runtime_cfg.chirpStackMqtt)
        if chirpstack_client:
            mqtt_clients['chirpstack'] = chirpstack_client
        else:
            mqtt_clients['chirpstack'] = None


## 连接单个 MQTT 客户端
def _connect_mqtt_client(source_type: str):
    """Attempts to connect a specific MQTT client to its broker."""
    global mqtt_clients, runtime_cfg, mqtt_connection_statuses, is_mqtt_intentionally_disconnected, main_event_loop

    if source_type not in mqtt_clients or mqtt_clients[source_type] is None:
        log.warning(f"MQTT client for {source_type} not initialized.")
        mqtt_connection_statuses[source_type] = "error"
        return False

    client = mqtt_clients[source_type]
    mqtt_config = None
    
    if source_type == 'sensecap' and hasattr(runtime_cfg, 'sensecapOpenStream'):
        mqtt_config = runtime_cfg.sensecapOpenStream
    elif source_type == 'chirpstack' and hasattr(runtime_cfg, 'chirpStackMqtt'):
        mqtt_config = runtime_cfg.chirpStackMqtt

    if not mqtt_config or not mqtt_config.brokerHost:
        log.warning(f"{source_type} MQTT brokerHost not configured. Cannot connect.")
        mqtt_connection_statuses[source_type] = "misconfigured"
        return False

    current_status = mqtt_connection_statuses.get(source_type, "disconnected")
    if current_status == "connected" or current_status == "connecting":
        # log.info(f"{source_type} MQTT client already {current_status}. No action needed.") # Can be noisy
        return True

    try:
        # log.info(f"Attempting to connect {source_type} MQTT client to {mqtt_config.brokerHost}...") # Reduced verbosity
        is_mqtt_intentionally_disconnected = False  # Clear flag before attempting connection
        mqtt_connection_statuses[source_type] = "connecting"
        
        if main_event_loop and main_event_loop.is_running():
            asyncio.run_coroutine_threadsafe(broadcast_mqtt_status(), main_event_loop)

        client.connect_async(mqtt_config.brokerHost, mqtt_config.brokerPort, 60)
        client.loop_start()  # loop_start is non-blocking and handles reconnects.
        log.info(f"{source_type} MQTT brokerHost is listening....")
        # Status will be updated by on_connect or on_disconnect callbacks
        return True
    except Exception as e:
        log.error(f"Error during {source_type} MQTT connect_async or loop_start: {e}", exc_info=True)
        mqtt_connection_statuses[source_type] = "error"
        if main_event_loop and main_event_loop.is_running():
            asyncio.run_coroutine_threadsafe(broadcast_mqtt_status(), main_event_loop)
        return False


## 连接所有 MQTT 客户端
def _connect_all_mqtt_clients():
    """Attempts to connect all initialized MQTT clients."""
    global mqtt_clients
    
    for source_type in mqtt_clients.keys():
        if mqtt_clients[source_type] is not None:
            _connect_mqtt_client(source_type)


def disconnect_mqtt_client(source_type: str = None, broadcast=True):
    """Disconnects MQTT client(s). If source_type is None, disconnects all clients."""
    global mqtt_clients, mqtt_connection_statuses, is_mqtt_intentionally_disconnected, main_event_loop
    is_mqtt_intentionally_disconnected = True
    
    clients_to_disconnect = []
    if source_type:
        if source_type in mqtt_clients and mqtt_clients[source_type]:
            clients_to_disconnect = [(source_type, mqtt_clients[source_type])]
    else:
        clients_to_disconnect = [(st, client) for st, client in mqtt_clients.items() if client is not None]
    
    for st, client in clients_to_disconnect:
        try:
            # log.info(f"Disconnecting {st} MQTT client...") # Reduced verbosity
            client.loop_stop()
            client.disconnect()
            
            # Ensure status is set if on_disconnect isn't triggered as expected
            if mqtt_connection_statuses.get(st) != "disconnected":
                mqtt_connection_statuses[st] = "disconnected"
                
        except Exception as e:
            log.error(f"Error disconnecting {st} MQTT client: {e}", exc_info=True)
            mqtt_connection_statuses[st] = "error"
    
    if broadcast:
        if main_event_loop and main_event_loop.is_running():
            asyncio.run_coroutine_threadsafe(broadcast_mqtt_status(), main_event_loop)
        else:
            log.warning("disconnect_mqtt_client: Main event loop not available for broadcasting MQTT status.")


def disconnect_all_mqtt_clients(broadcast=True):
    """Disconnects all MQTT clients."""
    disconnect_mqtt_client(None, broadcast)


## 检查配置并连接 mqtt broker
def setup_mqtt(force_reconnect: bool = False):
    """Initializes and connects MQTT clients for all enabled data sources."""
    global mqtt_clients, runtime_cfg, mqtt_connection_statuses, main_event_loop, is_mqtt_intentionally_disconnected

    # Ensure runtime_cfg is loaded
    if not runtime_cfg:
        log.warning("Server runtime configuration not loaded. Cannot setup MQTT.")
        mqtt_connection_statuses.clear()
        mqtt_connection_statuses['general'] = "misconfigured"
        if main_event_loop and main_event_loop.is_running():
            asyncio.run_coroutine_threadsafe(broadcast_mqtt_status(), main_event_loop)
        else:
            log.warning("setup_mqtt: Main event loop not available for broadcasting MQTT status for no runtime_cfg.")
        return

    log.info("MQTT setup called. Checking for enabled data sources...")

    if is_mqtt_intentionally_disconnected and not force_reconnect:
        log.info("MQTT was intentionally disconnected. Not reconnecting automatically unless forced.")
        return

    # Initialize all MQTT clients
    _initialize_all_mqtt_clients()

    # Connect all initialized clients
    _connect_all_mqtt_clients()


# This is the new on_message callback
def on_message(client, userdata, msg):
    global main_event_loop, rt_cfg  # Access the main event loop
    source_type = userdata.get('source_type', 'unknown') if userdata else 'unknown'
    if main_event_loop and main_event_loop.is_running():
        try:
            future = asyncio.run_coroutine_threadsafe(
                uplink_consumer.do(msg.topic, msg.payload, source_type), main_event_loop
            )
            future.add_done_callback(
                lambda f: log.error(
                    f"Error in topic {msg.topic} from {source_type}, error:\n  {f.exception()}, \nmessage:\n  {msg.payload}")
                if f.exception() else None
            )
        except Exception as e:
            log.error(
                f"Failed in topic {msg.topic} from {source_type}from {source_type}: {e}",
                exc_info=True)

    # global main_event_loop, rt_cfg  # Access the main event loop
    # source_type = userdata.get('source_type', 'unknown') if userdata else 'unknown'
    # report = message_formatter.do(msg.topic, msg.payload, source_type)
    # if report:
    #
    #     device_eui = report.trackerId
    #     if not rt_cfg.allow_all_tracker and device_eui not in allow_tracker_list:
    #         log.debug(f"the device: {device_eui} not in allow_list, ignore this message.")
    #         return
    #     if main_event_loop and main_event_loop.is_running():
    #         try:
    #             future = asyncio.run_coroutine_threadsafe(process_tracker_report(report), main_event_loop)
    #             future.add_done_callback(
    #                 lambda f: log.error(f"Error in process_tracker_report for device {report.trackerId} from {source_type}, error:\n  {f.exception()}, \nreport:\n   {report}")
    #                 if f.exception() else None
    #             )
    #         except Exception as e:
    #             log.error(f"Failed to schedule process_tracker_report for device {report.trackerId} from {source_type}: {e}", exc_info=True)
    #     else:
    #         log.error(
    #             "Main asyncio event loop not available or not running. Cannot schedule tracker report processing.")
    # else:
    #     log.warning(f"Failed to parse payload or no report generated from {source_type} topic {msg.topic}")



# ## 计算定位结果
# async def process_tracker_report(report: TrackerReport):
#     """Processes a parsed tracker report to calculate position and update state."""
#     # Use new global config variables
#     global runtime_cfg, dashboard_cfg
#
#     if not runtime_cfg:
#         log.warning("Server runtime configuration not loaded, cannot process tracker report for Kalman params.")
#         return
#
#     message_listener.pre_listener(report)
#     latest_state = position_resolver.do(report)
#     log.info(f"tracker(id: {report.trackerId}) location resolving done, state: \n {latest_state}")
#     await message_listener.post_listener(latest_state)
#     await event_consumer.message_handle(latest_state)


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
    global miniprogram_cfg, runtime_cfg, main_event_loop, dashboard_cfg

    # Capture the running event loop for thread-safe calls from MQTT callback
    main_event_loop = asyncio.get_running_loop()

    log.info("Server startup sequence initiated.")

    # Load server runtime configuration first as it might be needed by other components
    runtime_cfg = config_manager.load_server_runtime_config()
    config_manager.load_miniprogram_config()
    dashboard_cfg = config_manager.get_dashboard_config()
    if not runtime_cfg:
        log.error(
            "Critical: Server runtime configuration could not be loaded. MQTT and other services might not start.")
        # Depending on desired behavior, could raise an exception or proceed with limited functionality
    else:
        log.info(f"Server runtime configuration loaded. MQTT enabled: {runtime_cfg}")

    # Load miniprogram configuration
    miniprogram_cfg = config_manager.load_miniprogram_config()
    if not miniprogram_cfg:
        log.warning(
            "Miniprogram configuration (map_beacon_config.json) not found or failed to load. Positioning may be affected.")
    else:
        # log.info("Miniprogram configuration (map_beacon_config.json) loaded.") # Reduced verbosity
        pass

    devices = device_dao.get_all_device()

    if devices and len(devices) > 0:
        for device in devices:
            device_holder.set_tracker_state(device.dev_eui, TrackerState.toTrackerState(device))
        log.info("tracker list has been loaded successfully when startup...")
    else:
        log.info("there is no tracker need to load in application when startup...")

    # Initialize event manager
    try:
        event_manager.initialize()
        log.info("Event manager initialized successfully during startup.")
    except Exception as e:
        log.error(f"Failed to initialize event manager during startup: {e}", exc_info=True)

    # Check if any MQTT sources are enabled and setup accordingly
    any_mqtt_enabled = False
    if runtime_cfg:
        if hasattr(runtime_cfg, 'sensecapOpenStream') and runtime_cfg.sensecapOpenStream.enabled:
            any_mqtt_enabled = True
        if hasattr(runtime_cfg, 'chirpStackMqtt') and runtime_cfg.chirpStackMqtt.enabled:
            any_mqtt_enabled = True
    
    if any_mqtt_enabled:
        setup_mqtt()  # Initialize and connect MQTT clients
    else:
        log.info("No MQTT data sources enabled in server runtime configuration. Skipping MQTT setup.")
        global mqtt_connection_statuses
        mqtt_connection_statuses = {"general": "disabled"}
        await broadcast_mqtt_status()  # Inform clients that MQTT is disabled

    # 清理过期的会话记录
    # try:
    #     cleaned_count = session_holder.cleanup_expired_sessions()
    #     log.info(f"Server startup: Cleaned {cleaned_count} expired sessions from database.")
    # except Exception as e:
    #     log.warning(f"Failed to cleanup expired sessions on startup: {e}")

    asyncio.create_task(device_offline_checker.do())
    asyncio.create_task(event_trigger.position_detection_task())
    log.info("Server startup complete.")


async def graceful_shutdown():
    """Performs graceful shutdown operations."""
    global mqtt_clients, shutdown_flag
    
    log.info("Initiating graceful shutdown...")
    shutdown_flag = True
    
    # Disconnect all MQTT clients
    disconnect_all_mqtt_clients(broadcast=False)
    
    # Close all WebSocket connections
    await websocket_holder.close_all_connections(
        code=1000, 
        reason="Server is shutting down gracefully"
    )
    
    log.info("Graceful shutdown operations completed.")


@app.on_event("shutdown")
async def shutdown_event():
    """Runs on application shutdown."""
    global mqtt_clients
    log.info("Application shutdown...")
    for source_type, client in mqtt_clients.items():
        if client and client.is_connected():
            client.loop_stop()
            client.disconnect()
            log.info(f"{source_type} MQTT client disconnected.")

    if device_holder.get_tracker_count() > 0:
        devices = device_dao.get_active_devices()[0]
        devices_map = {}
        if devices and len(devices) > 0:
            devices_map = {device.dev_eui: device for device in devices}

        for tracker_id, tracker_state in device_holder.get_all_tracker_states().items():
            if tracker_id in devices_map:
                device_dao.update_device_status(
                    dev_eui=tracker_id,
                    battery_level=tracker_state.battery,
                    last_message_timestamp_ms=tracker_state.last_update_time
                )
        log.info("the tracker state has been saved successfully when shutdown...")
    else:
        log.info("there is no tracker need to save in app when shutdown...")
    log.info("Application shutdown complete.")


# --- API Endpoints ---
def check_authority(request: Request):
    # session_token = request.cookies.get('session_token')
    session_token = request.headers.get("session_token")
    if not session_token:
        raise HTTPException(status_code=401, detail="No session token")
    if not session_holder.get(session_token):
        raise HTTPException(status_code=401, detail="Invalid session token")
    user_session = session_holder.get(session_token)
    if user_session.role == 'guest':
        log.info(f"guest has been deny to access interface: {request.url.path}")
        raise HTTPException(status_code=403, detail="Unauthorized")


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
async def upload_miniprogram_config(config_content: MiniprogramConfig, response: Response, dep=Depends(check_authority)):
    """Receives miniprogram config JSON, saves it, and reloads.
       The request body should be the JSON content matching MiniprogramConfig model.
    """
    global miniprogram_cfg
    # log.info("Received request to upload miniprogram configuration.") # Reduced verbosity
    try:
        # config_content is already parsed by FastAPI into MiniprogramConfig model
        if config_manager.save_miniprogram_config(config_content):
            miniprogram_cfg = config_manager.get_miniprogram_config()  # Reload and update global cache
            log.info("Miniprogram configuration uploaded and reloaded successfully.")
            # Broadcast update to WebSocket clients
            await websocket_holder.broadcast(
                {"type": "config_update", "data": miniprogram_cfg.model_dump() if miniprogram_cfg else {}})
            return {"message": "Miniprogram configuration uploaded successfully."}
        else:
            raise HTTPException(status_code=500, detail="Failed to save miniprogram configuration.")
    except Exception as e:  # Catch any other unexpected errors
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


## 接收任意dev_eui 仅用于debug
@app.post("/api/debug/tracker_report")
async def push_sos(report: TrackerReport):
    report.timestamp = int(time.time()) * 1000
    if main_event_loop and main_event_loop.is_running():
        # asyncio.run_coroutine_threadsafe(process_tracker_report(report), main_event_loop)
        asyncio.run_coroutine_threadsafe(uplink_consumer.do_for_tracker_report(report), main_event_loop)


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
async def get_trackers(request: TrackerStateQueryRequest = None):
    """Returns the current state of all known trackers."""
    devices = device_dao.get_active_devices()[0]
    if not devices or len(devices) == 0:
        return {}
        # devices_map = {device.dev_eui: device for device in devices}

    result = {}
    for device in devices:
        tracker_state = device_holder.get_tracker_state(device.dev_eui)
        choose_state = {}
        match = True
        if tracker_state is None:
            choose_state = TrackerInfo.fromDeviceRecord(device)
        else:
            choose_state = tracker_state.toTrackerInfo(device)
        if request is not None and request.online_status is not None:
            match = (request.online_status == choose_state.online)
        if request is not None and request.is_favorite is not None:
            match = (request.is_favorite == choose_state.is_favorite)
        if request is not None and request.dev_eui_list and len(request.dev_eui_list) > 0:
            match = (choose_state.trackerId in request.dev_eui_list)
        if match:
            result[device.dev_eui] = choose_state
    return result
    # return tracker_states

@app.get("/api/beacons")
async def get_beacons() -> dict[str, list[WebUIBeaconConfig]]:
    all_beacon_by_map = beacon_holder.get_all_beacon_by_map()
    return all_beacon_by_map


@app.get("/api/server-runtime-config", response_model=Optional[config_manager.ServerRuntimeConfig])
async def get_api_server_runtime_config():
    global runtime_cfg, mqtt_connection_statuses  # Ensure mqtt_connection_statuses is accessible
    # Ensure runtime_cfg is loaded
    if runtime_cfg is None:
        config_manager.load_server_runtime_config()  # Attempt to load if not already loaded by startup

    if runtime_cfg:
        # Create a copy to avoid modifying the global cache directly with transient status
        config_to_send = runtime_cfg.model_copy(deep=True)
        
        # Handle SenseCAP OpenStream
        if hasattr(config_to_send, 'sensecapOpenStream') and config_to_send.sensecapOpenStream:
            # Mask password before sending to client
            if config_to_send.sensecapOpenStream.password:
                config_to_send.sensecapOpenStream.password = config_manager.PASSWORD_PLACEHOLDER
            # Add live status
            config_to_send.sensecapOpenStream.live_mqtt_status = mqtt_connection_statuses.get('sensecap', 'disconnected')
        
        # Handle ChirpStack MQTT
        if hasattr(config_to_send, 'chirpStackMqtt') and config_to_send.chirpStackMqtt:
            # Mask password before sending to client
            if config_to_send.chirpStackMqtt.password:
                config_to_send.chirpStackMqtt.password = config_manager.PASSWORD_PLACEHOLDER
            # Add live status
            config_to_send.chirpStackMqtt.live_mqtt_status = mqtt_connection_statuses.get('chirpstack', 'disconnected')
        
        # Legacy MQTT handling (for backward compatibility)
        if hasattr(config_to_send, 'mqtt') and config_to_send.mqtt:
            if config_to_send.mqtt.password:
                config_to_send.mqtt.password = config_manager.PASSWORD_PLACEHOLDER
            config_to_send.mqtt.live_mqtt_status = mqtt_connection_statuses.get('legacy', 'disconnected')
                
        return config_to_send
    return None


@app.post("/api/server-runtime-config", status_code=200)
async def update_api_server_runtime_config(config_payload: PartialServerRuntimeConfig, dep=Depends(check_authority)):
    global runtime_cfg, mqtt_clients, mqtt_connection_statuses, is_mqtt_intentionally_disconnected, main_event_loop
    try:
        # log.info("Received request to update server runtime configuration.") # Reduced verbosity

        # Determine if MQTT settings that require reconnect have changed for each data source
        sources_to_reconnect = set()
        
        # Check SenseCAP OpenStream changes
        if (runtime_cfg and hasattr(runtime_cfg, 'sensecapOpenStream') and 
            config_payload.sensecapOpenStream is not None):
            old_sensecap = runtime_cfg.sensecapOpenStream
            new_sensecap = config_payload.sensecapOpenStream
            if (old_sensecap.brokerHost != new_sensecap.brokerHost or
                old_sensecap.brokerPort != new_sensecap.brokerPort or
                old_sensecap.username != new_sensecap.username or
                (new_sensecap.password != config_manager.PASSWORD_PLACEHOLDER and
                 new_sensecap.password is not None and
                 old_sensecap.password != new_sensecap.password) or
                old_sensecap.clientID != new_sensecap.clientID or
                old_sensecap.applicationID != new_sensecap.applicationID or
                old_sensecap.topicPattern != new_sensecap.topicPattern or
                old_sensecap.enabled != new_sensecap.enabled):
                sources_to_reconnect.add('sensecap')
        
        # Check ChirpStack changes
        if (runtime_cfg and hasattr(runtime_cfg, 'chirpStackMqtt') and 
            config_payload.chirpStackMqtt is not None):
            old_chirpstack = runtime_cfg.chirpStackMqtt
            new_chirpstack = config_payload.chirpStackMqtt
            if (old_chirpstack.brokerHost != new_chirpstack.brokerHost or
                old_chirpstack.brokerPort != new_chirpstack.brokerPort or
                old_chirpstack.username != new_chirpstack.username or
                (new_chirpstack.password != config_manager.PASSWORD_PLACEHOLDER and
                 new_chirpstack.password is not None and
                 old_chirpstack.password != new_chirpstack.password) or
                old_chirpstack.clientID != new_chirpstack.clientID or
                old_chirpstack.applicationID != new_chirpstack.applicationID or
                old_chirpstack.topicPattern != new_chirpstack.topicPattern or
                old_chirpstack.enabled != new_chirpstack.enabled):
                sources_to_reconnect.add('chirpstack')

        # Save the new configuration using partial update method
        success, new_cfg = config_manager.save_partial_server_runtime_config(config_payload)
        if success and new_cfg:
            runtime_cfg = new_cfg  # Update global runtime_cfg with the effectively saved one
            log.info("Server runtime configuration updated successfully.")

            # Handle reconnect for changed data sources
            for source_type in sources_to_reconnect:
                log.info(f"{source_type} MQTT configuration changed that requires reconnect.")
                
                # Disconnect existing client if connected
                current_status = mqtt_connection_statuses.get(source_type, "disconnected")
                if current_status in ["connected", "connecting"]:
                    disconnect_mqtt_client(source_type, broadcast=False)
                
                # Check if the source should be enabled
                source_config = None
                if source_type == 'sensecap' and hasattr(new_cfg, 'sensecapOpenStream'):
                    source_config = new_cfg.sensecapOpenStream
                elif source_type == 'chirpstack' and hasattr(new_cfg, 'chirpStackMqtt'):
                    source_config = new_cfg.chirpStackMqtt
                
                if source_config and source_config.enabled and source_config.brokerHost:
                    # Re-initialize and connect
                    is_mqtt_intentionally_disconnected = False
                    if source_type == 'sensecap':
                        mqtt_clients['sensecap'] = _initialize_mqtt_client('sensecap', source_config)
                        if mqtt_clients['sensecap']:
                            _connect_mqtt_client('sensecap')
                    elif source_type == 'chirpstack':
                        mqtt_clients['chirpstack'] = _initialize_mqtt_client('chirpstack', source_config)
                        if mqtt_clients['chirpstack']:
                            _connect_mqtt_client('chirpstack')
                else:
                    # Mark as disabled if not enabled or no broker host
                    mqtt_connection_statuses[source_type] = "disabled" if source_config and not source_config.enabled else "misconfigured"
                    
            if main_event_loop and main_event_loop.is_running():
                asyncio.run_coroutine_threadsafe(broadcast_mqtt_status(), main_event_loop)
                
            return {"message": "Server runtime configuration updated successfully."}
        else:
            log.error("Failed to save server runtime configuration to file.")
            raise HTTPException(status_code=500, detail="Failed to save server runtime configuration.")
    except Exception as e:
        log.error(f"Error updating server runtime config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/api/change-password", status_code=200)
async def change_password(password_request: PasswordChangeRequest, dep=Depends(check_authority)):
    """
    专用密码修改接口
    验证当前密码后更新为新密码
    """
    global runtime_cfg
    try:
        log.info(f"Password change request received for verification")
        
        # 验证密码并更新
        success, message, new_cfg = config_manager.verify_and_change_password(password_request)
        
        if success and new_cfg:
            # 更新全局配置缓存
            runtime_cfg = new_cfg
            log.info("Password changed successfully")
            
            return {
                "success": True,
                "message": message
            }
        else:
            # 密码验证失败或更新失败
            log.warning(f"Password change failed: {message}")
            
            # 根据错误类型返回不同的HTTP状态码
            if "incorrect" in message.lower():
                # 当前密码错误 - 401 Unauthorized
                raise HTTPException(status_code=401, detail=message)
            elif "same" in message.lower() or "different" in message.lower():
                # 新密码与当前密码相同 - 400 Bad Request
                raise HTTPException(status_code=400, detail=message)
            elif "characters" in message.lower():
                # 密码长度不符合要求 - 400 Bad Request  
                raise HTTPException(status_code=400, detail=message)
            else:
                # 其他服务器错误 - 500 Internal Server Error
                raise HTTPException(status_code=500, detail=message)
                
    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        log.error(f"Unexpected error during password change: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# @app.post("/api/set-service-credentials", status_code=200)
# async def set_service_credentials(credentials_request: ServiceCredentialsRequest):
#     """
#     专用服务凭证设置接口
#     安全地设置各种服务的用户名和密码，不会将密码存储在可提交的配置文件中
#     支持的服务类型: sensecap, chirpstack, webhook
#     """
#     global runtime_cfg
#     try:
#         log.info(f"Service credentials setting request received for service: {credentials_request.service_type}")
#
#         # 设置服务凭证
#         success, message, new_cfg = config_manager.set_service_credentials(credentials_request)
#
#         if success and new_cfg:
#             # 更新全局配置缓存
#             runtime_cfg = new_cfg
#             log.info(f"Service credentials set successfully for: {credentials_request.service_type}")
#
#             return {
#                 "success": True,
#                 "message": message,
#                 "service_type": credentials_request.service_type
#             }
#         else:
#             # 设置失败
#             log.warning(f"Service credentials setting failed: {message}")
#             raise HTTPException(status_code=400, detail=message)
#
#     except HTTPException:
#         # 重新抛出HTTP异常
#         raise
#     except Exception as e:
#         log.error(f"Unexpected error during service credentials setting: {e}", exc_info=True)
#         raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/api/login", status_code=200)
async def login(login_request: LoginRequest, response: Response):
    """
    用户登录接口
    接收用户名和MD5计算后的密码摘要，验证通过后返回httponly cookie
    """
    global runtime_cfg
    try:
        log.info(f"Login request received for username: {login_request.username}")

        if login_request.username == 'guest':
            # ca2d140c362dfd56acab2fdbd56ff5a5 访客模式默认密码: indoor_positioning  目前不校验
            user_session = UserSessionInfo(username="guest", role="guest")
        else:
            # 验证用户名
            if runtime_cfg.username != login_request.username:
                log.warning(f"Login failed: invalid username '{login_request.username}'")
                raise HTTPException(status_code=401, detail="用户名或密码错误")

            # 计算配置中密码的MD5摘要
            config_password_md5 = hashlib.md5(runtime_cfg.password.encode('utf-8')).hexdigest()

            # 验证MD5密码摘要
            if config_password_md5 != login_request.password.lower():
                log.warning(f"Login failed: invalid password for username '{login_request.username}'")
                raise HTTPException(status_code=401, detail="用户名或密码错误")
            user_session = UserSessionInfo(username="admin", role="admin")

        # 生成登录令牌 (简单的session token)
        import secrets
        session_token = secrets.token_urlsafe(32)
        session_holder.set(session_token, user_session, username=login_request.username)
        
        # 设置httponly cookie，有效期1天
        # response.set_cookie(
        #     key="session_token",
        #     value=session_token,
        #     max_age=86400 * 15,  # 1天 (24小时 * 60分钟 * 60秒)
        #     httponly=True,
        #     secure=False,  # 允许HTTP，如果需要HTTPS可以设为True
        #     samesite="lax"
        # )
        log.info(f"Login successful for username: {login_request.username}")
        return {
            "success": True,
            "message": "登录成功",
            "username": login_request.username,
            "data": {
                "token": session_token
            }
        }
        
    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        log.error(f"Unexpected error during login: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/auth/check", status_code=200)
async def check_auth(request: Request, response: Response):
    """
    检查当前用户的登录状态
    """
    try:
        # session_token = request.cookies.get('session_token')
        session_token = request.headers.get("session_token")
        if session_token and session_holder.get(session_token):
            return {
                "success": True,
                "message": "登录成功",
                "username": session_holder.get(session_token).username
            }
        # 2025-09-23
        import secrets
        session_token = secrets.token_urlsafe(32)
        user_session = UserSessionInfo(username="guest", role="guest")
        session_holder.set(session_token, user_session, username="guest")

        # 设置httponly cookie，有效期1天
        # response.set_cookie(
        #     key="session_token",
        #     value=session_token,
        #     max_age=86400 * 15,  # 1天 (24小时 * 60分钟 * 60秒)
        #     httponly=True,
        #     secure=False,  # 允许HTTP，如果需要HTTPS可以设为True
        #     samesite="lax"
        # )
        log.info(f"Login successful for username: guest")
        return {
            "success": True,
            "message": "登录成功",
            "username": "guest",
            "data": {
                "token": session_token
            }
        }


        # if not session_token:
        #     raise HTTPException(status_code=401, detail="No session token")
        #
        # if not session_holder.get(session_token):
        #     raise HTTPException(status_code=401, detail="Invalid session token")
        #
        # return {
        #     "authenticated": True,
        #     "message": "用户已登录"
        # }
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error checking auth status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/api/auth/logout", status_code=200) 
async def logout(request: Request, response: Response):
    """
    用户登出接口
    清除session token和cookie
    """
    try:
        # session_token = request.cookies.get('session_token')
        session_token = request.headers.get("session_token")
        if session_token:
            session_holder.remove(session_token)
        
        # 清除cookie
        # response.delete_cookie(
        #     key="session_token",
        #     httponly=True,
        #     secure=False,
        #     samesite="lax"
        # )
        
        return {
            "success": True,
            "message": "登出成功"
        }
        
    except Exception as e:
        log.error(f"Error during logout: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.middleware("http")
async def auth_middleware(request: Request, next):
    if request.method == "OPTIONS":
        return await next(request)
    # 允许访问的公开路径
    public_paths = ['/api/login', '/api/auth/check', '/ws', '/login', '/']
    
    # 检查是否为静态文件或公开API
    if (request.url.path in public_paths or 
        request.url.path.startswith('/static/') or
        request.url.path.startswith('/assets/')):
        return await next(request)
    
    # 对于API路径，检查认证状态
    if request.url.path.startswith('/api/'):
        # session_token = request.cookies.get('session_token')
        session_token = request.headers.get("session_token")
        if not session_token:
            return JSONResponse(status_code=401, content={"detail": "No session token"})

        if not session_holder.get(session_token):
            return JSONResponse(status_code=401, content={"detail": "Invalid or expired session"})
    
    return await next(request)


@app.get("/api/mqtt-status")
async def get_mqtt_connection_status():
    return {"statuses": mqtt_connection_statuses}


@app.post("/api/mqtt/connect", status_code=200)
async def api_mqtt_connect():
    global runtime_cfg, mqtt_connection_statuses, is_mqtt_intentionally_disconnected, main_event_loop
    # log.info("API call to connect MQTT.") # Reduced verbosity

    # Reload runtime_cfg to ensure latest settings are used for connection attempt
    current_runtime_cfg = config_manager.load_server_runtime_config()
    if not current_runtime_cfg:
        log.warning("MQTT Connect API: Runtime configuration not found.")
        raise HTTPException(status_code=400, detail="Runtime configuration not available.")

    runtime_cfg = current_runtime_cfg  # Update global runtime_cfg

    # Check if any MQTT sources are configured and enabled
    any_enabled = False
    if (hasattr(runtime_cfg, 'sensecapOpenStream') and runtime_cfg.sensecapOpenStream.enabled):
        any_enabled = True
    if (hasattr(runtime_cfg, 'chirpStackMqtt') and runtime_cfg.chirpStackMqtt.enabled):
        any_enabled = True
        
    if not any_enabled:
        raise HTTPException(status_code=400, detail="No MQTT data sources are enabled in configuration.")

    is_mqtt_intentionally_disconnected = False  # User intends to connect

    # Attempt to setup/connect all enabled sources
    setup_mqtt(force_reconnect=True)

    # Give a slight delay for connection attempt to progress before returning status
    await asyncio.sleep(0.1)  # Small delay
    return {"message": "MQTT connection process initiated.", "current_statuses": mqtt_connection_statuses}


@app.post("/api/mqtt/disconnect", status_code=200)
async def api_mqtt_disconnect(dep=Depends(check_authority)):
    global mqtt_connection_statuses
    # log.info("API call to disconnect MQTT.") # Reduced verbosity
    disconnect_all_mqtt_clients()  # This function sets is_mqtt_intentionally_disconnected = True
    # Give a slight delay for disconnection to reflect
    await asyncio.sleep(0.1)
    return {"message": "MQTT disconnect process initiated.", "current_statuses": mqtt_connection_statuses}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Handles WebSocket connections."""
    success = await websocket_holder.connect(websocket, websocket_auth_handler)
    if not success:
        return
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
                    await websocket_holder.broadcast({"type": "info", "message": "Scanning started."})
                elif command == "stopScan":
                    log.info("Stop scan command received.")
                    # TODO: Implement logic to stop Bluetooth scanning here
                    # For now, send a confirmation that scan stopped.
                    await websocket_holder.broadcast({"type": "info", "message": "Scanning stopped."})
                elif message.get("action") == "request_initial_data":  # Example action, kept for now
                    # Send initial data if needed
                    await websocket_holder.broadcast({"type": "initial_data", "payload": "some_initial_state"})
                else:
                    log.warning(f"Unknown command/action received: {message}")
                    await websocket_holder.broadcast({"type": "error", "message": "Unknown command"})

            except json.JSONDecodeError:
                log.error(f"Error decoding JSON from WebSocket: {data}")
                await websocket_holder.broadcast({"type": "error", "message": "Error decoding JSON"})

    except WebSocketDisconnect:
        websocket_holder.disconnect(websocket)
    except Exception as e:
        log.error(f"WebSocket error for client {websocket.client}: {e}", exc_info=True)
        websocket_holder.disconnect(websocket)  # Ensure disconnect on error


@app.get("/api/configuration/dashboard", response_model=Optional[DashboardConfig])
async def get_dashboard_config():
    global dashboard_cfg
    if dashboard_cfg is None:
        dashboard_cfg = config_manager.get_dashboard_config()

    if dashboard_cfg:
        return dashboard_cfg
    else:
        log.warning("GET /api/configuration/dashboard: No Dashboard configuration available after load attempt.")
        return DashboardConfig(maps=None)  # Use direct model name


@app.post("/api/configuration/dashboard", status_code=200)
async def save_dashboard_config(config_content: DashboardConfig, response: Response, dep=Depends(check_authority)):
    """Saves the dashboard configuration to file and updates in-memory cache."""
    global dashboard_cfg
    try:
        if config_manager.save_dashboard_config_to_file(config_content):
            dashboard_cfg = config_content
            beacon_holder.update_by_dashboard_config(dashboard_cfg)
            log.info("Dashboard configuration successfully received and saved.")
            return {"message": "Dashboard configuration saved successfully."}
        else:
            raise HTTPException(status_code=500, detail="Failed to save Dashboard configuration to file.")
    except Exception as e:
        log.error(f"Error processing uploaded Dashboard configuration: {e}", exc_info=True)
        raise HTTPException(status_code=500,
                            detail=f"Internal server error while saving Dashboard configuration: {str(e)}")


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


@app.get("/api/map-example-format")  # New endpoint
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
async def update_allow_tracker_list(request: TrackerListUpdateRequest, dep=Depends(check_authority)):
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


# --- Group Management API ---

@app.post("/api/groups", status_code=200)
async def create_group(group_request: GroupCreateRequest, dep=Depends(check_authority)):
    """
    创建分组接口
    """
    try:
        # 检查分组名称是否已存在（不包括已删除的）
        if group_dao.group_name_exists(group_request.group_name, include_deleted=False):
            raise HTTPException(status_code=409, detail="分组名称已存在")
        
        # 创建分组
        group = group_dao.create_group(group_request.group_name)
        
        log.info(f"Created group: {group.group_name} (ID: {group.id})")
        return {
            "success": True,
            "message": "分组创建成功",
            "data": {
                "id": group.id,
                "group_name": group.group_name
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error creating group: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"创建分组失败: {str(e)}")


@app.get("/api/groups", response_model=List[GroupListItem])
async def get_groups():
    """
    获取分组列表接口（仅返回ID和名称，不包括已删除的）
    """
    try:
        # 获取所有未删除的分组
        groups, total = group_dao.get_active_groups(page=1, page_size=1000)  # 大页面大小获取所有
        
        # 转换为响应格式
        group_list = [
            GroupListItem(id=group.id, group_name=group.group_name) 
            for group in groups
        ]
        
        return group_list
        
    except Exception as e:
        log.error(f"Error getting groups: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取分组列表失败: {str(e)}")


@app.put("/api/groups/{group_id}", status_code=200)
async def update_group(group_id: int, group_request: GroupUpdateRequest, dep=Depends(check_authority)):
    """
    更新分组名称接口
    """
    try:
        # 检查分组是否存在
        existing_group = group_dao.get_by_id(group_id)
        if not existing_group or existing_group.is_deleted():
            raise HTTPException(status_code=404, detail="分组不存在或已被删除")
        
        # 检查新名称是否与其他分组重复（排除当前分组）
        if group_dao.group_name_exists(group_request.group_name, exclude_id=group_id, include_deleted=False):
            raise HTTPException(status_code=409, detail="分组名称已存在")
        
        # 更新分组名称
        updated_group = group_dao.update_group_name(group_id, group_request.group_name)
        
        if not updated_group:
            raise HTTPException(status_code=500, detail="更新分组失败")
        
        log.info(f"Updated group {group_id}: {existing_group.group_name} -> {updated_group.group_name}")
        return {
            "success": True,
            "message": "分组更新成功",
            "data": {
                "id": updated_group.id,
                "group_name": updated_group.group_name
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error updating group {group_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"更新分组失败: {str(e)}")


@app.delete("/api/groups/{group_id}", status_code=200)
async def delete_group(group_id: int, dep=Depends(check_authority)):
    """
    删除分组接口（软删除）
    """
    try:
        # 检查分组是否存在
        existing_group = group_dao.get_by_id(group_id)
        if not existing_group or existing_group.is_deleted():
            raise HTTPException(status_code=404, detail="分组不存在或已被删除")
        
        # 软删除分组
        deleted_group = group_dao.soft_delete_group(group_id)
        
        if not deleted_group:
            raise HTTPException(status_code=500, detail="删除分组失败")

        device_dao.update_devices_group(old_group_id=group_id, new_group_id=0)

        log.info(f"Soft deleted group {group_id}: {existing_group.group_name}")
        return {
            "success": True,
            "message": "分组删除成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error deleting group {group_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"删除分组失败: {str(e)}")


# --- Device Management API ---
@app.put("/api/devices/{dev_eui}", status_code=200)
async def update_device(dev_eui: str, device_request: DeviceUpdateRequest, dep=Depends(check_authority)):
    """
    更新设备信息接口
    """
    try:
        # 检查设备是否存在
        existing_device = device_dao.get_by_dev_eui(dev_eui)
        if not existing_device or existing_device.is_deleted():
            raise HTTPException(status_code=404, detail="设备不存在或已被删除")
        
        # 如果指定了分组ID，检查分组是否存在
        if device_request.group_id is not None and device_request.group_id > 0:
            group = group_dao.get_by_id(device_request.group_id)
            if not group or group.is_deleted():
                raise HTTPException(status_code=400, detail="指定的分组不存在")
        
        # 构建更新数据
        update_data = {}
        if device_request.device_name is not None:
            update_data["device_name"] = device_request.device_name
        if device_request.group_id is not None:
            update_data["group_id"] = device_request.group_id
        if device_request.is_favorite is not None:
            update_data["is_favorite"] = device_request.is_favorite
        
        if not update_data:
            raise HTTPException(status_code=400, detail="没有提供要更新的数据")
        
        # 更新设备
        updated_device = device_dao.update_device_info(dev_eui=dev_eui, **update_data)
        
        if not updated_device:
            raise HTTPException(status_code=500, detail="更新设备失败")
        
        log.info(f"Updated device {dev_eui}: {existing_device.device_name}")
        return {
            "success": True,
            "message": "设备更新成功",
            "data": {
                "dev_eui": dev_eui,
                "device_name": updated_device.device_name
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error updating device {dev_eui}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"更新设备失败: {str(e)}")


@app.post("/api/devices/search", response_model=List[DeviceListItem])
async def search_devices(search_request: DeviceSearchRequest, dep=Depends(check_authority)):
    """
    搜索设备接口
    """
    try:
        devices, total = device_dao.search_devices(
            search_request.keyword, 
            search_request.page, 
            search_request.page_size
        )
        
        # 转换为响应格式
        device_list = []
        for device in devices:
            device_item = DeviceListItem(
                id=device.id,
                dev_eui=device.dev_eui,
                device_name=device.device_name,
                group_id=device.group_id,
                is_online=device.is_online,
                is_favorite=device.is_favorite,
                battery_level=device.battery_level,
                create_time=device.create_time.isoformat() if device.create_time else "",
                last_data_update_time=device.last_data_update_time.isoformat() if device.last_data_update_time else None
            )
            device_list.append(device_item)
        
        return device_list
        
    except Exception as e:
        log.error(f"Error searching devices: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"搜索设备失败: {str(e)}")


@app.post("/api/devices/batch-update-group", status_code=200)
async def batch_update_devices_group(request: DeviceBatchUpdateGroupRequest, dep=Depends(check_authority)):
    """
    批量更新设备分组接口
    """
    try:
        # 检查分组是否存在（如果group_id > 0）
        if request.group_id > 0:
            group = group_dao.get_by_id(request.group_id)
            if not group or group.is_deleted():
                raise HTTPException(status_code=400, detail="指定的分组不存在")
        
        # 验证设备EUI列表不能为空
        if not request.dev_eui_list:
            raise HTTPException(status_code=400, detail="设备EUI列表不能为空")
        
        # 检查设备是否存在（可选，根据业务需求决定是否严格检查）
        existing_devices = []
        for dev_eui in request.dev_eui_list:
            device = device_dao.get_by_dev_eui(dev_eui)
            if device and not device.is_deleted():
                existing_devices.append(dev_eui)
        
        if not existing_devices:
            raise HTTPException(status_code=400, detail="没有找到有效的设备")
        
        # 执行批量更新
        updated_count = device_dao.batch_update_devices_group(existing_devices, request.group_id)
        
        log.info(f"Batch updated {updated_count} devices to group {request.group_id}: {existing_devices}")
        
        return {
            "success": True,
            "message": f"成功更新 {updated_count} 个设备的分组",
            "data": {
                "updated_count": updated_count,
                "group_id": request.group_id,
                "updated_devices": existing_devices
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error batch updating devices group: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"批量更新设备分组失败: {str(e)}")


# --- Event Trigger Management API ---

@app.post("/api/events", status_code=200)
async def create_event_trigger(event_request: EventTriggerCreateRequest):
    """
    创建事件触发条件接口
    """
    try:
        # 检查事件名称是否已存在
        if event_manager.get_cache_stats()["initialized"]:
            # 如果缓存已初始化，使用DAO检查
            from server.dao.event_trigger_dao import event_trigger_dao
            if event_trigger_dao.event_name_exists(event_request.event_name, include_deleted=False):
                raise HTTPException(status_code=400, detail="事件名称已存在")
        
        # 使用事件管理器创建事件
        event = event_manager.create_event(
            event_name=event_request.event_name,
            event_type=event_request.event_type,
            device_range=event_request.device_range,
            ble_range=event_request.ble_range,
            time_range=event_request.time_range,
            ble_rule=event_request.ble_rule,
            dis_range=event_request.dis_range,
            enable_status=event_request.enable_status
        )
        
        if not event:
            raise HTTPException(status_code=500, detail="创建事件失败")
        
        log.info(f"Created event trigger: {event.event_name} (ID: {event.id})")
        return {
            "success": True,
            "message": "事件创建成功",
            "data": {
                "id": event.id,
                "event_name": event.event_name,
                "event_type": event.event_type
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error creating event trigger: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"创建事件失败: {str(e)}")


@app.get("/api/events")
async def get_event_triggers(
        page: int = Query(1, ge=1),
        page_size: int = Query(20, ge=1, le=100)):
    """
    获取事件触发条件列表接口（分页）
    """
    try:
        from server.dao.event_trigger_dao import event_trigger_dao
        events, total = event_trigger_dao.get_active_event_triggers(page, page_size)
        
        # 转换为响应格式
        event_list = []
        for event in events:
            event_item = EventTriggerListItem(
                id=event.id,
                event_name=event.event_name,
                event_type=event.event_type,
                device_range=event.get_device_range_list(),
                ble_range=event.get_ble_range_list(),
                time_range=event.time_range,
                ble_rule=event.ble_rule,
                dis_range=event.dis_range,
                enable_status=event.enable_status,
                create_time=event.create_time.isoformat() if event.create_time else ""
            )
            event_list.append(event_item)
        
        # 计算总页数
        total_pages = (total + page_size - 1) // page_size
        
        return {
            "data": event_list,
            "pagination": {
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages
            }
        }
        
    except Exception as e:
        log.error(f"Error getting event triggers: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取事件列表失败: {str(e)}")

@app.get("/api/events/device/{dev_eui}")
async def get_event_by_device(dev_eui: str):
    try:
        list_alarm = event_manager.get_events_for_device(dev_eui)
        return list_alarm

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取设备事件失败: {str(e)}")


@app.get("/api/events/{event_id}", response_model=EventTriggerListItem)
async def get_event_trigger(event_id: int):
    """
    获取单个事件触发条件详情接口
    """
    try:
        from server.dao.event_trigger_dao import event_trigger_dao
        event = event_trigger_dao.get_by_id(event_id)
        
        if not event or event.is_deleted():
            raise HTTPException(status_code=404, detail="事件不存在或已被删除")
        
        return EventTriggerListItem(
            id=event.id,
            event_name=event.event_name,
            event_type=event.event_type,
            device_range=event.get_device_range_list(),
            ble_range=event.get_ble_range_list(),
            time_range=event.time_range,
            ble_rule=event.ble_rule,
            dis_range=event.dis_range,
            enable_status=event.enable_status,
            create_time=event.create_time.isoformat() if event.create_time else ""
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error getting event trigger {event_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取事件详情失败: {str(e)}")


@app.put("/api/events/{event_id}", status_code=200)
async def update_event_trigger(event_id: int, event_request: EventTriggerUpdateRequest, dep=Depends(check_authority)):
    """
    更新事件触发条件接口
    """
    try:
        from server.dao.event_trigger_dao import event_trigger_dao
        
        # 检查事件是否存在
        existing_event = event_trigger_dao.get_by_id(event_id)
        if not existing_event or existing_event.is_deleted():
            raise HTTPException(status_code=404, detail="事件不存在或已被删除")
        
        # 检查新名称是否与其他事件重复（如果提供了新名称）
        if event_request.event_name and event_request.event_name != existing_event.event_name:
            if event_trigger_dao.event_name_exists(event_request.event_name, exclude_id=event_id, include_deleted=False):
                raise HTTPException(status_code=400, detail="事件名称已存在")
        
        # 构建更新数据
        update_data = {}
        if event_request.event_name is not None:
            update_data["event_name"] = event_request.event_name
        if event_request.event_type is not None:
            update_data["event_type"] = event_request.event_type
        if event_request.device_range is not None:
            update_data["device_range_list"] = event_request.device_range
        if event_request.ble_range is not None:
            update_data["ble_range_list"] = event_request.ble_range
        if event_request.time_range is not None:
            update_data["time_range"] = event_request.time_range
        if event_request.ble_rule is not None:
            update_data["ble_rule"] = event_request.ble_rule
        if event_request.dis_range is not None:
            update_data["dis_range"] = event_request.dis_range
        if event_request.enable_status is not None:
            update_data["enable_status"] = event_request.enable_status
        
        if not update_data:
            raise HTTPException(status_code=400, detail="没有提供要更新的数据")
        
        # 使用事件管理器更新事件
        updated_event = event_manager.update_event(event_id, **update_data)
        
        if not updated_event:
            raise HTTPException(status_code=500, detail="更新事件失败")
        
        log.info(f"Updated event trigger {event_id}: {existing_event.event_name}")
        return {
            "success": True,
            "message": "事件更新成功",
            "data": {
                "id": updated_event.id,
                "event_name": updated_event.event_name,
                "event_type": updated_event.event_type
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error updating event trigger {event_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"更新事件失败: {str(e)}")


@app.delete("/api/events/{event_id}", status_code=200)
async def delete_event_trigger(event_id: int, dep=Depends(check_authority)):
    """
    删除事件触发条件接口（软删除）
    """
    try:
        from server.dao.event_trigger_dao import event_trigger_dao
        
        # 检查事件是否存在
        existing_event = event_trigger_dao.get_by_id(event_id)
        if not existing_event or existing_event.is_deleted():
            raise HTTPException(status_code=404, detail="事件不存在或已被删除")
        
        # 使用事件管理器删除事件
        success = event_manager.delete_event(event_id)
        
        if not success:
            raise HTTPException(status_code=500, detail="删除事件失败")
        
        log.info(f"Soft deleted event trigger {event_id}: {existing_event.event_name}")
        return {
            "success": True,
            "message": "事件删除成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error deleting event trigger {event_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"删除事件失败: {str(e)}")


@app.post("/api/events/{event_id}/enable", status_code=200)
async def enable_event_trigger(event_id: int, dep=Depends(check_authority)):
    """
    启用事件触发条件接口
    """
    try:
        # 使用事件管理器启用事件
        success = event_manager.enable_event(event_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="事件不存在或启用失败")
        
        log.info(f"Enabled event trigger: {event_id}")
        return {
            "success": True,
            "message": "事件已启用"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error enabling event trigger {event_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"启用事件失败: {str(e)}")


@app.get("/api/events/device/{eui}", status_code=200)
async def get_event_by_device(eui: str, dep=Depends(check_authority)):
    return event_manager.get_events_for_device(eui)


@app.post("/api/events/{event_id}/disable", status_code=200)
async def disable_event_trigger(event_id: int, dep=Depends(check_authority)):
    """
    禁用事件触发条件接口
    """
    try:
        # 使用事件管理器禁用事件
        success = event_manager.disable_event(event_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="事件不存在或禁用失败")
        
        log.info(f"Disabled event trigger: {event_id}")
        return {
            "success": True,
            "message": "事件已禁用"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error disabling event trigger {event_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"禁用事件失败: {str(e)}")


@app.post("/api/shutdown", status_code=200)
async def api_shutdown(request: Request, dep=Depends(check_authority)):
    """
    优雅停止服务接口
    需要管理员认证，执行优雅停止操作
    """
    global shutdown_flag
    
    try:
        # 检查是否已经在关闭中
        if shutdown_flag:
            return {
                "success": True,
                "message": "Server is already shutting down"
            }
        
        # 执行优雅停止
        await graceful_shutdown()
        
        # 延迟一段时间后停止服务器
        async def delayed_exit():
            await asyncio.sleep(2)  # 给响应时间返回
            log.info("Stopping Uvicorn server...")
            os._exit(0)  # 强制退出进程
        
        # 在后台执行延迟退出
        asyncio.create_task(delayed_exit())
        
        return {
            "success": True,
            "message": "Server shutdown initiated successfully"
        }
        
    except Exception as e:
        log.error(f"Error during graceful shutdown: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Shutdown failed: {str(e)}")


# --- Main Execution ---
if __name__ == "__main__":
    # Load runtime config first for server port
    # config_manager loads both on import, so we can get it directly.
    rt_cfg = config_manager.get_server_runtime_config()
    server_port = 8000  # Default
    if rt_cfg and rt_cfg.server and rt_cfg.server.port:
        server_port = rt_cfg.server.port
    else:
        log.warning(f"Could not load server port from runtime config. Using default {server_port}.")
        # Fallback if server_runtime_config.json is missing or malformed for port.

    if rt_cfg and len(rt_cfg.tracker_list) > 0:
        allow_tracker_list = rt_cfg.tracker_list
    log.info(f"Starting Uvicorn server on host 0.0.0.0 port {server_port}")

    dashboard_cfg = config_manager.get_dashboard_config()
    # Uvicorn should be run from project root: uvicorn server.main:app --reload
    uvicorn.run(app, host="0.0.0.0", port=server_port)
