# server/config_manager.py
import json
from pathlib import Path
from typing import Optional, Tuple
from .models import MiniprogramConfig, ServerRuntimeConfig, MiniprogramBeaconConfig, PartialServerRuntimeConfig, PasswordChangeRequest, ServiceCredentialsRequest

# Define paths for the two configuration files
# These paths are relative to the project root, assuming FastAPI runs from there.
MINIPROGRAM_CONFIG_FILE_PATH = Path("server/miniprogram_config.json")
SERVER_RUNTIME_CONFIG_FILE_PATH = Path("server/server_runtime_config.json")

# Placeholder for passwords when returning config to frontend
PASSWORD_PLACEHOLDER = "********" 

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

def apply_sensecap_defaults(config: ServerRuntimeConfig) -> None:
    """Apply default values for SenseCap OpenStream configuration."""
    import random
    
    if config.sensecapOpenStream:
        # Set default broker host and port if not set
        if not config.sensecapOpenStream.brokerHost:
            config.sensecapOpenStream.brokerHost = 'sensecap-openstream.seeed.cc'
        if not config.sensecapOpenStream.brokerPort:
            config.sensecapOpenStream.brokerPort = 1883
            
        # Auto-update username, topic pattern and client ID based on applicationID
        if config.sensecapOpenStream.applicationID and config.sensecapOpenStream.applicationID.strip():
            app_id = config.sensecapOpenStream.applicationID.strip()
            
            # Auto-update username: org-{applicationId}
            config.sensecapOpenStream.username = f"org-{app_id}"
            
            # Auto-update topic pattern: /device_sensor_data/{applicationId}/+/+/+/+
            config.sensecapOpenStream.topicPattern = f"/device_sensor_data/{app_id}/+/+/+/+"
            
            # Auto-update client ID: org-{applicationId}-{六位随机数}
            random_digits = str(random.randint(100000, 999999))
            config.sensecapOpenStream.clientID = f"org-{app_id}-{random_digits}"
        else:
            # If applicationID is empty, clear related fields
            if config.sensecapOpenStream.username and config.sensecapOpenStream.username.startswith('org-'):
                config.sensecapOpenStream.username = None
            if config.sensecapOpenStream.topicPattern and '/device_sensor_data/' in config.sensecapOpenStream.topicPattern:
                config.sensecapOpenStream.topicPattern = None
            if config.sensecapOpenStream.clientID and config.sensecapOpenStream.clientID.startswith('org-'):
                config.sensecapOpenStream.clientID = None

def apply_chirpstack_defaults(config: ServerRuntimeConfig) -> None:
    """Apply default values for ChirpStack MQTT configuration."""
    if config.chirpStackMqtt:
        # Set default broker host and port if not set
        if not config.chirpStackMqtt.brokerHost:
            config.chirpStackMqtt.brokerHost = '127.0.0.1'
        if not config.chirpStackMqtt.brokerPort:
            config.chirpStackMqtt.brokerPort = 1883
            
        # Auto-update topic pattern based on applicationID
        if config.chirpStackMqtt.applicationID and config.chirpStackMqtt.applicationID.strip():
            app_id = config.chirpStackMqtt.applicationID.strip()
            
            # Auto-update topic pattern: application/{applicationID}/device/+/event/up
            config.chirpStackMqtt.topicPattern = f"application/{app_id}/device/+/event/up"
        else:
            # If applicationID is empty, clear topic pattern
            if config.chirpStackMqtt.topicPattern and 'application/' in config.chirpStackMqtt.topicPattern:
                config.chirpStackMqtt.topicPattern = None

