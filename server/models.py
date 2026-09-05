# server/models.py
from pydantic import BaseModel, Field, AliasChoices, field_validator, model_validator
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime
from dataclasses import dataclass, asdict
import json

import server.constant.event_constant as event_constant

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
    minX: Optional[float] = None # Minimum X coordinate in meters
    maxX: Optional[float] = None # Maximum X coordinate in meters
    minY: Optional[float] = None # Minimum Y coordinate in meters
    maxY: Optional[float] = None # Maximum Y coordinate in meters
    background: Optional[str] = None # Background image URL or path

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
    is_darwin: Optional[bool] = Field(default=False, description="True if MAC address is virtual (server running on macOS)")


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


# ODbL 要求署名可点击回到 OSM 版权页.
OSM_ATTRIBUTION = (
    '&copy; <a href="https://www.openstreetmap.org/copyright" '
    'target="_blank" rel="noopener noreferrer">OpenStreetMap contributors</a>'
)

DEFAULT_OUTDOOR_TILE_SOURCES = [
    {
        "id": "osm",
        "name": "OpenStreetMap",
        "url": "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        "attribution": OSM_ATTRIBUTION,
        "subdomains": ["a", "b", "c"],
        "maxZoom": 19,
        "coordSystem": "wgs84",
        "gcj02Correction": False,
        "kind": "raster",
    }
]


class OutdoorTileSource(BaseModel):
    """One base-map source for the outdoor (WGS84) view."""
    id: str
    name: Optional[str] = None
    url: str
    # raster: {z}/{x}/{y} 瓦片 URL; pmtiles: 单个 .pmtiles 归档的 URL (离线底图).
    kind: str = "raster"
    attribution: Optional[str] = ""
    subdomains: Optional[List[str]] = None
    maxZoom: int = 19
    coordSystem: str = "wgs84"          # wgs84 | gcj02
    # 高德/天地图瓦片是 GCJ-02, 与设备上报的 WGS84 有偏移. 本期只标记, 不纠偏.
    gcj02Correction: bool = False

    @field_validator("kind", mode="after")
    @classmethod
    def _known_kind(cls, value):
        if value not in ("raster", "pmtiles"):
            raise ValueError("kind must be 'raster' or 'pmtiles'")
        return value


class OutdoorConfig(BaseModel):
    tileSources: List[OutdoorTileSource] = Field(
        default_factory=lambda: [OutdoorTileSource(**s) for s in DEFAULT_OUTDOOR_TILE_SOURCES])
    defaultSource: str = "osm"

    @field_validator("tileSources", mode="after")
    @classmethod
    def _at_least_one_source(cls, value):
        # 配置里给了空列表也自动补回 OSM.
        if not value:
            return [OutdoorTileSource(**s) for s in DEFAULT_OUTDOOR_TILE_SOURCES]
        return value

    @model_validator(mode="after")
    def _default_source_must_exist(self):
        if self.defaultSource not in {s.id for s in self.tileSources}:
            self.defaultSource = self.tileSources[0].id
        return self


class DashboardConfig(BaseModel):
    maps: Optional[list[SingleMapConfig]] = []
    # 旧的 dashboard_config.json 没有这一段, 缺失时自动补一份 OSM 默认配置.
    outdoor: OutdoorConfig = Field(default_factory=OutdoorConfig)

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


class GroupCreateRequest(BaseModel):
    """
    创建分组请求模型
    """
    group_name: str = Field(..., min_length=1, max_length=100, description="分组名称")
    
    class Config:
        json_schema_extra = {
            "example": {
                "group_name": "生产车间A"
            }
        }


class GroupUpdateRequest(BaseModel):
    """
    更新分组请求模型
    """
    group_name: str = Field(..., min_length=1, max_length=100, description="新的分组名称")
    
    class Config:
        json_schema_extra = {
            "example": {
                "group_name": "生产车间B"
            }
        }


class GroupListItem(BaseModel):
    """
    分组列表项响应模型
    """
    id: int = Field(..., description="分组ID")
    group_name: str = Field(..., description="分组名称")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "group_name": "生产车间A"
            }
        }


class DeviceCreateRequest(BaseModel):
    """
    创建设备请求模型
    """
    dev_eui: str = Field(..., min_length=16, max_length=16, description="设备EUI（16位字符）")
    device_name: str = Field(..., min_length=1, max_length=20, description="设备名称（最多20字符）")
    group_id: Optional[int] = Field(None, description="分组ID，可为空")
    is_favorite: bool = Field(default=False, description="是否收藏")
    
    class Config:
        json_schema_extra = {
            "example": {
                "dev_eui": "1234567890ABCDEF",
                "device_name": "传感器001",
                "group_id": 1,
                "is_favorite": False
            }
        }


