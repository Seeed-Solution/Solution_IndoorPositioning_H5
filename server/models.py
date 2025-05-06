# server/models.py
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

# --- Configuration Models ---

class MapEntity(BaseModel):
    type: str
    points: List[List[float]]
    closed: Optional[bool] = None
    color: Optional[str] = None
    lineWidth: Optional[float] = None
    # Add other potential entity fields if needed

class MapInfo(BaseModel):
    width: float
    height: float
    entities: List[MapEntity]

class BeaconConfig(BaseModel):
    macAddress: str = Field(..., description="BLE MAC address of the beacon (e.g., C3:00:00:3E:7D:EF)")
    major: Optional[int] = None # Keep if needed, but not in example payload
    minor: Optional[int] = None # Keep if needed, but not in example payload
    name: Optional[str] = None
    txPower: int # RSSI at 1m
    x: float # meters
    y: float # meters

class MqttConfig(BaseModel):
    brokerHost: str = "localhost"
    brokerPort: int = 1883
    username: Optional[str] = None
    password: Optional[str] = None
    applicationID: str = "your_chirpstack_application_id" # Match LoRaWAN Server App ID
    topicPattern: str = "application/{ApplicationID}/device/+/event/up"

class ServerConfig(BaseModel):
    port: int = 8000

class CommonSettings(BaseModel):
    signalPropagationFactor: float = 2.5 # Default value (n in path loss model)
    kalmanProcessVariance: float = 1.0 # Uncertainty in motion model
    kalmanMeasurementVariance: float = 10.0 # Uncertainty in position measurement

class ConfigData(BaseModel):
    mapInfo: MapInfo
    beacons: List[BeaconConfig]
    settings: CommonSettings
    mqtt: MqttConfig
    server: ServerConfig

# --- Tracker Data Models ---

class DetectedBeacon(BaseModel):
    macAddress: str = Field(..., description="BLE MAC address detected")
    major: Optional[int] = None
    minor: Optional[int] = None
    rssi: int

class TrackerReport(BaseModel):
    trackerId: str # Corresponds to device devEui
    timestamp: int # Unix ms timestamp from message
    detectedBeacons: List[DetectedBeacon]
    # Optional: Add other fields from LoRaWAN if needed later
    # e.g., raw_payload: Optional[str] = None, gateway_info: Optional[Any] = None

class TrackerState(BaseModel):
    trackerId: str
    x: Optional[float] = None
    y: Optional[float] = None
    last_update_time: int # Unix ms timestamp (server time)
    last_known_measurement_time: Optional[int] = None # Unix ms timestamp (from report)
    last_detected_beacons: List[DetectedBeacon] = [] 