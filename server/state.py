# server/state.py
import json
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, List

from .models import ConfigData, TrackerReport, DetectedBeacon
from .positioning import calculate_position, KalmanFilter2D
from .main import manager

# --- Constants ---
CONFIG_FILE = "config.json"
TRACKER_STALE_TIMEOUT = timedelta(seconds=60)
KF_PROCESS_VARIANCE = 0.5
KF_MEASUREMENT_VARIANCE = 15.0

# --- State Variables ---
tracker_states: Dict[str, Dict] = {}
current_config: Optional[ConfigData] = None

def load_config() -> Optional[ConfigData]:
    """Loads configuration from config.json."""
    global current_config
    try:
        with open(CONFIG_FILE, 'r') as f:
            config_dict = json.load(f)
            current_config = ConfigData(**config_dict)
            print("Configuration loaded successfully.")
            return current_config
    except FileNotFoundError:
        print(f"Error: {CONFIG_FILE} not found.")
        current_config = None
        return None
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {CONFIG_FILE}.")
        current_config = None
        return None
    except Exception as e: # Catch other potential errors like Pydantic validation
        print(f"Error loading configuration: {e}")
        current_config = None
        return None

def save_config(config: ConfigData):
    """Saves configuration to config.json."""
    global current_config
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config.dict(), f, indent=2)
        current_config = config # Update in-memory cache
        print(f"Configuration saved to {CONFIG_FILE}.")
    except Exception as e:
        print(f"Error saving configuration: {e}")

def get_current_config() -> Optional[ConfigData]:
    """Returns the currently loaded configuration."""
    return current_config

def get_tracker_states() -> Dict[str, Dict]:
    """Returns the current state of all non-stale trackers."""
    now = datetime.now()
    active_states = {}
    stale_trackers = []
    for tracker_id, state in tracker_states.items():
        last_update = state.get('last_update_time', None)
        # Check if state has last_update_time and if it's recent
        if last_update and (now - last_update < TRACKER_STALE_TIMEOUT):
            active_states[tracker_id] = {
                 "x": state.get("x"),
                 "y": state.get("y"),
                 "last_seen": state.get("last_seen"),
             }
        elif last_update: # Tracker is stale
            stale_trackers.append(tracker_id)

    # Clean up stale trackers from the main state dictionary
    if stale_trackers:
        print(f"Removing stale trackers: {stale_trackers}")
        for tracker_id in stale_trackers:
             # Use pop with default to avoid KeyError if already removed by another process
            tracker_states.pop(tracker_id, None)

    return active_states

async def update_tracker_state(report: TrackerReport):
    """
    Updates the state of a tracker based on a report, calculates position,
    applies Kalman filter, and broadcasts the update.
    """
    global tracker_states
    if not current_config:
        print("Warning: Cannot process tracker report, configuration not loaded.")
        return

    tracker_id = report.tracker_id
    now = datetime.now()
    now_str = now.isoformat()

    # --- Calculate Raw Position ---
    # Determine last known position for initial guess
    last_known_pos = None
    if tracker_id in tracker_states and tracker_states[tracker_id].get('x') is not None:
        last_known_pos = (tracker_states[tracker_id]['x'], tracker_states[tracker_id]['y'])

    raw_position = calculate_position(
        report.beacons,
        current_config,
        last_known_position=last_known_pos
    )

    # --- Kalman Filter Update ---
    filtered_position = None
    kf = tracker_states.get(tracker_id, {}).get('kalman_filter')
    last_update_time = tracker_states.get(tracker_id, {}).get('last_update_time')

    if kf and last_update_time:
        dt = (now - last_update_time).total_seconds()
        if dt > 0: # Avoid division by zero or nonsensical dt
             kf.predict(dt)
        else:
             print(f"Warning: Non-positive dt ({dt}) for Kalman predict, skipping predict step.")

        if raw_position:
            kf.update(raw_position)
            filtered_position = kf.get_position()
        else:
            # No new measurement, use predicted position
            filtered_position = kf.get_position()
            print(f"Tracker {tracker_id}: No raw position, using KF prediction.")

    elif raw_position:
        # First time seeing tracker OR filter wasn't initialized, and we have a position
        print(f"Initializing Kalman filter for tracker {tracker_id} at {raw_position}")
        kf = KalmanFilter2D(
            initial_pos=raw_position,
            process_variance=KF_PROCESS_VARIANCE,
            measurement_variance=KF_MEASUREMENT_VARIANCE
        )
        filtered_position = raw_position # Use raw position for the first update

    else:
        # No previous state and no current raw position - cannot estimate
        print(f"Tracker {tracker_id}: No raw position and no prior state, cannot estimate position.")
        filtered_position = None


    # --- Update State Dictionary ---
    current_state = tracker_states.get(tracker_id, {})
    current_state.update({
        'last_seen': now_str,
        'beacons': [b.dict() for b in report.beacons], # Store raw beacon data
        'x': filtered_position[0] if filtered_position else current_state.get('x'), # Keep old if no update
        'y': filtered_position[1] if filtered_position else current_state.get('y'), # Keep old if no update
        'raw_x': raw_position[0] if raw_position else None, # Store for debugging?
        'raw_y': raw_position[1] if raw_position else None,
        'kalman_filter': kf, # Store the filter object itself
        'last_update_time': now # Store timestamp for dt calculation
    })
    tracker_states[tracker_id] = current_state


    # --- Broadcast Update ---
    update_message = {
        "type": "tracker_update",
        "data": {
            tracker_id: {
                "x": current_state['x'],
                "y": current_state['y'],
                "last_seen": now_str,
                # Include velocity?
                # "vx": kf.get_velocity()[0] if kf else 0,
                # "vy": kf.get_velocity()[1] if kf else 0,
            }
        }
    }
    await manager.broadcast(json.dumps(update_message))

    print(f"Tracker {tracker_id} state updated: Raw={raw_position}, Filtered=({filtered_position[0]}, {filtered_position[1]})")

# --- Initialization ---
# Load config on startup
load_config() 