class DeviceUpdateRequest(BaseModel):
    """
    更新设备请求模型
    """
    dev_eui: Optional[str] = Field(None, min_length=1, max_length=20, description="eui")
    device_name: Optional[str] = Field(None, min_length=1, max_length=20, description="设备名称")
    group_id: Optional[int] = Field(None, description="分组ID")
    is_favorite: Optional[bool] = Field(None, description="是否收藏")
    
    class Config:
        json_schema_extra = {
            "example": {
                "device_name": "传感器002",
                "group_id": 2,
                "is_favorite": True
            }
        }


class DeviceStatusUpdateRequest(BaseModel):
    """
    设备状态更新请求模型
    """
    is_online: Optional[bool] = Field(None, description="是否在线")
    battery_level: Optional[int] = Field(None, ge=0, le=100, description="电量（0-100）")
    
    class Config:
        json_schema_extra = {
            "example": {
                "is_online": True,
                "battery_level": 85
            }
        }

class TrackerStateQueryRequest(BaseModel):
    dev_eui_list: Optional[list[str]] = Field(None, description="eui list")
    online_status: Optional[str] = Field(None, description="在线状态")
    is_favorite: Optional[bool] = Field(None, description="是否收藏")


class DeviceListItem(BaseModel):
    """
    设备列表项响应模型
    """
    id: int = Field(..., description="设备ID")
    dev_eui: str = Field(..., description="设备EUI")
    device_name: str = Field(..., description="设备名称")
    group_id: Optional[int] = Field(None, description="分组ID")
    is_online: bool = Field(..., description="是否在线")
    is_favorite: bool = Field(..., description="是否收藏")
    battery_level: Optional[int] = Field(None, description="电量")
    create_time: str = Field(..., description="创建时间")
    last_data_update_time: Optional[str] = Field(None, description="最后数据更新时间")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "dev_eui": "1234567890ABCDEF",
                "device_name": "传感器001",
                "group_id": 1,
                "is_online": True,
                "is_favorite": False,
                "battery_level": 85,
                "create_time": "2024-01-01T10:00:00",
                "last_data_update_time": "2024-01-01T15:30:00"
            }
        }


class DeviceSearchRequest(BaseModel):
    """
    设备搜索请求模型
    """
    keyword: str = Field(..., min_length=1, description="搜索关键词（设备名称或EUI）")
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量")
    
    class Config:
        json_schema_extra = {
            "example": {
                "keyword": "传感器",
                "page": 1,
                "page_size": 20
            }
        }


class DeviceBatchUpdateGroupRequest(BaseModel):
    """
    批量更新设备分组请求模型
    """
    dev_eui_list: List[str] = Field(..., min_items=1, description="设备EUI列表，至少包含1个设备")
    group_id: int = Field(...,  description="目标分组ID，0表示默认分组")
    
    class Config:
        json_schema_extra = {
            "example": {
                "dev_eui_list": ["1234567890ABCDEF", "FEDCBA0987654321"],
                "group_id": 1
            }
        }


class EventTriggerCreateRequest(BaseModel):
    """
    创建事件触发条件请求模型
    """
    event_name: str = Field(..., min_length=1, max_length=100, description="事件名称")
    event_type: int = Field(..., description="事件类型")
    device_range: Optional[List[str]] = Field(default=[], description="设备范围列表")
    ble_range: Optional[List[str]] = Field(default=[], description="BLE范围列表")
    time_range: Optional[int] = Field(default=0, description="时间范围")
    ble_rule: Optional[int] = Field(default=0, description="BLE规则")
    dis_range: Optional[float] = Field(default=0.0, ge=0, description="距离范围")
    enable_status: Optional[bool] = Field(default=True, description="启用状态")
    geofence_id: Optional[int] = Field(default=None, description="地理围栏ID，location_mode=geo 时必填")
    location_mode: Optional[str] = Field(default="ble", description="判定模式 ble|geo")
    transition: Optional[str] = Field(default="both", description="进出方向 enter|exit|both")

    class Config:
        json_schema_extra = {
            "example": {
                "event_name": "设备离线告警",
                "event_type": 1,
                "device_range": ["device001", "device002"],
                "ble_range": ["00:11:22:33:44:55"],
                "time_range": 0,
                "ble_rule": 1,
                "dis_range": 10.0,
                "enable_status": True
            }
        }


