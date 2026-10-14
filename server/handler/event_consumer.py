from server.models import (  # Grouped imports for models
    DetectedBeacon, TrackerReport, TrackerState, WebUIBeaconConfig, DashboardConfig,
    MqttServerConfig, WebUISettings, PartialServerRuntimeConfig, UserSessionInfo, GroupCreateRequest,
    GroupUpdateRequest, GroupListItem, DeviceListItem, DeviceRecord, TrackerInfo,EventTriggerListItem,
    EventTriggerRecord, DeviceAlarmRecord
)
from server.components.event_manager import event_manager
from server.components.device_holder import device_event_holder
from server.components.device_holder import device_holder
from server.components.websocket_holder import websocket_holder

import server.handler.event_trigger as event_trigger

from server.dao.device_alarm_record_dao import alarm_record_dao

from server.components.geofence_holder import geofence_holder
from server import geofence as geofence_engine

from server.constant import event_constant
from server.constant import message_constant

import datetime
from typing import Optional
import json

import logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


## 找出tracker 最近的beacon
def find_closest_beacon(
        ble_range: list[str],
        detectedBeacons: list[DetectedBeacon],
        range_in:
        float = 9999999) -> tuple[str, float]:
    if not ble_range or len(ble_range) == 0:
        return "", -1
    if not detectedBeacons or len(detectedBeacons) == 0:
        return "", -1
    closest_beacon = ""
    closest_dis = 999999
    for target in ble_range:
        for beacon in detectedBeacons:
            mac = beacon.macAddress.replace(":", "").upper()
            if mac != target.replace(":", "").upper():
                continue
            if beacon.dis > range_in:
                continue
            if beacon.dis < closest_dis:
                closest_beacon = target
                closest_dis = beacon.dis
    return closest_beacon, closest_dis


def build_geo_loc(state: TrackerState, fence_id: Optional[int], transition: str) -> dict:
    """告警记录的 loc: 经纬度 + 坐标系 + 围栏与转换方向.

    旧的 x/y 在室内模式下继续写(见下面 build_metric_loc), 读侧两种都要吃.
    """
    return {
        "lat": state.lat,
        "lon": state.lon,
        "coordSystem": "wgs84",
        "fence_id": fence_id,
        "transition": transition,
    }


def build_metric_loc(state: TrackerState) -> dict:
    """BLE 模式的告警坐标: 旧的 x/y/radius 照写, 有经纬度时一并带上."""
    loc = {}
    if state.x and state.y:
        loc["x"] = state.x
        loc["y"] = state.y
        loc["coordSystem"] = "metric"
    if state.radius:
        loc["radius"] = state.radius
    if state.lat is not None and state.lon is not None:
        loc["lat"] = state.lat
        loc["lon"] = state.lon
        if "coordSystem" not in loc:
            loc["coordSystem"] = "wgs84"
    return loc


async def consume_geo_event(state: TrackerState,
                            alarm_setting: EventTriggerRecord) -> Optional[DeviceAlarmRecord]:
    """location_mode=geo 的判定: 只看经纬度, 不依赖 beacon.

    围栏状态走 FenceHysteresis: 连续 3 点且持续 10 s 才切换,
    切换瞬间产出一次 enter/exit; 方向与 alarm_setting.transition 匹配才告警.
    """
    if state.lat is None or state.lon is None:
        log.info(
            f'the tracker: {state.trackerId} geo-event(id:{alarm_setting.id}) '
            f'skip because of no lat/lon in this uplink')
        return None

    fence = geofence_holder.get_fence(alarm_setting.geofence_id)
    if fence is None:
        log.info(
            f'the tracker: {state.trackerId} geo-event(id:{alarm_setting.id}) '
            f'skip because geofence {alarm_setting.geofence_id} is missing/disabled/invalid')
        return None

    hysteresis = geofence_holder.get_hysteresis(state.trackerId, alarm_setting.id)
    transition = hysteresis.feed(
        fence=fence,
        lat=state.lat,
        lon=state.lon,
        timestamp_ms=state.timestamp or int(datetime.datetime.now().timestamp() * 1000),
        accuracy=state.accuracy,
        log_key=f'{state.trackerId}/{alarm_setting.id}',
    )
    if not transition:
        return None
    if not geofence_engine.transition_matches(alarm_setting.transition, transition):
        log.info(
            f'the tracker: {state.trackerId} geo-event(id:{alarm_setting.id}) '
            f'ignores {transition} because configured transition is {alarm_setting.transition}')
        return None

    loc = build_geo_loc(state, fence.id, transition)
    record = alarm_record_dao.create_record(
        dev_eui=state.trackerId,
        alarm_time=datetime.datetime.fromtimestamp(state.timestamp / 1000)
        if state.timestamp else datetime.datetime.now(),
        pos_type=message_constant.TRACKER_POSITIONING_TYPE_GPS,
        loc=loc,
        beacons=state.used_beacons,
        status=1,
        event_type=alarm_setting.event_type,
        event_id=alarm_setting.id,
        event_name=alarm_setting.event_name,
        map_name=fence.name or state.map,
        desc={"fence_id": fence.id, "fence_name": fence.name, "transition": transition},
    )
    if transition == geofence_engine.TRANSITION_ENTER:
        await websocket_holder.broadcast(message_constant.get_geofence_message(
            state, fence.id, fence.name, transition, message_constant.MESSAGE_TYPE_TRACKER_CHECKIN))
    else:
        await websocket_holder.broadcast(message_constant.get_geofence_message(
            state, fence.id, fence.name, transition,
            message_constant.MESSAGE_TYPE_TRACKER_POSITION_DETECTION))
    log.info(
        f'the tracker: {state.trackerId} geofence {fence.id} {transition} '
        f'event(id:{alarm_setting.id}) triggered')
    return record


