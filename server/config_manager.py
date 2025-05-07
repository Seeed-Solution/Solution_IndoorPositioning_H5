# server/config_manager.py
import json
from pathlib import Path
from typing import Optional, Tuple
from .models import MiniprogramConfig, ServerRuntimeConfig, MiniprogramBeaconConfig

# Define paths for the two configuration files
# These paths are relative to the project root, assuming FastAPI runs from there.
MINIPROGRAM_CONFIG_FILE_PATH = Path("server/miniprogram_config.json")
SERVER_RUNTIME_CONFIG_FILE_PATH = Path("server/server_runtime_config.json")

# Caches for the loaded configurations
miniprogram_cfg_cache: Optional[MiniprogramConfig] = None
server_runtime_cfg_cache: Optional[ServerRuntimeConfig] = None

def load_miniprogram_config() -> Optional[MiniprogramConfig]:
    """Loads the miniprogram-generated configuration (map, beacons, basic settings)."""
    global miniprogram_cfg_cache
    if MINIPROGRAM_CONFIG_FILE_PATH.is_file():
        try:
            with open(MINIPROGRAM_CONFIG_FILE_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Ensure top-level keys match MiniprogramConfig model expectations
                # Specifically, the miniprogram exports "map", not "mapInfo"
                # Our MiniprogramConfig model expects "map", so this should align.
                miniprogram_cfg_cache = MiniprogramConfig(**data)
                print(f"Miniprogram configuration loaded successfully from {MINIPROGRAM_CONFIG_FILE_PATH}")
                return miniprogram_cfg_cache
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON from {MINIPROGRAM_CONFIG_FILE_PATH}: {e}")
            miniprogram_cfg_cache = None
            return None
        except Exception as e: # Catches Pydantic validation errors and others
            print(f"Error loading miniprogram configuration from {MINIPROGRAM_CONFIG_FILE_PATH}: {e}")
            miniprogram_cfg_cache = None
            return None
    else:
        print(f"Miniprogram configuration file not found at {MINIPROGRAM_CONFIG_FILE_PATH}")
        miniprogram_cfg_cache = None
        return None

def load_server_runtime_config() -> Optional[ServerRuntimeConfig]:
    """Loads the server-specific runtime configuration (MQTT, server port, Kalman params)."""
    global server_runtime_cfg_cache
    if SERVER_RUNTIME_CONFIG_FILE_PATH.is_file():
        try:
            with open(SERVER_RUNTIME_CONFIG_FILE_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
                server_runtime_cfg_cache = ServerRuntimeConfig(**data)
                print(f"Server runtime configuration loaded successfully from {SERVER_RUNTIME_CONFIG_FILE_PATH}")
                return server_runtime_cfg_cache
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON from {SERVER_RUNTIME_CONFIG_FILE_PATH}: {e}")
            server_runtime_cfg_cache = None
            return None
        except Exception as e: # Catches Pydantic validation errors and others
            print(f"Error loading server runtime configuration from {SERVER_RUNTIME_CONFIG_FILE_PATH}: {e}")
            server_runtime_cfg_cache = None
            return None
    else:
        print(f"Server runtime configuration file not found at {SERVER_RUNTIME_CONFIG_FILE_PATH}. Please create it.")
        # Consider creating a default one if it doesn't exist, or ensure manual creation.
        server_runtime_cfg_cache = None
        return None

def save_miniprogram_config(config_data: MiniprogramConfig) -> bool:
    """Saves the miniprogram-generated configuration data to its file."""
    global miniprogram_cfg_cache
    try:
        # config_data should be an instance of MiniprogramConfig
        # The .dict() method is from Pydantic BaseModel
        with open(MINIPROGRAM_CONFIG_FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(config_data.model_dump(), f, indent=2) # Use model_dump() for Pydantic v2+
        miniprogram_cfg_cache = config_data
        print(f"Miniprogram configuration saved successfully to {MINIPROGRAM_CONFIG_FILE_PATH}")
        return True
    except Exception as e:
        print(f"Error saving miniprogram configuration: {e}")
        return False

def get_miniprogram_config() -> Optional[MiniprogramConfig]:
    """Returns the currently loaded miniprogram configuration."""
    if miniprogram_cfg_cache is None:
        load_miniprogram_config() # Attempt to load if not already loaded
    return miniprogram_cfg_cache

def get_server_runtime_config() -> Optional[ServerRuntimeConfig]:
    """Returns the currently loaded server runtime configuration."""
    if server_runtime_cfg_cache is None:
        load_server_runtime_config() # Attempt to load if not already loaded
    return server_runtime_cfg_cache

# This helper function might still be useful, but it now uses MiniprogramConfig
def get_beacon_by_mac(mac_address: str) -> Optional[MiniprogramBeaconConfig]:
    """Finds a configured beacon by its MAC Address from the miniprogram config."""
    mp_config = get_miniprogram_config()
    if not mp_config or not mp_config.beacons:
        return None
    for beacon in mp_config.beacons:
        # macAddress field in MiniprogramBeaconConfig should be populated by AliasChoices
        if beacon.macAddress and beacon.macAddress.lower() == mac_address.lower():
            return beacon
    return None

# Initial load attempt when the module is imported
print("Initializing configuration manager...")
load_miniprogram_config()
load_server_runtime_config()

# Example of how to potentially create a default server_runtime_config.json if it's missing
# This is optional and depends on desired behavior.
# if server_runtime_cfg_cache is None and not SERVER_RUNTIME_CONFIG_FILE_PATH.exists():
#     print(f"Attempting to create a default server runtime config at {SERVER_RUNTIME_CONFIG_FILE_PATH}")
#     try:
#         default_mqtt = MqttServerConfig(brokerHost="your_broker_host", applicationID="your_org_id", topicPattern="your/topic/pattern")
#         default_server = WebServerConfig(port=8000)
#         default_kalman = KalmanParams()
#         default_runtime_cfg = ServerRuntimeConfig(mqtt=default_mqtt, server=default_server, kalman=default_kalman)
#         with open(SERVER_RUNTIME_CONFIG_FILE_PATH, 'w', encoding='utf-8') as f:
#             json.dump(default_runtime_cfg.model_dump(), f, indent=2)
#         server_runtime_cfg_cache = default_runtime_cfg
#         print(f"Created default server runtime config at {SERVER_RUNTIME_CONFIG_FILE_PATH}")
#     except Exception as e:
#         print(f"Failed to create default server runtime config: {e}") 