from typing import Any, List, Optional

from server.models import (
    TrackerReport, DetectedBeacon
)

from server.components.uplink_collector import UplinkCollector

import server.constant.message_constant as message_constant
import server.constant.event_constant as event_constant

import asyncio
import json
import datetime
import time

import logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


# SenseCAP / ChirpStack measurement ids used for positioning.
#   4197 -> longitude, 4198 -> latitude  (per the SenseCAP T1000 uplink protocol)
#   4200 -> SOS event, 5002 -> BLE scan result, 3000 -> battery, 5003 -> event list
MEASUREMENT_LONGITUDE = '4197'
MEASUREMENT_LATITUDE = '4198'
MEASUREMENT_SOS = '4200'
MEASUREMENT_BEACONS = '5002'
MEASUREMENT_BATTERY = '3000'
MEASUREMENT_EVENTS = '5003'


def _to_float(value: Any) -> Optional[float]:
    """Convert a measurement value to float. Returns None when not convertible."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def build_gnss_loc(longitude: Any, latitude: Any) -> dict:
    """Build the WGS84 loc dict from raw measurement values.

    A fix is only accepted when BOTH longitude and latitude are present.  ``0.0``
    is a legal coordinate, so presence is checked with ``is not None`` rather
    than truthiness (the previous ``if altitude and longitude`` dropped every
    fix that sat exactly on the equator / prime meridian).
    """
    lon = _to_float(longitude)
    lat = _to_float(latitude)
    if lon is None or lat is None:
        return {}
    return {"lat": lat, "lon": lon}


def parse_beacon_list(beacon_values: Any, device_eui: str) -> List[DetectedBeacon]:
    """Parse a raw 5002 scan-result list into DetectedBeacon objects."""
    if not isinstance(beacon_values, list):
        return []
    detected_beacons_list: List[DetectedBeacon] = []
    for beacon_data in beacon_values:
        if not isinstance(beacon_data, dict):
            continue
        mac_address = beacon_data.get("mac") or beacon_data.get("macAddress")
        rssi_val = beacon_data.get("rssi")
        if mac_address and rssi_val is not None:
            try:
                detected_beacons_list.append(DetectedBeacon(
                    macAddress=str(mac_address).upper(),
                    rssi=int(rssi_val)
                ))
            except (ValueError, TypeError) as conv_err:
                log.warning(f"Could not convert beacon data for {device_eui}: {beacon_data} - {conv_err}")
    return detected_beacons_list


def resolve_loc_type(loc: dict, detected_beacons: List[DetectedBeacon]) -> str:
    """这一包携带的定位数据种类: 有 GNSS fix 记 gps, 否则有 beacon 记 bluetooth.

    注意区分两个概念: 这里是"上行里有什么", 是逐包的事实;
    界面展示的室内/室外 (``TrackerState.type``) 由
    ``server/handler/indoor_outdoor.py`` 的迟滞状态机决定, 不逐包翻转.
    """
    if loc:
        return message_constant.TRACKER_POSITIONING_TYPE_GPS
    if detected_beacons:
        return message_constant.TRACKER_POSITIONING_TYPE_BLE
    return message_constant.TRACKER_POSITIONING_TYPE_UNKNOWN


async def parse_sensecap_payload(topic: str, payload_bytes: bytes) -> Optional[TrackerReport]:
    """
    Parses the SenseCAP-like payload (JSON string) for beacon data.
    Assumes topic provides DeviceEUI, and payload contains timestamp and beacon list.
    Payload example: {"value":[{"mac":"C3:00:00:3E:7D:DA","rssi":"-53"}, ...],"timestamp":1746522494000}
    """
    device_eui = ''
    measurement_id = ''
    try:
        # SenseCAP topic format: /device_sensor_data/{ApplicationID}/+/+/+/+
        topic_parts = topic.split('/')
        if not topic.startswith('/device_sensor_data/') or len(topic_parts) < 7:
            log.warning(f"Received message on unexpected SenseCAP topic structure: {topic}")
            return
        device_eui = topic_parts[3].upper()
        measurement_id = topic_parts[6]
        data = json.loads(payload_bytes.decode('utf-8'))

        payload_timestamp = data.get("timestamp")
        if payload_timestamp is None:
            log.warning(f"Missing 'timestamp' in SenseCAP payload for {device_eui}. Using current time.")
            payload_timestamp = int(time.time() * 1000)
        else:
            try:
                payload_timestamp = int(payload_timestamp)
            except ValueError:
                log.warning(f"Invalid 'timestamp' format in SenseCAP payload for {device_eui}. Using current time.")
                payload_timestamp = int(time.time() * 1000)

        UplinkCollector.set(dev_eui=device_eui, measurement_id='timestamp', value=payload_timestamp)
        battery = -1

        # 除了3000之外所有消息直接返回空, 收到3000, 汇总成完整的定位包
        if measurement_id in (MEASUREMENT_LONGITUDE, MEASUREMENT_LATITUDE, MEASUREMENT_BEACONS):
            UplinkCollector.set(dev_eui=device_eui, measurement_id=measurement_id, value=data.get("value"))
            return None
        elif measurement_id == MEASUREMENT_SOS:
            UplinkCollector.set(dev_eui=device_eui, measurement_id=measurement_id, value=data.get("value", 0))
            return None
        elif measurement_id == MEASUREMENT_BATTERY:
            battery = data.get("value", -1)
            UplinkCollector.set(dev_eui=device_eui, measurement_id=measurement_id, value=battery)
            await asyncio.sleep(1)
        else:
            return None

        sos = UplinkCollector.get(dev_eui=device_eui, measurement_id=MEASUREMENT_SOS, default_value=0)
        longitude = UplinkCollector.get(dev_eui=device_eui, measurement_id=MEASUREMENT_LONGITUDE)
        latitude = UplinkCollector.get(dev_eui=device_eui, measurement_id=MEASUREMENT_LATITUDE)
        beacon_values = UplinkCollector.get(dev_eui=device_eui, measurement_id=MEASUREMENT_BEACONS)

        loc = build_gnss_loc(longitude, latitude)
        detected_beacons_list = parse_beacon_list(beacon_values, device_eui)
        loc_type = resolve_loc_type(loc, detected_beacons_list)

        # 同一个包里同时带 GNSS 和 BLE 时, 生成一个组合报告, 两类数据都保留.
        return TrackerReport(
            trackerId=device_eui,
            timestamp=payload_timestamp,
            detectedBeacons=detected_beacons_list,
            battery=battery,
            sos=sos,
            loc=loc,
            locType=loc_type,
            sourceType=message_constant.SOURCE_FROM_SENSECAP
        )

    except json.JSONDecodeError:
        log.error(f"Failed to decode JSON payload for {device_eui}: {payload_bytes.decode('utf-8', errors='ignore')}")
        return None
    except Exception as e:
        log.error(f"Error processing SenseCAP MQTT payload for tracker '{device_eui}': {e}", exc_info=True)
        return None


async def parse_chirpstack_payload(topic: str, payload_bytes: bytes) -> Optional[TrackerReport]:
    """
    Parses ChirpStack MQTT payload for beacon data.
    Topic format example: application/[appID]/device/[devEUI]/event/up
    The decoded payload carries object.messages[0] as a list of
    {"measurementId": "...", "measurementValue": ..., "timestamp": ...} entries.
    """
    topic_parts = topic.split('/')
    if len(topic_parts) < 6 or topic_parts[0] != 'application' or topic_parts[2] != 'device':
        log.warning(f"Received message on unexpected ChirpStack topic structure: {topic}")
        return
    device_eui = topic_parts[3].upper()
    try:
        data = json.loads(payload_bytes.decode('utf-8'))
        log.debug(f"Raw ChirpStack MQTT data for {device_eui}: {data}")

        # Extract beacon data from object field
        object_data = data.get("object", {})
        messages = object_data.get("messages", [])

        if not messages or len(messages) == 0:
            log.warning(f"device: {device_eui}, empty packet. so break. ")
            return None

        payload_timestamp = 0
        beacon_values = []
        longitude = None
        latitude = None
        sos_value = 0
        battery = -1
        for entry in messages[0]:
            if entry.get('timestamp', 0):
                payload_timestamp = int(entry.get('timestamp', 0))
            measurement_id = entry.get('measurementId', 0)
            measurement_value = entry.get('measurementValue', 0)
            if measurement_value is not None:
                UplinkCollector.set(dev_eui=device_eui, measurement_id=measurement_id,
                                    value=measurement_value)

            if measurement_id == MEASUREMENT_BATTERY:
                battery = entry.get('measurementValue', -1)
            elif measurement_id == MEASUREMENT_LONGITUDE:
                longitude = entry.get('measurementValue')
            elif measurement_id == MEASUREMENT_LATITUDE:
                latitude = entry.get('measurementValue')
            elif measurement_id == MEASUREMENT_BEACONS:
                beacon_values = measurement_value or []
            elif measurement_id == MEASUREMENT_EVENTS:
                for event in measurement_value or []:
                    if isinstance(event, dict) and event.get("id", 0) == 7:
                        sos_value = 1

        loc = build_gnss_loc(longitude, latitude)
        detected_beacons_list = parse_beacon_list(beacon_values, device_eui)
        loc_type = resolve_loc_type(loc, detected_beacons_list)

        if not loc and not detected_beacons_list:
            log.info(f'ChirpStack uplink without position for {device_eui}, sos: {sos_value}')

        # GNSS 不再提前返回: 同一个包里的 beacon 继续解析, 组合成一个报告.
        return TrackerReport(
            trackerId=device_eui,
            timestamp=payload_timestamp,
            detectedBeacons=detected_beacons_list,
            locType=loc_type,
            loc=loc,
            sos=sos_value,
            sourceType=message_constant.SOURCE_FROM_CHIRPSTACK,
            battery=battery
        )

    except json.JSONDecodeError:
        log.error(f"Failed to decode JSON payload from ChirpStack for {device_eui}: {payload_bytes.decode('utf-8', errors='ignore')}")
        return None
    except Exception as e:
        log.error(f"Error processing ChirpStack MQTT payload for tracker '{device_eui}': {e}", exc_info=True)
        return None


async def do(topic: str, payload_bytes: bytes, source_type: str = "chirpstack") -> Optional[TrackerReport]:
    if source_type == message_constant.SOURCE_FROM_SENSECAP:
        return await parse_sensecap_payload(topic, payload_bytes)
    elif source_type == message_constant.SOURCE_FROM_CHIRPSTACK:
        return await parse_chirpstack_payload(topic, payload_bytes)
    else:
        log.warning(f"Unknown source type: {source_type}, topic: {topic}")
        return