async def single_event_consume(state: TrackerState, alarm_setting: EventTriggerRecord) -> Optional[DeviceAlarmRecord]:
    log.info(f"single_event_consume: {state.trackerId} in event: {alarm_setting.id}")
    try:
        now = datetime.datetime.now().timestamp() * 1000
        match alarm_setting.event_type:
            case event_constant.ALARM_TYPE_SOS:
                ## sos 状态与当前设备状态不一致, 则触发
                previous_sos = device_holder.get_tracker_sos(state.trackerId)
                device_holder.update_tracker_sos(state.trackerId, state.sos)
                log.info(f'the tracker: {state.trackerId} sos event: {state.sos} from {previous_sos}')
                if previous_sos != state.sos and state.sos != event_constant.SOS_STATUS_UNKNOWN:
                    # device_holder.update_tracker_sos(tracker_id=state.trackerId, sos=state.sos)
                    await websocket_holder.broadcast(message_constant.get_sos_message(state))
                    if previous_sos == event_constant.SOS_STATUS_UNKNOWN:
                        return
                    log.info(f'the tracker: {state.trackerId} sos event: {state.sos} from {previous_sos}')
                    loc = build_metric_loc(state)
                    alarm_record_dao.create_record(
                        dev_eui=state.trackerId,
                        alarm_time=datetime.datetime.fromtimestamp(state.timestamp / 1000),
                        pos_type=state.type,
                        loc=loc,
                        beacons=state.used_beacons,
                        event_type=event_constant.ALARM_TYPE_SOS,
                        event_id=alarm_setting.id,
                        event_name=alarm_setting.event_name,
                        map_name=state.map,
                        status=state.sos
                    )
            # case event_constant.ALARM_TYPE_OFFLINE:
            case event_constant.ALARM_TYPE_CHECKIN:
                if alarm_setting.is_geo_mode():
                    return await consume_geo_event(state, alarm_setting)
                if not alarm_setting.ble_range or len(alarm_setting.ble_range) == 0:
                    log.info(
                        f'the tracker: {state.trackerId} check-in-event(id:{alarm_setting.id}) skip '
                        f'because of none ble-range')
                    return
                target_beacons: list[str] = json.loads(alarm_setting.ble_range)
                if not target_beacons or len(target_beacons) == 0:
                    log.info(
                        f'the tracker: {state.trackerId} check-in-event(id:{alarm_setting.id}) skip '
                        f'because of none ble-range')
                    return
                if not state.used_beacons or len(state.used_beacons) == 0:
                    log.info(
                        f'the tracker: {state.trackerId} check-in-event(id:{alarm_setting.id}) '
                        f'RECOVER because of none none used_beacons')
                    device_event_holder.delete_device_event_timestamp(dev_eui=state.trackerId,
                                                                      event_id=alarm_setting.id)
                    return

                closed_beacons = find_closest_beacon(target_beacons, state.used_beacons, alarm_setting.dis_range)
                closest_beacon = closed_beacons[0]
                closest_dis = closed_beacons[1]
                if not closest_beacon or len(closed_beacons) == 0:
                    device_event_holder.delete_device_event_timestamp(dev_eui=state.trackerId,
                                                                      event_id=alarm_setting.id)
                    log.info(
                        f'the tracker: {state.trackerId} check-in-event(id:{alarm_setting.id}) '
                        f'skip because no applicable beacon')
                    return

                triggered_time = device_event_holder.get_device_event_timestamp(state.trackerId, alarm_setting.id)
                if triggered_time:
                    log.info(
                        f'the tracker: {state.trackerId} check-in-event(id:{alarm_setting.id}) '
                        f'skip because of has been triggered in {triggered_time}')
                    return

                loc = build_metric_loc(state)
                alarm_record_dao.create_record(
                    dev_eui=state.trackerId,
                    alarm_time=datetime.datetime.fromtimestamp(state.timestamp / 1000),
                    pos_type=state.type,
                    loc=loc,
                    beacons=state.used_beacons,
                    status=1,
                    event_type=event_constant.ALARM_TYPE_CHECKIN,
                    event_id=alarm_setting.id,
                    event_name=alarm_setting.event_name,
                    map_name=state.map
                )
                await websocket_holder.broadcast(message_constant.get_checkin_message(state))
                device_event_holder.set_device_event_timestamp(
                    dev_eui=state.trackerId,
                    event_id=alarm_setting.id,
                    timestamp=state.timestamp
                )
                log.info(f'the tracker: {state.trackerId} check-in event: {closest_beacon} with dis: {closest_dis} M')
            case event_constant.ALARM_TYPE_POSITION_DETECTION:
                if alarm_setting.is_geo_mode():
                    return await consume_geo_event(state, alarm_setting)
                if not alarm_setting.ble_range or len(alarm_setting.ble_range) == 0:
                    log.info(
                        f'the tracker: {state.trackerId} '
                        f'position-detection-event(id:{alarm_setting.id}) skip because of none ble-range')
                    return
                target_beacons: list[str] = json.loads(alarm_setting.ble_range)
                if not target_beacons or len(target_beacons) == 0:
                    log.info(
                        f'the tracker: {state.trackerId} '
                        f'position-detection-event(id:{alarm_setting.id}) skip because of none ble-range')
                    return
                if not state.last_detected_beacons or len(state.last_detected_beacons) == 0:
                    log.info(
                        f'the tracker: {state.trackerId} position-detection-event'
                        f'(id:{alarm_setting.id}) skip because of none none detectedBeacons')
                    return

                leaving = True
                for target in target_beacons:
                    for beacon in state.last_detected_beacons:
                        beacon_mac = beacon.macAddress.replace(":", "").upper()
                        if beacon_mac == target.replace(":", "").upper():
                            leaving = False
                            break

                if not leaving:
                    await event_trigger.remove_device_leaving_waiting_event(
                        dev_eui=state.trackerId,
                        event_id=alarm_setting.id
                    )
                    return

                triggered_time = device_event_holder.get_device_event_timestamp(
                    dev_eui=state.trackerId,
                    event_id=alarm_setting.id
                )
                if triggered_time:
                    log.info(
                        f'the tracker: {state.trackerId} position detection(id:{alarm_setting.id}) '
                        f'skip because of has been triggered in {triggered_time}')
                    return
                await event_trigger.device_leaving_event_checker(state, alarm_setting, now)
                log.info(f'the tracker: {state.trackerId} position-detection event: {alarm_setting.id} '
                         f'with time_: {alarm_setting.time_range} min')
    except Exception as err:
        log.error(f"the tracker({state.trackerId}) in event({alarm_setting.id}) is failed, err:\n {err}")

            # if alarm_setting.time_range == 0:
            #     event_trigger.leaving_event_action(event_setting=alarm_setting, report=report)
            #      DeviceAlarmRecord(
            #         dev_eui=report.trackerId,
            #         alarm_time=datetime.datetime.fromtimestamp(report.timestamp / 1000),
            #         status=1,
            #         event_type=alarm_setting.event_type,
            #         event_id=alarm_setting.id,
            #     )
            #     return


async def message_handle(state: TrackerState):
    log.info(f"alarm_handle: {state.trackerId}")
    finish_event: dict[int, int] = {}

    device_event = event_manager.get_events_for_device(state.trackerId)
    if not device_event or len(device_event) == 0:
        return []
    alarm_list = []
    for setting in device_event:
        if finish_event.get(setting.id, 0):
            continue
        alarm = await single_event_consume(state, setting)
        if not alarm:
            alarm_list.append(alarm)
        finish_event[setting.id] = 1
    return alarm_list


