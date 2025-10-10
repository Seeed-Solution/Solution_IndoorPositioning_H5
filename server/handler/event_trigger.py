from server.dao.event_trigger_dao import event_trigger_dao
from server.dao.device_alarm_record_dao import alarm_record_dao
from server.dao.device_dao import device_dao

from server.constant import event_constant
from server.components.device_holder import device_event_holder
from server.components.websocket_holder import websocket_holder

import server.constant.message_constant as message_constant

from server.models import (  # Grouped imports for models
    DetectedBeacon, TrackerReport, TrackerState, WebUIBeaconConfig,
    MiniprogramConfig, WebUIConfig, DashboardConfig, MqttServerConfig,
    WebUISettings, PartialServerRuntimeConfig, PasswordChangeRequest, ServiceCredentialsRequest,
    LoginRequest,  # Import WebUISettings directly
    UserSessionInfo, GroupCreateRequest, GroupUpdateRequest, GroupListItem,
    DeviceCreateRequest, DeviceUpdateRequest, DeviceStatusUpdateRequest, DeviceListItem, DeviceSearchRequest,
    DeviceBatchUpdateGroupRequest, DeviceRecord, TrackerInfo, TrackerStateQueryRequest,
    EventTriggerCreateRequest, EventTriggerUpdateRequest, EventTriggerListItem, EventTriggerRecord, DeviceAlarmRecord
)

import datetime
from typing import Optional
import json

import logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

MINUTE_IN_MS = 60 * 1000

class LeavingEventChecker:

    def __int__(self):
        self.leaving_check: dict[str, TrackerState] = {}

    def push_leaving_check(self, event_id: int, message: TrackerState):
        key = f"{event_id}:{message.trackerId}"
        self.leaving_check[key] = message

    def delete_leaving_check(self, event_id: int, tracker_id: str):
        key = f"{event_id}:{tracker_id}"
        del self.leaving_check[key]

    def get_event_report(self, event_id: int, tracker_id: str) -> TrackerState:
        key = f"{event_id}:{tracker_id}"
        return self.leaving_check.get(key, None)


event_checker = LeavingEventChecker()

## 古希腊掌管position-detection的神
## 创建对应event记录
## 推送
## 创建event触发标志避免重复触发
## 清理触发状态
def leaving_event_action(event_setting: EventTriggerRecord, state: TrackerState):
    try:
        loc = {}
        if state.x and state.y:
            loc["x"] = state.x
            loc["y"] = state.y
        if state.radius:
            loc["radius"] = state.radius
        alarm_record_dao.create_record(
            dev_eui=state.trackerId,
            loc=loc,
            pos_type=state.type,
            alarm_time=datetime.datetime.fromtimestamp(int(state.last_known_measurement_time / 1000)),
            beacons=state.used_beacons,
            status=event_constant.SOS_STATUS_TRIGGERED,
            event_type=event_setting.event_type,
            event_id=event_setting.id,
            event_name=event_setting.event_name,
            desc={},
            map_name=state.map
        )
        event_checker.delete_leaving_check(event_id=event_setting.id, tracker_id=state.trackerId)
        device_event_holder.set_device_event_timestamp(
            dev_eui=state.trackerId,
            event_id=event_setting.id,
            timestamp=int(state.last_known_measurement_time)
        )
        websocket_holder.broadcast(message_constant.get_leaving_message(state))
    except Exception as err:
        log.error(f"leaving event({state.trackerId}:${event_setting.id}) can not finish, err:\n  {err}")


def device_leaving_event_checker(state: TrackerState, event_setting: EventTriggerRecord, now: float):
    dev_eui = state.trackerId
    triggered_time = device_event_holder.get_device_event_timestamp(dev_eui=dev_eui, event_id=event_setting.id)
    if triggered_time:
        log.info(f"leaving event({dev_eui}:{event_setting.id}) will be skipped because of triggered")
        return
    if event_setting.time_range == 0:
        leaving_event_action(event_setting=event_setting, state=state)
        return
    timestamp = state.last_known_measurement_time

    target_time = timestamp + event_setting.time_range * MINUTE_IN_MS
    if now < target_time:
        event_checker.push_leaving_check(event_id=event_setting.id, message=state)
        log.info(f"leaving_event is waiting, id:{event_setting.id}, "
                 f"timestamp:${timestamp}, waiting-time: {event_setting.time_range},now: ${now}")
        return
    leaving_event_action(event_setting, state)
    log.info(f"leaving_event has been triggered, id:{event_setting.id}, "
             f"timestamp:${timestamp}, waiting-time: {event_setting.time_range},now: ${now}")


def leaving_event_check_task():
    now = datetime.datetime.now().timestamp() * 1000
    log.info(f"leaving_event_trigger is running, now: ${now}")
    try:
        event_list: list[EventTriggerRecord] = (
            event_trigger_dao.get_all_event_by_type(event_constant.ALARM_TYPE_POSITION_DETECTION))
        if not event_list or len(event_list) == 0:
            return
        for event_setting in event_list:
            device_str = event_setting.device_range
            if not device_str or len(device_str) == 0:
                log.info(f"leaving event(id:{event_setting.id}) will be skipped because of none device")
                continue

            device_list: list[str] = json.loads(device_str)
            if not device_list or len(device_list) == 0:
                log.info(f"leaving event(id:{event_setting.id}) will be skipped because of none device")
                continue
            if len(device_list) == 1 and device_list[0] == "all":
                tracker_list = device_dao.get_all_device()
                if not tracker_list or len(tracker_list) == 0:
                    log.info(f"leaving event(id:{event_setting.id}) will be skipped because of none device")
                    return
                device_list = [tracker.dev_eui for tracker in tracker_list]
            for dev_eui in device_list:
                triggered_time = device_event_holder.get_device_event_timestamp(
                    dev_eui=dev_eui,
                    event_id=event_setting.id
                )
                if triggered_time:
                    log.info(f"leaving event({dev_eui}:{event_setting.id}) will be skipped because of triggered")
                    continue
                state = event_checker.get_event_report(event_setting.id, dev_eui)
                if not state:
                    log.info(
                        f"leaving event({dev_eui}:{event_setting.id}) will be skipped "
                        f"because the tracker is not leaving...")
                    continue
                device_leaving_event_checker(state=state, event_setting=event_setting, now=now)
                # log.info(f"leaving_event has been triggered, id:{event_setting.id}, "
                #          f"timestamp:${timestamp}, waiting-time: {event_setting.time_range},now: ${now}")
    except Exception as err:
        log.error(err)