def save_server_runtime_config(config_data: ServerRuntimeConfig) -> Tuple[bool, Optional[ServerRuntimeConfig]]:
    """Saves the server runtime configuration data to its file.
       If a new password is provided (not the placeholder), it's saved directly.
       If the password in config_data is the placeholder, it means no change was intended by the user for the password.
       In this case, we retain the existing password from the cache or file if possible.
    """
    global server_runtime_cfg_cache
    try:
        data_to_save = config_data.model_copy(deep=True) # Work with a copy

        # Apply default values for both services
        apply_sensecap_defaults(data_to_save)
        apply_chirpstack_defaults(data_to_save)

        # Handle passwords for multiple MQTT sources: if placeholder is received, try to keep existing password
        # SenseCAP OpenStream password handling
        if (hasattr(data_to_save, 'sensecapOpenStream') and data_to_save.sensecapOpenStream and 
            data_to_save.sensecapOpenStream.password == PASSWORD_PLACEHOLDER):
            existing_password = None
            if (server_runtime_cfg_cache and hasattr(server_runtime_cfg_cache, 'sensecapOpenStream') and 
                server_runtime_cfg_cache.sensecapOpenStream):
                existing_password = server_runtime_cfg_cache.sensecapOpenStream.password
            elif SERVER_RUNTIME_CONFIG_FILE_PATH.is_file():
                try:
                    with open(SERVER_RUNTIME_CONFIG_FILE_PATH, 'r', encoding='utf-8') as f_read:
                        current_file_data = json.load(f_read)
                        if (current_file_data.get("sensecapOpenStream") and 
                            current_file_data["sensecapOpenStream"].get("password")):
                            existing_password = current_file_data["sensecapOpenStream"]["password"]
                except Exception as e_read:
                    print(f"Could not read existing SenseCAP password from file during save: {e_read}")
            
            if existing_password and existing_password != PASSWORD_PLACEHOLDER:
                data_to_save.sensecapOpenStream.password = existing_password
            else:
                data_to_save.sensecapOpenStream.password = None
        
        # ChirpStack MQTT password handling
        if (hasattr(data_to_save, 'chirpStackMqtt') and data_to_save.chirpStackMqtt and 
            data_to_save.chirpStackMqtt.password == PASSWORD_PLACEHOLDER):
            existing_password = None
            if (server_runtime_cfg_cache and hasattr(server_runtime_cfg_cache, 'chirpStackMqtt') and 
                server_runtime_cfg_cache.chirpStackMqtt):
                existing_password = server_runtime_cfg_cache.chirpStackMqtt.password
            elif SERVER_RUNTIME_CONFIG_FILE_PATH.is_file():
                try:
                    with open(SERVER_RUNTIME_CONFIG_FILE_PATH, 'r', encoding='utf-8') as f_read:
                        current_file_data = json.load(f_read)
                        if (current_file_data.get("chirpStackMqtt") and 
                            current_file_data["chirpStackMqtt"].get("password")):
                            existing_password = current_file_data["chirpStackMqtt"]["password"]
                except Exception as e_read:
                    print(f"Could not read existing ChirpStack password from file during save: {e_read}")
            
            if existing_password and existing_password != PASSWORD_PLACEHOLDER:
                data_to_save.chirpStackMqtt.password = existing_password
            else:
                data_to_save.chirpStackMqtt.password = None
        
        # Legacy MQTT password handling (for backward compatibility)
        if hasattr(data_to_save, 'mqtt') and data_to_save.mqtt and data_to_save.mqtt.password == PASSWORD_PLACEHOLDER:
            existing_password = None
            if server_runtime_cfg_cache and server_runtime_cfg_cache.mqtt:
                existing_password = server_runtime_cfg_cache.mqtt.password
            elif SERVER_RUNTIME_CONFIG_FILE_PATH.is_file(): # Fallback to reading from file if cache is stale/empty
                try:
                    with open(SERVER_RUNTIME_CONFIG_FILE_PATH, 'r', encoding='utf-8') as f_read:
                        current_file_data = json.load(f_read)
                        if current_file_data.get("mqtt") and current_file_data["mqtt"].get("password"):
                            existing_password = current_file_data["mqtt"]["password"]
                except Exception as e_read:
                    print(f"Could not read existing password from file during save: {e_read}")
            
            if existing_password and existing_password != PASSWORD_PLACEHOLDER:
                data_to_save.mqtt.password = existing_password
            else:
                # If no existing sensible password, save it as empty or None (as Pydantic model allows)
                data_to_save.mqtt.password = None 

        with open(SERVER_RUNTIME_CONFIG_FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(data_to_save.model_dump(), f, indent=2)
        
        server_runtime_cfg_cache = data_to_save # Update cache with what was actually saved
        print(f"Server runtime configuration saved successfully to {SERVER_RUNTIME_CONFIG_FILE_PATH}")
        return True, server_runtime_cfg_cache
    except Exception as e:
        print(f"Error saving server runtime configuration: {e}")
        return False, None

def save_partial_server_runtime_config(partial_config: PartialServerRuntimeConfig) -> Tuple[bool, Optional[ServerRuntimeConfig]]:
    """
    部分更新服务器运行时配置，只更新允许修改的字段
    保持其他字段不变
    """
    global server_runtime_cfg_cache
    try:
        # 首先加载当前完整配置
        current_config = load_server_runtime_config()
        if not current_config:
            print("Cannot load current server runtime configuration for partial update")
            return False, None
        
        # 创建一个副本用于修改
        updated_config = current_config.model_copy(deep=True)
        
        # 只更新提供的字段
        if partial_config.sensecapOpenStream is not None:
            # 处理密码占位符
            if (partial_config.sensecapOpenStream.password == PASSWORD_PLACEHOLDER and 
                updated_config.sensecapOpenStream and updated_config.sensecapOpenStream.password):
                # 保持原密码不变
                partial_config.sensecapOpenStream.password = updated_config.sensecapOpenStream.password
            updated_config.sensecapOpenStream = partial_config.sensecapOpenStream
            # Apply SenseCap defaults after updating
            apply_sensecap_defaults(updated_config)
            
        if partial_config.chirpStackMqtt is not None:
            # 处理密码占位符
            if (partial_config.chirpStackMqtt.password == PASSWORD_PLACEHOLDER and 
                updated_config.chirpStackMqtt and updated_config.chirpStackMqtt.password):
                # 保持原密码不变
                partial_config.chirpStackMqtt.password = updated_config.chirpStackMqtt.password
            updated_config.chirpStackMqtt = partial_config.chirpStackMqtt
            # Apply ChirpStack defaults after updating
            apply_chirpstack_defaults(updated_config)
            
        if partial_config.tracker_list is not None:
            updated_config.tracker_list = partial_config.tracker_list
            
        if partial_config.allow_all_tracker is not None:
            updated_config.allow_all_tracker = partial_config.allow_all_tracker
            
        if partial_config.username is not None:
            updated_config.username = partial_config.username
            
        # 注意：不处理Authentication部分的password字段，密码通过专门的密码修改接口设置
            
        if partial_config.webhook is not None:
            updated_config.webhook = partial_config.webhook
        
        # 保存完整的更新后配置
        return save_server_runtime_config(updated_config)
        
    except Exception as e:
        print(f"Error in partial update of server runtime configuration: {e}")
        return False, None

def verify_and_change_password(password_request: PasswordChangeRequest) -> Tuple[bool, str, Optional[ServerRuntimeConfig]]:
    """
    验证当前密码并更新为新密码
    返回: (成功状态, 消息, 更新后的配置)
    """
    global server_runtime_cfg_cache
    try:
        # 加载当前配置
        current_config = load_server_runtime_config()
        if not current_config:
            return False, "Cannot load current server runtime configuration", None
        
        # 验证当前密码
        if current_config.password != password_request.current_password:
            print(f"Password verification failed for user: {current_config.username}")
            return False, "Current password is incorrect", None
        
        # 检查新密码是否与当前密码相同
        if current_config.password == password_request.new_password:
            return False, "New password must be different from current password", None
        
        # 验证新密码长度
        if len(password_request.new_password) < 6:
            return False, "New password must be at least 6 characters long", None
        
        print(f"Password verification successful for user: {current_config.username}")
        
        # 创建配置副本并更新密码
        updated_config = current_config.model_copy(deep=True)
        updated_config.password = password_request.new_password
        
        # 保存更新后的配置
        success, saved_config = save_server_runtime_config(updated_config)
        if success and saved_config:
            print(f"Password updated successfully for user: {saved_config.username}")
            return True, "Password changed successfully", saved_config
        else:
            return False, "Failed to save new password to configuration file", None
            
    except Exception as e:
        print(f"Error in password verification and update: {e}")
        return False, f"Internal server error: {str(e)}", None

def set_service_credentials(credentials_request: ServiceCredentialsRequest) -> Tuple[bool, str, Optional[ServerRuntimeConfig]]:
    """
    安全地设置服务凭证（用户名和密码）
    支持的服务类型: sensecap, chirpstack, webhook
    返回: (成功状态, 消息, 更新后的配置)
    """
    global server_runtime_cfg_cache
    try:
        # 加载当前配置
        current_config = load_server_runtime_config()
        if not current_config:
            return False, "Cannot load current server runtime configuration", None
        
        # 创建配置副本用于修改
        updated_config = current_config.model_copy(deep=True)
        
        # 根据服务类型设置凭证
        if credentials_request.service_type == "sensecap":
            if not updated_config.sensecapOpenStream:
                # 如果不存在，创建默认配置
                from .models import SensecapOpenStreamConfig
                updated_config.sensecapOpenStream = SensecapOpenStreamConfig()
            
            if credentials_request.username is not None:
                updated_config.sensecapOpenStream.username = credentials_request.username
            if credentials_request.password is not None:
                updated_config.sensecapOpenStream.password = credentials_request.password
                
        elif credentials_request.service_type == "chirpstack":
            if not updated_config.chirpStackMqtt:
                # 如果不存在，创建默认配置
                from .models import MqttServerConfig
                updated_config.chirpStackMqtt = MqttServerConfig()
            
            if credentials_request.username is not None:
                updated_config.chirpStackMqtt.username = credentials_request.username
            if credentials_request.password is not None:
                updated_config.chirpStackMqtt.password = credentials_request.password
                
        elif credentials_request.service_type == "webhook":
            if credentials_request.password is not None:
                if not updated_config.webhook:
                    from .models import WebhookSetting
                    updated_config.webhook = WebhookSetting()
                updated_config.webhook.authorization = credentials_request.password
                
        else:
            return False, f"Unsupported service type: {credentials_request.service_type}", None
        
        # 保存更新后的配置
        success, saved_config = save_server_runtime_config(updated_config)
        if success and saved_config:
            print(f"Service credentials updated successfully for service: {credentials_request.service_type}")
            return True, f"Credentials for {credentials_request.service_type} updated successfully", saved_config
        else:
            return False, "Failed to save credentials to configuration file", None
            
    except Exception as e:
        print(f"Error in service credentials update: {e}")
        return False, f"Internal server error: {str(e)}", None

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