class EventTriggerUpdateRequest(BaseModel):
    """
    更新事件触发条件请求模型
    """
    event_name: Optional[str] = Field(None, min_length=1, max_length=100, description="事件名称")
    event_type: Optional[int] = Field(None, description="事件类型")
    device_range: Optional[List[str]] = Field(None, description="设备范围列表")
    ble_range: Optional[List[str]] = Field(None, description="BLE范围列表")
    time_range: Optional[int] = Field(default=0, description="时间范围")
    ble_rule: Optional[int] = Field(None, description="BLE规则")
    dis_range: Optional[float] = Field(None, ge=0, description="距离范围")
    enable_status: Optional[bool] = Field(None, description="启用状态")
    geofence_id: Optional[int] = Field(None, description="地理围栏ID")
    location_mode: Optional[str] = Field(None, description="判定模式 ble|geo")
    transition: Optional[str] = Field(None, description="进出方向 enter|exit|both")

    class Config:
        json_schema_extra = {
            "example": {
                "event_name": "设备离线告警-更新",
                "event_type": 2,
                "device_range": ["device003"],
                "enable_status": False
            }
        }


class EventTriggerListItem(BaseModel):
    """
    事件触发条件列表项响应模型
    """
    id: int = Field(..., description="事件ID")
    event_name: str = Field(..., description="事件名称")
    event_type: int = Field(..., description="事件类型")
    device_range: List[str] = Field(..., description="设备范围列表")
    ble_range: List[str] = Field(..., description="BLE范围列表")
    time_range: int = Field(default=0, description="时间范围")
    ble_rule: int = Field(..., description="BLE规则")
    dis_range: float = Field(..., description="距离范围")
    enable_status: bool = Field(..., description="启用状态")
    create_time: str = Field(..., description="创建时间")
    geofence_id: Optional[int] = Field(default=None, description="地理围栏ID")
    location_mode: str = Field(default="ble", description="判定模式 ble|geo")
    transition: str = Field(default="both", description="进出方向 enter|exit|both")

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "event_name": "设备离线告警",
                "event_type": 1,
                "device_range": ["device001", "device002"],
                "ble_range": ["00:11:22:33:44:55"],
                "time_range": 0,
                "ble_rule": 1,
                "dis_range": 10.0,
                "enable_status": True,
                "create_time": "2024-01-01T10:00:00"
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
    dis: Optional[float] = -1

class TrackerReport(BaseModel):
    trackerId: str # Corresponds to device devEui from MQTT topic
    timestamp: int # Unix ms timestamp from message payload
    receive_time: Optional[int] = int(datetime.now().timestamp()) # unit: second
    detectedBeacons: List[DetectedBeacon] = []
    sos: int = 2 # 0: 恢复, 1: 触发, 2: 未知
    locType: str = 'bluetooth'
    map_name: str = "unknown"
    loc: dict[str, Any] = {}
    sourceType: str = "sensecap"
    battery: Optional[int] = -1


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


# --- Event Trigger Model ---

