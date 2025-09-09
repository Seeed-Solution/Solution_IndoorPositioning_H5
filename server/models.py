# server/models.py
from pydantic import BaseModel, Field, AliasChoices
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime
from dataclasses import dataclass, asdict
import json

# --- Models for Miniprogram Exported Configuration (e.g., map_beacon_config.json) ---

class MapEntity(BaseModel):
    type: str
    points: List[List[float]]
    closed: Optional[bool] = None
    color: Optional[str] = None
    lineWidth: Optional[float] = None

class MiniprogramMapInfo(BaseModel): # Renamed for clarity, matches "map" key in miniprogram JSON
    width: float
    height: float
    entities: List[MapEntity]

class MiniprogramBeaconConfig(BaseModel): # Renamed for clarity
    macAddress: str = Field(validation_alias=AliasChoices('macAddress', 'deviceId'), description="BLE MAC address")
    major: Optional[int] = None
    minor: Optional[int] = None
    name: Optional[str] = Field(default=None, validation_alias=AliasChoices('name', 'displayName'))
    txPower: int = Field(..., description="RSSI at 1m")
    x: float = Field(..., description="x coordinate in meters")
    y: float = Field(..., description="y coordinate in meters")

class MiniprogramSettings(BaseModel): # Renamed for clarity
    signalPropagationFactor: float = Field(default=2.5, description="Path loss exponent 'n'")

class MiniprogramConfig(BaseModel):
    map: MiniprogramMapInfo # Expects a top-level "map" key from miniprogram JSON
    beacons: List[MiniprogramBeaconConfig]
    settings: MiniprogramSettings


# --- Models for Web UI Configuration (e.g., web_ui_config.json) ---

class WebUIMapEntity(BaseModel):
    type: str # e.g., 'polyline'
    points: List[List[float]] # List of [x, y] coordinates
    closed: Optional[bool] = None
    # Visual properties, ensure they match what MapEditorTab.vue uses/expects
    strokeColor: Optional[str] = None 
    lineWidth: Optional[float] = None
    fillColor: Optional[str] = None # If supporting filled shapes
    # 'color' was in MiniprogramMapEntity, MapEditorTab uses strokeColor, fillColor

class WebUIMapInfo(BaseModel):
    name: Optional[str] = None # Optional name for the map layout itself
    width: float # in meters
    height: float # in meters
    entities: List[WebUIMapEntity] = []

class WebUIBeaconConfig(BaseModel):
    uuid: str = Field(..., description="iBeacon UUID")
    major: int = Field(..., description="iBeacon Major value")
    minor: int = Field(..., description="iBeacon Minor value")
    x: float = Field(..., description="x coordinate in meters")
    y: float = Field(..., description="y coordinate in meters")
    txPower: int = Field(..., description="Measured RSSI at 1m for distance calculation")
    displayName: Optional[str] = Field(default=None, description="User-friendly display name for the beacon")
    macAddress: Optional[str] = Field(default=None, description="Physical MAC address, if known/relevant")
    deviceId: Optional[str] = Field(default=None, description="Device ID for backward compatibility - will be mapped to macAddress")
    map: Optional[str] = None


class WebUISettings(BaseModel):
    signalPropagationFactor: float = Field(default=2.5, ge=1.0, le=6.0, description="Path loss exponent 'n' for RSSI to distance conversion")


class SingleMapConfig(BaseModel):
    map: Optional[WebUIMapInfo] = None  # Map can be optional initially
    beacons: List[WebUIBeaconConfig] = []
    settings: WebUISettings
    is_darwin: Optional[bool] = Field(default=False,description="True if MAC addresses are virtual (server running on macOS)")


class WebUIConfig(BaseModel):
    map: Optional[WebUIMapInfo] = None # Map can be optional initially
    beacons: List[WebUIBeaconConfig] = []
    settings: WebUISettings
    is_darwin: Optional[bool] = Field(default=False, description="True if MAC addresses are virtual (server running on macOS)")


class DashboardConfig(BaseModel):
    maps: Optional[list[SingleMapConfig]] = []

# --- Models for Server-Side Runtime Configuration (e.g., server_runtime_config.json) ---

class MqttServerConfig(BaseModel): # Renamed from MqttConfig to avoid clash if old one is kept temporarily
    brokerHost: str = '127.0.0.1'
    brokerPort: int = 1883
    username: Optional[str] = None
    password: Optional[str] = None
    applicationID: Optional[str] = None  # e.g., your OrgID
    topicPattern: Optional[str] = None   # e.g., "/device_sensor_data/{ApplicationID}/+/+/+/+"
    clientID: Optional[str] = Field(default=None, validation_alias=AliasChoices('clientID', 'clientId'))
    enabled: bool = Field(default=True, description="Enable or disable MQTT client")
    live_mqtt_status: Optional[str] = Field(default=None, description="Live MQTT connection status, not saved to file")

