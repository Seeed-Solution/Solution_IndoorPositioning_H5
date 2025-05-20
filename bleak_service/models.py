from typing import Optional, List, Dict, Any
from pydantic import BaseModel

class BeaconData(BaseModel):
    id: str
    address: str
    rssi: int
    localName: Optional[str] = None
    txPowerAdv: Optional[int] = None
    iBeacon: Optional[Dict[str, Any]] = None

class WebSocketMessage(BaseModel):
    type: str
    message: Optional[str] = None
    data: Optional[BeaconData] = None

class ClientCommand(BaseModel):
    command: str
    ignoredMacAddresses: Optional[List[str]] = [] 