@dataclass
class EventTriggerRecord:
    """事件触发条件数据模型"""
    id: Optional[int] = None
    event_name: str = ""  # 事件名称
    event_type: int = 0  # 事件类型  1:sos, 2:offline, 3:checkin, 4: position detection
    device_range: str = "[]"  # 设备范围，JSON格式存储list[str]
    ble_range: str = "[]"  # BLE范围，JSON格式存储list[str]
    time_range: int = 0  # 时间范围
    ble_rule: int = 0  # BLE规则
    dis_range: float = 0.0  # 距离范围
    enable_status: bool = True  # 启用状态
    create_time: Optional[datetime] = None  # 创建时间
    delete_time: Optional[datetime] = None  # 删除时间（软删除）
    geofence_id: Optional[int] = None  # 关联的地理围栏 ID（location_mode=geo 时必填）
    location_mode: str = "ble"  # ble | geo
    transition: str = "both"  # enter | exit | both

    def __post_init__(self):
        if self.create_time is None:
            self.create_time = datetime.now()
        if not self.location_mode:
            self.location_mode = "ble"
        if not self.transition:
            self.transition = "both"

    def is_geo_mode(self) -> bool:
        """是否按经纬度围栏判定（而不是 BLE MAC 白名单）"""
        return (self.location_mode or "ble").lower() == "geo"

    def get_device_range_list(self) -> List[str]:
        """获取设备范围列表"""
        try:
            return json.loads(self.device_range) if self.device_range else []
        except json.JSONDecodeError:
            return []
    
    def set_device_range_list(self, device_list: List[str]):
        """设置设备范围列表"""
        self.device_range = json.dumps(device_list, ensure_ascii=False)
    
    def get_ble_range_list(self) -> List[str]:
        """获取BLE范围列表"""
        try:
            return json.loads(self.ble_range) if self.ble_range else []
        except json.JSONDecodeError:
            return []
    
    def set_ble_range_list(self, ble_list: List[str]):
        """设置BLE范围列表"""
        self.ble_range = json.dumps(ble_list, ensure_ascii=False)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典，方便JSON序列化"""
        data = asdict(self)
        # 转换datetime为字符串
        if self.create_time:
            data['create_time'] = self.create_time.isoformat()
        if self.delete_time:
            data['delete_time'] = self.delete_time.isoformat()
        # 解析JSON字段为列表
        data['device_range_list'] = self.get_device_range_list()
        data['ble_range_list'] = self.get_ble_range_list()
        return data
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EventTriggerRecord':
        """从字典创建对象"""
        # 转换字符串为datetime
        if 'create_time' in data and isinstance(data['create_time'], str):
            data['create_time'] = datetime.fromisoformat(data['create_time'])
        if 'delete_time' in data and isinstance(data['delete_time'], str):
            data['delete_time'] = datetime.fromisoformat(data['delete_time'])
        
        # 处理列表字段
        if 'device_range_list' in data:
            data['device_range'] = json.dumps(data.pop('device_range_list'), ensure_ascii=False)
        if 'ble_range_list' in data:
            data['ble_range'] = json.dumps(data.pop('ble_range_list'), ensure_ascii=False)
        
        return cls(**data)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'EventTriggerRecord':
        """从JSON字符串创建对象"""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def is_deleted(self) -> bool:
        """检查事件是否已被删除"""
        return self.delete_time is not None


# --- Device Information Model ---

@dataclass
class DeviceRecord:
    """设备信息数据模型"""
    id: Optional[int] = None
    dev_eui: str = ""  # 设备EUI，CHAR(16)
    device_name: str = ""  # 设备名称，CHAR(20)
    group_id: int = 0  # 分组ID，0表示默认分组
    is_favorite: bool = False  # 是否收藏
    battery_level: Optional[int] = 0  # 电量（0-100），可为空
    create_time: Optional[datetime] = None  # 创建时间
    delete_time: Optional[datetime] = None  # 删除时间（软删除）
    last_data_update_time: Optional[datetime] = None  # 最后一次数据更新时间
    
    def __post_init__(self):
        if self.create_time is None:
            self.create_time = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典，方便JSON序列化"""
        data = asdict(self)
        # 转换datetime为字符串
        if self.create_time:
            data['create_time'] = self.create_time.isoformat()
        if self.delete_time:
            data['delete_time'] = self.delete_time.isoformat()
        if self.last_data_update_time:
            data['last_data_update_time'] = self.last_data_update_time.isoformat()
        return data
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DeviceRecord':
        """从字典创建对象"""
        # 转换字符串为datetime
        if 'create_time' in data and isinstance(data['create_time'], str):
            data['create_time'] = datetime.fromisoformat(data['create_time'])
        if 'delete_time' in data and isinstance(data['delete_time'], str):
            data['delete_time'] = datetime.fromisoformat(data['delete_time'])
        if 'last_data_update_time' in data and isinstance(data['last_data_update_time'], str):
            data['last_data_update_time'] = datetime.fromisoformat(data['last_data_update_time'])
        return cls(**data)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'DeviceRecord':
        """从JSON字符串创建对象"""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def is_deleted(self) -> bool:
        """检查设备是否已被删除"""
        return self.delete_time is not None


# --- Group Management Model ---

