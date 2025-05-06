# server/config_manager.py
import json
from pathlib import Path
from typing import Optional, Tuple
from .models import ConfigData

CONFIG_FILE_PATH = Path("server/config.json") # Relative to project root for FastAPI running from root
current_config: Optional[ConfigData] = None

def load_config() -> Optional[ConfigData]:
    """Loads config from file if it exists."""
    global current_config
    if CONFIG_FILE_PATH.is_file():
        try:
            with open(CONFIG_FILE_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
                current_config = ConfigData(**data)
                print(f"Configuration loaded successfully from {CONFIG_FILE_PATH}")
                return current_config
        except Exception as e:
            print(f"Error loading configuration: {e}")
            current_config = None
            return None
    else:
        print(f"Configuration file not found at {CONFIG_FILE_PATH}")
        current_config = None
        return None

def save_config(config_data: ConfigData) -> bool:
    """Saves config data to the file."""
    global current_config
    try:
        with open(CONFIG_FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(config_data.dict(), f, indent=2)
        current_config = config_data
        print(f"Configuration saved successfully to {CONFIG_FILE_PATH}")
        return True
    except Exception as e:
        print(f"Error saving configuration: {e}")
        return False

def get_config() -> Optional[ConfigData]:
    """Returns the currently loaded config."""
    if current_config is None:
        load_config() # Attempt to load if not already loaded
    return current_config

def get_beacon_by_identifier(mac_address: str, major: Optional[int], minor: Optional[int]) -> Optional[Tuple[float, float, int]]:
    """Finds beacon coordinates and txPower by MAC Address, Major, Minor."""
    config = get_config()
    if not config:
        return None
    for beacon in config.beacons:
        if (beacon.macAddress.lower() == mac_address.lower() and
                beacon.major == major and
                beacon.minor == minor):
            return (beacon.x, beacon.y, beacon.txPower)
    return None

# Initial load attempt when the module is imported
load_config() 