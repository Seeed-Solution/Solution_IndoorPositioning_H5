
from typing import List, Dict, Optional, Tuple
import time

from server.models import (
    TrackerReport, DetectedBeacon, TrackerState
)

from server.components.device_holder import device_holder
from server.components.beacon_holder import beacon_holder
from server.components.uplink_collector import UplinkCollector

import server.constant.message_constant as message_constant
import server.constant.event_constant as event_constant

import server.config.config_manager as config_manager

from server.positioning import KalmanFilter2D
from server import positioning

import logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

kalman_filters: Dict[str, KalmanFilter2D] = {}  # Stores Kalman filter instance per tracker


# 主要针对蓝牙定位: 1. 解析出所在地图, 2. 计算出每个beacon的距离, 3.根据定位方式解算结果
def do(report: TrackerReport) -> TrackerState:
    try:
        global kalman_filters
        current_time_ms = int(time.time() * 1000)
        if report.locType == message_constant.TRACKER_POSITIONING_TYPE_GPS:
            return TrackerState(
                trackerId=report.trackerId,
                last_update_time=current_time_ms,
                last_known_measurement_time=report.timestamp,
                last_detected_beacons=[],
                map="",
                sos=report.sos,
                battery=report.battery,
                type=message_constant.TRACKER_STATE_TYPE_WGS84,
                x=report.loc.get("alt"),
                y=report.loc.get("lon"),
                online=event_constant.ONLINE_STATUS_ACTIVE
            )
        if report.locType != message_constant.TRACKER_POSITIONING_TYPE_BLE:
            return TrackerState(
                trackerId=report.trackerId,
                last_update_time=current_time_ms,
                last_known_measurement_time=report.timestamp,
                sos=report.sos,
                battery=report.battery,
                type=message_constant.TRACKER_STATE_TYPE_BLE_UNKNOWN,
                online=event_constant.ONLINE_STATUS_ACTIVE
            )
        # 非蓝牙定位, 不需要进入后面的部分
        if len(report.detectedBeacons) == 0:
            return TrackerState(
                trackerId=report.trackerId,
                last_update_time=current_time_ms,
                last_known_measurement_time=report.timestamp,
                sos=report.sos,
                battery=report.battery,
                type=message_constant.TRACKER_STATE_TYPE_BLE_UNKNOWN,
                online=event_constant.ONLINE_STATUS_ACTIVE
            )

        log.info(f"开始进行蓝牙定位计算: eui=>{report.trackerId}")
        tracker_id = report.trackerId

        last_state = device_holder.get_tracker_state(tracker_id)
        last_known_pos = (
            last_state.x,
            last_state.y) if last_state and last_state.x is not None and last_state.y is not None else None
        dt = (current_time_ms - last_state.last_update_time) / 1000.0 if last_state else 0.1

        current_position_history = list(
            last_state.position_history) if last_state and last_state.position_history else []

        best_map = "unknown map"
        best_beacons: list[DetectedBeacon] = []
        max_beacon_count = 0

        beacons_by_map = {}
        for detected in report.detectedBeacons:
            mac_formatted = detected.macAddress.replace(":", "")
            beacon_info = beacon_holder.get_beacon(mac_formatted)
            if beacon_info is None:
                continue
            detected.name = beacon_info.displayName
            detected.configured_x = beacon_info.x
            detected.configured_y = beacon_info.y
            if beacons_by_map.get(beacon_info.map, None) is None:
                beacons_by_map[beacon_info.map] = []
            beacons_by_map[beacon_info.map].append(detected)

        for map_name, map_beacons in beacons_by_map.items():
            if len(map_beacons) > max_beacon_count:
                max_beacon_count = len(map_beacons)
                best_map = map_name
                best_beacons = map_beacons

        if len(best_beacons) == 0:
            log.info(f"device(id: {tracker_id}) can not find effective beacon..")
            return TrackerState(
                trackerId=report.trackerId,
                last_update_time=current_time_ms,
                last_known_measurement_time=report.timestamp,
                sos=report.sos,
                battery=report.battery,
                type=message_constant.TRACKER_STATE_TYPE_BLE_FAILED,
                map=best_map,
                last_detected_beacons=report.detectedBeacons,
                online=event_constant.ONLINE_STATUS_ACTIVE
            )
        log.info(f"device(id: {tracker_id}): choose map '{best_map}' length of beacons: {len(best_beacons)} ")

        dashboard_cfg = config_manager.get_dashboard_config()
        if not dashboard_cfg or len(dashboard_cfg.maps) == 0:
            log.error(f"positioning resolve error:  dashboard config is NULL....")
            return TrackerState(
                trackerId=report.trackerId,
                last_update_time=current_time_ms,
                last_known_measurement_time=report.timestamp,
                sos=report.sos,
                battery=report.battery,
                type=message_constant.TRACKER_STATE_TYPE_BLE_FAILED,
                map=best_map,
                last_detected_beacons=report.detectedBeacons,
                online=event_constant.ONLINE_STATUS_ACTIVE
            )

        map_config = None

        for map_setting in dashboard_cfg.maps:
            if map_setting.map.name == best_map:
                map_config = map_setting

        if not map_config:
            log.error(
                f"positioning resolve error: there is not any map named {best_map}, please check dashboard-config....")
            return TrackerState(
                trackerId=report.trackerId,
                last_update_time=current_time_ms,
                last_known_measurement_time=report.timestamp,
                sos=report.sos,
                battery=report.battery,
                type=message_constant.TRACKER_STATE_TYPE_BLE_FAILED,
                map=best_map,
                last_detected_beacons=report.detectedBeacons,
                online=event_constant.ONLINE_STATUS_ACTIVE
            )

        report.map_name = map_config.map.name

        calculated_position = positioning.calculate_position(
            detected_beacons=best_beacons,
            miniprogram_config=map_config,
            device_id=tracker_id,
            map_name=best_map
        )

        filtered_position: Optional[Tuple[float, float]] = None
        kf = kalman_filters.get(tracker_id)

        runtime_cfg = config_manager.get_server_runtime_config()

        if calculated_position and calculated_position[2] == message_constant.TRACKER_STATE_TYPE_BLE_RANGE:
            if not runtime_cfg.allow_area_location:
                log.info(f"未启用区域定位, 丢弃消息: eui=>{report.trackerId}")
                return TrackerState(
                    trackerId=report.trackerId,
                    last_update_time=current_time_ms,
                    last_known_measurement_time=report.timestamp,
                    sos=report.sos,
                    battery=report.battery,
                    type=message_constant.TRACKER_STATE_TYPE_BLE_FAILED,
                    map=best_map,
                    used_beacons=best_beacons,
                    last_detected_beacons=report.detectedBeacons,
                    online=event_constant.ONLINE_STATUS_ACTIVE
                )

            scanned_beacon = best_beacons[int(calculated_position[1])]
            beacon_config = beacon_holder.get_beacon(scanned_beacon.macAddress)

            new_state = TrackerState(
                trackerId=tracker_id,
                last_update_time=current_time_ms,
                last_known_measurement_time=report.timestamp,
                last_detected_beacons=report.detectedBeacons,
                x=beacon_config.x,
                y=beacon_config.y,
                used_beacons=[DetectedBeacon(
                    macAddress=beacon_config.macAddress,
                    rssi=scanned_beacon.rssi,
                    configured_x=beacon_config.x,
                    configured_y=beacon_config.y,
                    name=beacon_config.displayName,
                    dis=calculated_position[0]
                )],
                map=best_map,
                sos=report.sos,
                battery=report.battery,
                type=message_constant.TRACKER_STATE_TYPE_BLE_RANGE,
                radius=calculated_position[0],
                online=event_constant.ONLINE_STATUS_ACTIVE
            )

            # device_holder.set_tracker_state(tracker_id, new_state)
            return new_state
        elif calculated_position:
            # log.info(f"Calculated position for {tracker_id}: {calculated_position}") # Can be noisy
            if kf:
                kf.predict(dt)
                kf.update(calculated_position)
            else:
                kf = KalmanFilter2D(
                    initial_pos=calculated_position,
                    process_variance=runtime_cfg.kalman.processVariance,
                    measurement_variance=runtime_cfg.kalman.measurementVariance
                )
                kalman_filters[tracker_id] = kf
                # log.info(f"Initialized Kalman filter for {tracker_id} with PV:{runtime_cfg.kalman.processVariance}, MV:{runtime_cfg.kalman.measurementVariance}") # Can be noisy

            filtered_position = kf.get_position()
            # log.info(f"Filtered position for {tracker_id}: {filtered_position}") # Can be noisy

            # Add new position to history
            if filtered_position:
                current_position_history.append((filtered_position[0], filtered_position[1], current_time_ms))

        elif kf:  # No new calculation, but KF might have predicted
            kf.predict(dt)
            filtered_position = kf.get_position()
            # log.info(f"Position prediction (no new measurement) for {tracker_id}: {filtered_position}") # Can be noisy
            # Optionally, decide if predicted-only positions should go into history.
            # For now, let's assume only measurement-updated or KF-initialized positions go to history via the block above.
            # If you want to add predicted positions too, uncomment and adjust:
            # if filtered_position:
            #     current_position_history.append((filtered_position[0], filtered_position[1], current_time_ms))

        # Prune history to last 30 minutes (30 * 60 * 1000 ms)
        history_time_window_ms = 30 * 60 * 1000
        cutoff_time_ms = current_time_ms - history_time_window_ms
        current_position_history = [p for p in current_position_history if p[2] >= cutoff_time_ms]

        log.info(f"device({tracker_id}) 最终定位: ${current_position_history}")  # Can be noisy

        new_state = TrackerState(
            trackerId=tracker_id,
            x=filtered_position[0] if filtered_position else (last_state.x if last_state else None),
            y=filtered_position[1] if filtered_position else (last_state.y if last_state else None),
            last_update_time=current_time_ms,
            last_known_measurement_time=report.timestamp,
            last_detected_beacons=report.detectedBeacons,
            used_beacons=[
                DetectedBeacon(
                    macAddress=beacon.macAddress,
                    rssi=beacon.rssi,
                    configured_x=beacon_holder.get_beacon(beacon.macAddress).x,
                    configured_y=beacon_holder.get_beacon(beacon.macAddress).y,
                    name=beacon_holder.get_beacon(beacon.macAddress).displayName
                ) for beacon in best_beacons
            ],
            position_history=current_position_history,
            map=best_map,
            sos=report.sos,
            battery=report.battery,
            type=message_constant.TRACKER_STATE_TYPE_BLE_CAL,
            online=event_constant.ONLINE_STATUS_ACTIVE
        )
        return new_state
    except Exception as err:
        log.error(f"tracker({report.trackerId}) resolve location err. \n report:\n  {report}, \nerr:\n  {err}")
        raise err