@dataclass
class GroupRecord:
    """分组管理数据模型"""
    id: Optional[int] = None
    group_name: str = ""
    create_time: Optional[datetime] = None
    delete_time: Optional[datetime] = None  # 软删除时间，None表示未删除
    
    def __post_init__(self):
        if self.create_time is None:
            self.create_time = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典，方便JSON序列化"""
        data = asdict(self)
        # 转换datetime为字符串
        if self.create_time:
            data['create_time'] = self.create_time.isoformat()
        if self.delete_time:
            data['delete_time'] = self.delete_time.isoformat()
        return data
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GroupRecord':
        """从字典创建对象"""
        # 转换字符串为datetime
        if 'create_time' in data and isinstance(data['create_time'], str):
            data['create_time'] = datetime.fromisoformat(data['create_time'])
        if 'delete_time' in data and isinstance(data['delete_time'], str):
            data['delete_time'] = datetime.fromisoformat(data['delete_time'])
        return cls(**data)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'GroupRecord':
        """从JSON字符串创建对象"""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def is_deleted(self) -> bool:
        """检查分组是否已被删除"""
        return self.delete_time is not None


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
    status: int = 1
    event_type: int = 1
    event_id: int = 1
    event_name: str = ""
    desc: Optional[Dict[str, Any]] = None
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


COORD_SYSTEM_METRIC = "metric"
COORD_SYSTEM_WGS84 = "wgs84"


class PositionHistoryEntry(BaseModel):
    """A single point of a tracker trail.

    Replaces the legacy ``(x, y, timestamp_ms)`` triple. Legacy triples are still
    accepted on input and read back as ``coordSystem="metric"`` (see
    ``TrackerState.position_history`` validator).
    """
    coordSystem: str = COORD_SYSTEM_METRIC  # metric | wgs84
    time: int = 0                           # unix ms
    # metric (indoor, map local frame)
    x: Optional[float] = None
    y: Optional[float] = None
    map: Optional[str] = None
    # wgs84 (outdoor)
    lat: Optional[float] = None
    lon: Optional[float] = None
    alt: Optional[float] = None
    accuracy: Optional[float] = None


def normalize_position_history(value: Any) -> Any:
    """Accept legacy ``[x, y, t]`` triples alongside PositionHistoryEntry dicts."""
    if not isinstance(value, (list, tuple)):
        return value
    normalized = []
    for item in value:
        if isinstance(item, PositionHistoryEntry):
            normalized.append(item)
        elif isinstance(item, (list, tuple)) and len(item) == 3:
            normalized.append(PositionHistoryEntry(
                coordSystem=COORD_SYSTEM_METRIC,
                x=float(item[0]), y=float(item[1]), time=int(item[2]),
            ))
        else:
            normalized.append(item)
    return normalized


class TrackerState(BaseModel):
    trackerId: str
    x: Optional[float] = None
    y: Optional[float] = None
    last_update_time: Optional[int] = 0 # Unix ms timestamp in ms (server time of this update)
    timestamp: Optional[int] = None # Unix ms timestamp (from original report)
    last_detected_beacons: List[DetectedBeacon] = []
    position_history: List[PositionHistoryEntry] = []  # trail, mixed metric/wgs84 segments
    used_beacons: List[DetectedBeacon] = []  # MAC addresses of beacons used in position calculation
    map: Optional[str] = "unknown"
    sos: int = 0
    type: Optional[str] = "calculation"
    radius: float = 0
    battery: Optional[int] = -1
    online: Optional[str] = "unknown"
    lat: Optional[float] = None
    lon: Optional[float] = None
    alt: Optional[float] = None
    accuracy: Optional[float] = None
    fix_time: Optional[int] = None  # unix ms of the GNSS fix

    @field_validator("position_history", mode="before")
    @classmethod
    def _coerce_position_history(cls, value):
        return normalize_position_history(value)

    def toTrackerInfo(self, device_record: DeviceRecord) -> "TrackerInfo":
        """将TrackerState和DeviceRecord合并转换为TrackerInfo"""
        # 创建TrackerInfo实例，合并两个对象的数据
        tracker_info = TrackerInfo(
            # TrackerState字段
            trackerId=self.trackerId,
            x=self.x,
            y=self.y,
            last_update_time=self.last_update_time,
            timestamp=self.timestamp,
            last_detected_beacons=self.last_detected_beacons,
            position_history=self.position_history,
            used_beacons=self.used_beacons,
            map=self.map,
            sos=self.sos,
            type=self.type,
            radius=self.radius,
            battery=self.battery,
            online=self.online,
            lat=self.lat,
            lon=self.lon,
            alt=self.alt,
            accuracy=self.accuracy,
            fix_time=self.fix_time,
            
            # DeviceRecord字段
            id=device_record.id,
            device_name=device_record.device_name,
            group_id=device_record.group_id,
            is_favorite=device_record.is_favorite,
        )
        if self.battery == -1:
            self.battery = device_record.battery_level
        return tracker_info

    @staticmethod
    def toTrackerState(deviceRecord: DeviceRecord) -> "TrackerState":
        """将TrackerInfo转换为TrackerState"""
        tracker_state = TrackerState(
            trackerId=deviceRecord.dev_eui,
            battery=deviceRecord.battery_level,
            online="unknown",
            sos=event_constant.SOS_STATUS_RECOVER
        )
        if deviceRecord.last_data_update_time:
            tracker_state.last_update_time = int(deviceRecord.last_data_update_time.timestamp()) * 1000
        return tracker_state


class TrackerInfo(BaseModel):
    """追踪器信息，包含TrackerState和DeviceRecord的所有字段"""
    # TrackerState字段
    trackerId: str
    tracker_number: Optional[int] = None
    x: Optional[float] = None
    y: Optional[float] = None
    last_update_time: int
    timestamp: Optional[int] = None
    last_detected_beacons: List[DetectedBeacon] = []
    position_history: List[PositionHistoryEntry] = []
    used_beacons: List[DetectedBeacon] = []
    map: Optional[str] = "unknown"
    sos: int = 0
    type: Optional[str] = "calculation"
    radius: float = 0
    battery: Optional[int] = -1
    online: Optional[str] = "unknown"
    lat: Optional[float] = None
    lon: Optional[float] = None
    alt: Optional[float] = None
    accuracy: Optional[float] = None
    fix_time: Optional[int] = None  # unix ms of the GNSS fix
    
    # DeviceRecord字段
    id: Optional[int] = None
    device_name: str = ""
    group_id: int = 0
    is_favorite: bool = False

    @field_validator("position_history", mode="before")
    @classmethod
    def _coerce_position_history(cls, value):
        return normalize_position_history(value)

    @staticmethod
    def fromDeviceRecord(device: DeviceRecord) -> "TrackerInfo":
        return TrackerInfo(
            trackerId=device.dev_eui,
            last_update_time=device.last_data_update_time.timestamp() * 1000,
            device_name=device.device_name,
            group_id=device.group_id,
            is_favorite=device.is_favorite
        )

    class Config:
        # 允许任意类型，因为包含datetime等复杂类型
        arbitrary_types_allowed = True


# --- Geofence Models (步骤 3) ---

@dataclass
class GeofenceRecord:
    """地理围栏数据模型.

    geometry_json 存 GeoJSON：多边形为 Polygon/MultiPolygon；
    圆形为 Point，半径写在 radius_m。
    """
    id: Optional[int] = None
    name: str = ""
    geometry_json: str = ""
    radius_m: Optional[float] = None
    crs: str = "wgs84"  # wgs84 | gcj02
    enabled: bool = True
    created_at: Optional[datetime] = None
    delete_time: Optional[datetime] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

    def is_deleted(self) -> bool:
        return self.delete_time is not None

    def get_geometry(self) -> Dict[str, Any]:
        try:
            return json.loads(self.geometry_json) if self.geometry_json else {}
        except json.JSONDecodeError:
            return {}

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        if self.created_at:
            data['created_at'] = self.created_at.isoformat()
        if self.delete_time:
            data['delete_time'] = self.delete_time.isoformat()
        data['geometry'] = self.get_geometry()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GeofenceRecord':
        data = dict(data)
        data.pop('geometry', None)
        if isinstance(data.get('created_at'), str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if isinstance(data.get('delete_time'), str):
            data['delete_time'] = datetime.fromisoformat(data['delete_time'])
        return cls(**data)


class GeofenceCreateRequest(BaseModel):
    """创建地理围栏请求"""
    name: str = Field(..., min_length=1, max_length=100, description="围栏名称")
    geometry: Dict[str, Any] = Field(..., description="GeoJSON 几何：Polygon/MultiPolygon/Point")
    radius_m: Optional[float] = Field(default=None, gt=0, description="圆形围栏半径（米），Point 时必填")
    crs: str = Field(default="wgs84", description="坐标系 wgs84|gcj02")
    enabled: bool = Field(default=True, description="是否启用")


class GeofenceUpdateRequest(BaseModel):
    """更新地理围栏请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    geometry: Optional[Dict[str, Any]] = None
    radius_m: Optional[float] = Field(None, gt=0)
    crs: Optional[str] = None
    enabled: Optional[bool] = None


class GeofenceListItem(BaseModel):
    """地理围栏列表项"""
    id: int
    name: str
    geometry: Dict[str, Any]
    radius_m: Optional[float] = None
    crs: str = "wgs84"
    enabled: bool = True
    created_at: str = ""
