
from server.models import TrackerState

from server.components.beacon_holder import beacon_holder

MESSAGE_TYPE_TRACKER_UPDATE = "tracker_update"
MESSAGE_TYPE_TRACKER_SOS = "tracker_sos"
MESSAGE_TYPE_TRACKER_LOC_APPR = "tracker_location_approximate"
MESSAGE_TYPE_TRACKER_CHECKIN = "tracker_checkin"
MESSAGE_TYPE_TRACKER_POSITION_DETECTION = "tracker_position_detection"
MESSAGE_TYPE_TRACKER_OFFLINE = "tracker_offline"


TRACKER_POSITIONING_TYPE_GPS = "gps"
TRACKER_POSITIONING_TYPE_WIFI = "wifi"
TRACKER_POSITIONING_TYPE_BLE = "bluetooth"
TRACKER_POSITIONING_TYPE_UNKNOWN = "unknown"

TRACKER_STATE_TYPE_BLE_RANGE = "approximate"
TRACKER_STATE_TYPE_BLE_CAL = "calculation"
TRACKER_STATE_TYPE_WGS84 = "wGS84"
TRACKER_STATE_TYPE_BLE_UNKNOWN = "unknown"
TRACKER_STATE_TYPE_BLE_FAILED = "ble_failed"

SOURCE_FROM_SENSECAP = "sensecap"
SOURCE_FROM_CHIRPSTACK = "chirpstack"


def get_sos_message(state: TrackerState) -> dict:
    return {
            "type": MESSAGE_TYPE_TRACKER_SOS,
            "data": {state.trackerId: {
                "timestamp": state.last_known_measurement_time,
                "sos": state.sos
            }}
        }


def get_checkin_message(state: TrackerState) -> dict:
    return {
        "type": MESSAGE_TYPE_TRACKER_CHECKIN,
        "data": {state.trackerId: {
            "timestamp": state.last_known_measurement_time,
            "map": state.map,
            "last_detected_beacons": [
                {
                    "name": beacon_holder.get_beacon(beacon.macAddress).displayName,
                    "configured_x": beacon_holder.get_beacon(beacon.macAddress).x,
                    "configured_y": beacon_holder.get_beacon(beacon.macAddress).y
                } for beacon in state.used_beacons
            ]
        }}
    }


def get_leaving_message(state: TrackerState) -> dict:
    return {
        "type": MESSAGE_TYPE_TRACKER_POSITION_DETECTION,
        "data": {state.trackerId: {
            "timestamp": state.last_known_measurement_time,
            "map": state.map,
            "last_detected_beacons": [
                {
                    "name": beacon_holder.get_beacon(beacon.macAddress).displayName,
                    "configured_x": beacon_holder.get_beacon(beacon.macAddress).x,
                    "configured_y": beacon_holder.get_beacon(beacon.macAddress).y
                } for beacon in state.used_beacons
            ]
        }}
    }

def get_tracker_update(state: TrackerState) -> dict:
    position_payload = None
    if state.x is not None and state.y is not None:
        position_payload = {"x": state.x, "y": state.y}
    tracker_data_payload = {
        "trackerId": state.trackerId,
        "timestamp": state.last_known_measurement_time,
        "position": position_payload,
        "last_detected_beacons": [
            {
                "name": beacon_holder.get_beacon(beacon.macAddress).displayName,
                "configured_x": beacon_holder.get_beacon(beacon.macAddress).x,
                "configured_y": beacon_holder.get_beacon(beacon.macAddress).y
            } for beacon in state.used_beacons
        ],
        "position_history": state.position_history,
        "map": state.map,
        "sos": state.sos
    }
    return {
        "type": MESSAGE_TYPE_TRACKER_UPDATE,
        "data": {state.trackerId: tracker_data_payload}
    }


def get_tracker_loc_appr(state: TrackerState) -> dict:
    tracker_data_payload = {
        "trackerId": state.trackerId,
        "timestamp": state.last_known_measurement_time,
        "radius": state.radius,
        "last_detected_beacons": [
            {
                "name": beacon_holder.get_beacon(beacon.macAddress).displayName,
                "configured_x": beacon_holder.get_beacon(beacon.macAddress).x,
                "configured_y": beacon_holder.get_beacon(beacon.macAddress).y
            } for beacon in state.used_beacons
        ],  # Use the enriched list
        "map": state.map,
        "sos": state.sos
    }
    return {
            "type": MESSAGE_TYPE_TRACKER_LOC_APPR,
            "data": {state.trackerId: tracker_data_payload}
        }