class SensecapMqttConfig(MqttServerConfig):
    """SenseCap OpenStream MQTT configuration."""
    pass

class ChirpstackMqttConfig(MqttServerConfig):
    """ChirpStack MQTT configuration."""
    pass

class WebServerConfig(BaseModel): # Renamed from ServerConfig
    port: int = Field(default=8000, description="Port for the FastAPI web server")

class KalmanParams(BaseModel):
    processVariance: float = Field(default=1.0, description="Kalman filter process variance Q")
    measurementVariance: float = Field(default=10.0, description="Kalman filter measurement variance R")

class WebhookSetting(BaseModel):
    enable: bool = False
    host: Optional[str] = None
    headers: Optional[dict[str, str]] = {}


class ServerRuntimeConfig(BaseModel):
    sensecapOpenStream: SensecapMqttConfig = SensecapMqttConfig(
        enabled=False,
        brokerHost='sensecap-openstream.seeed.cc',
        brokerPort=1883
    )
    chirpStackMqtt: ChirpstackMqttConfig = ChirpstackMqttConfig(
        enabled=False,
        brokerHost='127.0.0.1',
        brokerPort=1883
    )
    server: WebServerConfig = None
    kalman: KalmanParams = None
    tracker_list: list[str] = []
    allow_all_tracker: bool = True
    allow_area_location: bool = True
    username: str = 'admin'
    password: str = 'ctyshjdl'
    webhook: WebhookSetting = WebhookSetting(enable=False)


class PartialServerRuntimeConfig(BaseModel):
    sensecapOpenStream: Optional[SensecapMqttConfig] = None
    chirpStackMqtt: Optional[ChirpstackMqttConfig] = None
    tracker_list: Optional[list[str]] = None
    allow_all_tracker: Optional[bool] = None
    allow_area_location: Optional[bool] = None
    username: Optional[str] = None
    webhook: Optional[WebhookSetting] = None


class PasswordChangeRequest(BaseModel):
    """
    密码修改请求模型
    """
    current_password: str = Field(..., description="当前密码")
    new_password: str = Field(..., min_length=6, description="新密码，最少6位字符")
    
    class Config:
        json_schema_extra = {
            "example": {
                "current_password": "old_password_here",
                "new_password": "new_password_here"
            }
        }


class ServiceCredentialsRequest(BaseModel):
    """
    服务凭证设置请求模型
    用于安全地设置各种服务的用户名和密码
    """
    service_type: str = Field(..., description="服务类型: sensecap, chirpstack, webhook")
    username: Optional[str] = Field(None, description="用户名")
    password: Optional[str] = Field(None, description="密码")
    
    class Config:
        json_schema_extra = {
            "example": {
                "service_type": "sensecap",
                "username": "your_username",
                "password": "your_password"
            }
        }


class LoginRequest(BaseModel):
    """
    登录请求模型
    """
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")
    
    class Config:
        json_schema_extra = {
            "example": {
                "username": "admin",
                "password": "5d41402abc4b2a76b9719d911017c592"
            }
        }



# --- Tracker Data Models (remain largely unchanged) ---

class DetectedBeacon(BaseModel):
    macAddress: str = Field(..., description="BLE MAC address detected")
    major: Optional[int] = None
    minor: Optional[int] = None
    name: Optional[str] = Field(default=None)
    rssi: int
    configured_x: Optional[float] = None
    configured_y: Optional[float] = None

class TrackerReport(BaseModel):
    trackerId: str # Corresponds to device devEui from MQTT topic
    timestamp: int # Unix ms timestamp from message payload
    detectedBeacons: List[DetectedBeacon] = []
    sos: int = 2 # 0: 恢复, 1: 触发, 2: 未知
    locType: str = 'bluetooth'
    loc: dict[str, Any] = {}
    sourceType: str = "sensecap"


class TrackerState(BaseModel):
    trackerId: str
    tracker_number: Optional[int] = None  # 固定的数字标记
    x: Optional[float] = None
    y: Optional[float] = None
    last_update_time: int # Unix ms timestamp (server time of this update)
    last_known_measurement_time: Optional[int] = None # Unix ms timestamp (from original report)
    last_detected_beacons: List[DetectedBeacon] = [] 
    position_history: List[Tuple[float, float, int]] = [] # List of (x, y, timestamp_ms)
    used_beacon_macs: List[str] = []  # MAC addresses of beacons used in position calculation
    map: Optional[str] = "unknown"
    sos: int = 0
    type: Optional[str] = "calculation"
    radius: float = 0


