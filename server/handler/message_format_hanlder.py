from typing import Optional

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
        beacon_values = None
        loc = None
        loc_type = message_constant.TRACKER_POSITIONING_TYPE_UNKNOWN
        sos = event_constant.SOS_STATUS_RECOVER
        battery = -1

        # 除了3000之外所有消息直接返回空, 收到3000, 汇总成完整的定位包
        match measurement_id:
            case '4197':
                UplinkCollector.set(dev_eui=device_eui, measurement_id=measurement_id, value=data.get("value"))
                return None
            case '4198':
                UplinkCollector.set(dev_eui=device_eui, measurement_id=measurement_id, value=data.get("value"))
                return None
            case '4200':
                UplinkCollector.set(dev_eui=device_eui, measurement_id=measurement_id, value=data.get("value", 0))
                return None
            case '5002':
                UplinkCollector.set(dev_eui=device_eui, measurement_id=measurement_id, value=data.get("value"))
                return None
            case '3000':
                battery = data.get("value", -1)
                UplinkCollector.set(dev_eui=device_eui, measurement_id=measurement_id, value=data.get("value", -1))
                await asyncio.sleep(1)
            case _:
                return None

        sos = UplinkCollector.get(dev_eui=device_eui, measurement_id='4200', default_value=0)
        altitude = UplinkCollector.get(dev_eui=device_eui, measurement_id='4197')
        longitude = UplinkCollector.get(dev_eui=device_eui, measurement_id='4198')
        beacon_values = UplinkCollector.get(dev_eui=device_eui, measurement_id='5002')
        if altitude and longitude:
            loc = {
                "alt": altitude,
                "lon": longitude
            }
            loc_type = 'gps'
            UplinkCollector.set(dev_eui=device_eui, measurement_id='loc', value=loc)
            UplinkCollector.set(dev_eui=device_eui, measurement_id='loc_type', value=loc_type)
            return TrackerReport(
                trackerId=device_eui,
                timestamp=payload_timestamp,
                detectedBeacons=beacon_values,
                battery=battery,
                loc=loc,
                loc_type=loc_type,
                sourceType=message_constant.SOURCE_FROM_SENSECAP
            )

        beacon_values = UplinkCollector.get(dev_eui=device_eui, measurement_id='5002')
        if not isinstance(beacon_values, list):
            return TrackerReport(
                trackerId=device_eui,
                timestamp=payload_timestamp,
                battery=battery,
                sos=sos,
                detectedBeacons=[],
                loc={},
                locType=message_constant.TRACKER_POSITIONING_TYPE_UNKNOWN,
                sourceType=message_constant.SOURCE_FROM_SENSECAP
            )

        detected_beacons_list = []
        for beacon_data in beacon_values:
            if not isinstance(beacon_data, dict):
                # log.debug(f"Skipping non-dict item in 'value' list for {device_eui}: {beacon_data}") # DEBUG
                continue

            mac_address = beacon_data.get("mac")
            rssi_str = beacon_data.get("rssi")

            if mac_address and rssi_str is not None:
                try:
                    mac_addr_upper = str(mac_address).upper()
                    rssi_val = int(rssi_str)
                    detected = DetectedBeacon(
                        macAddress=mac_addr_upper,
                        rssi=rssi_val
                    )
                    detected_beacons_list.append(detected)
                except (ValueError, TypeError) as conv_err:
                    log.warning(f"Could not convert beacon data for {device_eui}: {beacon_data} - {conv_err}")
            else:
                # log.debug(f"Skipping beacon entry for {device_eui} due to missing mac or rssi: {beacon_data}") # DEBUG
                pass  # Keep it quiet

        if not detected_beacons_list:
            # log.info(f"No valid beacons found in SenseCAP payload for tracker {device_eui} after parsing 'value' list.") # Can be noisy
            pass
        return TrackerReport(
            trackerId=device_eui,
            timestamp=payload_timestamp,
            detectedBeacons=detected_beacons_list,
            locType=message_constant.TRACKER_POSITIONING_TYPE_BLE,
            loc={},
            battery=battery,
            sos=sos,
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
    ChirpStack typically sends uplink data in a different format than SenseCAP.
    Topic format example: application/[appID]/device/[devEUI]/event/up
    Payload example: {"applicationID":"1","applicationName":"indoor-positioning",
                     "deviceName":"tracker-001","devEUI":"2CF7F1C0530004AD",
                     "rxInfo":[...],"txInfo":{...},"object":{"beacons":[{"mac":"C3:00:00:3E:7D:DA","rssi":-53}]}}
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
        gps_value = {}
        sos_value = 0
        battery = -1
        for entry in messages[0]:
            if entry.get('timestamp', 0):
                payload_timestamp = int(entry.get('timestamp', 0))
            measurement_id = entry.get('measurementId', 0)
            measurement_value = entry.get('measurementValue', 0)
            if measurement_value:
                UplinkCollector.set(dev_eui=device_eui, measurement_id=measurement_id,
                                    value=entry.get('measurementValue', 0))

            match measurement_id:
                case '3000':
                    battery = entry.get('measurementValue', -1)
                case '4197':
                    gps_value['alt'] = entry.get('measurementValue', 0)
                case '4198':
                    gps_value['lon'] = entry.get('measurementValue', 0)
                case '5002':
                    beacon_values = entry.get('measurementValue', 0)
                case '4200':
                    event_list = entry.get('measurementValue', 0)
                    for event in event_list:
                        if event.get("id", 0) == 7:
                            sos_value = 1

        if len(gps_value) > 0:
            return TrackerReport(
                trackerId=device_eui,
                timestamp=payload_timestamp,
                sos=sos_value,
                locType="gps",
                loc=gps_value,
                sourceType="chirpstack",
                battery=battery
            )

        if not beacon_values or len(beacon_values) == 0:
            log.info(f'Detected tracker SOS from ChirpStack: {device_eui}, value: {sos_value}')
            return TrackerReport(
                trackerId=device_eui,
                timestamp=payload_timestamp,
                sos=sos_value,
                battery=battery
            )

        if not isinstance(beacon_values, list):
            log.warning(f"Invalid 'beacons' data in ChirpStack payload for {device_eui}. Expected list.")
            return TrackerReport(
                trackerId=device_eui,
                timestamp=payload_timestamp,
                detectedBeacons=[],
                loc={},
                battery=battery
            )

        detected_beacons_list = []
        for beacon_data in beacon_values:
            if not isinstance(beacon_data, dict):
                continue

            mac_address = beacon_data.get("mac") or beacon_data.get("macAddress")
            rssi_val = beacon_data.get("rssi")

            if mac_address and rssi_val is not None:
                try:
                    mac_addr_upper = str(mac_address).upper()
                    rssi_int = int(rssi_val)
                    detected = DetectedBeacon(
                        macAddress=mac_addr_upper,
                        rssi=rssi_int
                    )
                    detected_beacons_list.append(detected)
                except (ValueError, TypeError) as conv_err:
                    log.warning(f"Could not convert ChirpStack beacon data for {device_eui}: {beacon_data} - {conv_err}")

        return TrackerReport(
            trackerId=device_eui,
            timestamp=payload_timestamp,
            detectedBeacons=detected_beacons_list,
            locType="bluetooth",
            loc={},
            sos=sos_value,
            sourceType="chirpstack",
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