class UserSessionInfo(BaseModel):
    username: str
    role: str




# --- Old combined ConfigData and CommonSettings (can be removed after refactoring) ---
# class OldBeaconConfig(BaseModel):
#     macAddress: str = Field(validation_alias=AliasChoices('macAddress', 'deviceId'), description="BLE MAC address of the beacon (e.g., C3:00:00:3E:7D:EF)")
#     major: Optional[int] = None 
#     minor: Optional[int] = None 
#     name: Optional[str] = Field(default=None, validation_alias=AliasChoices('name', 'displayName'))
#     txPower: int # RSSI at 1m
#     x: float # meters
#     y: float # meters

# class OldMqttConfig(BaseModel):
#     brokerHost: str # No default, should be in config
#     brokerPort: int = 1883
#     username: Optional[str] = None
#     password: Optional[str] = None
#     applicationID: str # No default, your OrgID
#     topicPattern: str  # No default, e.g., "/device_sensor_data/{ApplicationID}/+/+/+/+"
#     clientID: Optional[str] = Field(default=None, validation_alias=AliasChoices('clientID', 'clientId'))

# class OldServerConfig(BaseModel):
#     port: int = 8000

# class OldCommonSettings(BaseModel):
#     signalPropagationFactor: float = 2.5 # Default value (n in path loss model)
#     kalmanProcessVariance: float = 1.0 # Uncertainty in motion model
#     kalmanMeasurementVariance: float = 10.0 # Uncertainty in position measurement

# class OldConfigData(BaseModel):
#     mapInfo: MiniprogramMapInfo # Changed to reflect it comes from miniprog
#     beacons: List[OldBeaconConfig]
#     settings: OldCommonSettings
#     mqtt: OldMqttConfig
#     server: OldServerConfig


# --- Device Alarm Record Model ---

@dataclass
class UserSessionRecord:
    session_token: str
    username: str
    login_time: datetime
    expire_time: datetime

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典，方便JSON序列化"""
        data = asdict(self)
        # 转换datetime为字符串
        if self.login_time:
            data['login_time'] = self.login_time.isoformat()
        if self.expire_time:
            data['expire_time'] = self.expire_time.isoformat()
        return data

    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserSessionRecord':
        if 'login_time' in data and isinstance(data['login_time'], str):
            data['login_time'] = datetime.fromisoformat(data['login_time'])
        if 'expire_time' in data and isinstance(data['expire_time'], str):
            data['expire_time'] = datetime.fromisoformat(data['expire_time'])
        return cls(**data)

    @classmethod
    def from_json(cls, json_str: str) -> 'UserSessionRecord':
        """从JSON字符串创建对象"""
        data = json.loads(json_str)
        return cls.from_dict(data)

    def is_expired(self) -> bool:
        """检查会话是否已过期"""
        return datetime.now() > self.expire_time



@dataclass
class DeviceAlarmRecord:
    """设备报警记录数据模型"""
    id: Optional[int] = None
    dev_eui: str = ""
    alarm_time: Optional[datetime] = None
    create_time: Optional[datetime] = None
    pos_type: str = "bluetooth"
    loc: Dict[str, Any] = None
    beacons: Optional[List[Dict[str, Any]]] = None
    sos: int = 0
    map_name: Optional[str] = 'unknown'
    
    def __post_init__(self):
        if self.loc is None:
            self.loc = {}
        if self.alarm_time is None:
            self.alarm_time = datetime.now()
        if self.create_time is None:
            self.create_time = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典，方便JSON序列化"""
        data = asdict(self)
        # 转换datetime为字符串
        if self.alarm_time:
            data['alarm_time'] = self.alarm_time.isoformat()
        if self.create_time:
            data['create_time'] = self.create_time.isoformat()
        return data
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DeviceAlarmRecord':
        """从字典创建对象"""
        # 转换字符串为datetime
        if 'alarm_time' in data and isinstance(data['alarm_time'], str):
            data['alarm_time'] = datetime.fromisoformat(data['alarm_time'])
        if 'create_time' in data and isinstance(data['create_time'], str):
            data['create_time'] = datetime.fromisoformat(data['create_time'])
        return cls(**data)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'DeviceAlarmRecord':
        """从JSON字符串创建对象"""
        data = json.loads(json_str)
        return cls.from_dict(data) 