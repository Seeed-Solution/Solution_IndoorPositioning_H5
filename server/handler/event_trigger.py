import asyncio

from server.dao.event_trigger_dao import event_trigger_dao
from server.dao.device_alarm_record_dao import alarm_record_dao
from server.dao.device_dao import device_dao

from server.constant import event_constant
from server.components.device_holder import device_event_holder
from server.components.websocket_holder import websocket_holder
from server.components.event_manager import event_manager

import server.constant.message_constant as message_constant

from server.models import (  # Grouped imports for models
    DetectedBeacon, TrackerReport, TrackerState, WebUIBeaconConfig,
    DashboardConfig, MqttServerConfig,
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

    def __init__(self):
        self.leaving_check: dict[str, TrackerState] = {}

    def push_leaving_check(self, event_id: int, message: TrackerState):
        key = f"{event_id}:{message.trackerId}"
        self.leaving_check.setdefault(key, message)

    def delete_leaving_check(self, event_id: int, tracker_id: str):
        key = f"{event_id}:{tracker_id}"
        self.leaving_check.pop(key, None)

    def get_event_report(self, event_id: int, tracker_id: str) -> TrackerState:
        key = f"{event_id}:{tracker_id}"
        return self.leaving_check.get(key, None)

    def get_all_key(self):
        return self.leaving_check.keys()



event_checker = LeavingEventChecker()

## 古希腊掌管position-detection的神
## 创建对应event记录
## 推送
## 创建event触发标志避免重复触发
## 清理触发状态
async def leaving_event_action(event_setting: EventTriggerRecord, state: TrackerState):
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
            alarm_time=datetime.datetime.fromtimestamp(int(state.timestamp / 1000)),
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
            timestamp=int(state.timestamp)
        )
        await websocket_holder.broadcast(message_constant.get_leaving_message(state))
    except Exception as err:
        log.error(f"leaving event({state.trackerId}:${event_setting.id}) can not finish, err:\n  {err}")


async def remove_device_leaving_waiting_event(dev_eui: str, event_id: int):
    event_checker.delete_leaving_check(event_id=event_id, tracker_id=dev_eui)
    device_event_holder.delete_device_event_timestamp(dev_eui=dev_eui, event_id=event_id)


async def device_leaving_event_checker(state: TrackerState, event_setting: EventTriggerRecord, now: float):
    dev_eui = state.trackerId
    triggered_time = device_event_holder.get_device_event_timestamp(dev_eui=dev_eui, event_id=event_setting.id)
    if triggered_time:
        log.info(f"leaving event({dev_eui}:{event_setting.id}) will be skipped because of triggered")
        return
    if event_setting.time_range == 0:
        await leaving_event_action(event_setting=event_setting, state=state)
        return
    timestamp = state.timestamp

    target_time = timestamp + event_setting.time_range * MINUTE_IN_MS
    if now < target_time:
        event_checker.push_leaving_check(event_id=event_setting.id, message=state)
        log.info(f"leaving_event is waiting, id:{event_setting.id}, "
                 f"timestamp:${timestamp}, plan_time: {target_time}, "
                 f"waiting: ${int(target_time - now) / 1000} second")
        return
    await leaving_event_action(event_setting, state)
    log.info(f"leaving_event has been triggered, id:{event_setting.id}, "
             f"timestamp:${timestamp}, waiting-time: {event_setting.time_range},now: ${now}")


async def global_leaving_event_check(now: int):
    flag_list = list(event_checker.get_all_key())
    if not flag_list or len(flag_list) == 0:
        return

    for flag in flag_list:
        try:

            # event_list: list[EventTriggerRecord] = (
            #     event_trigger_dao.get_all_event_by_type(event_constant.ALARM_TYPE_POSITION_DETECTION))
            # if not event_list or len(event_list) == 0:
            #     return
            #
            # for event_setting in event_list:
            #     device_str = event_setting.device_range
            #     if not device_str or len(device_str) == 0:
            #         log.info(f"leaving event(id:{event_setting.id}) will be skipped because of none device")
            #         continue
            #
            #     device_list: list[str] = json.loads(device_str)
            #     if not device_list or len(device_list) == 0:
            #         log.info(f"leaving event(id:{event_setting.id}) will be skipped because of none device")
            #         continue
            #     if len(device_list) == 1 and device_list[0] == "all":
            #         tracker_list = device_dao.get_all_device()
            #         if not tracker_list or len(tracker_list) == 0:
            #             log.info(f"leaving event(id:{event_setting.id}) will be skipped because of none device")
            #             return
            #         device_list = [tracker.dev_eui for tracker in tracker_list]
            #     for dev_eui in device_list:
            #         triggered_time = device_event_holder.get_device_event_timestamp(
            #             dev_eui=dev_eui,
            #             event_id=event_setting.id
            #         )
            #         if triggered_time:
            #             log.info(f"leaving event({dev_eui}:{event_setting.id}) will be skipped because of triggered")
            #             continue
            #         state = event_checker.get_event_report(event_setting.id, dev_eui)
            #         if not state:
            #             log.info(
            #                 f"leaving event({dev_eui}:{event_setting.id}) will be skipped "
            #                 f"because the tracker is not leaving...")
            #             continue
            #         await device_leaving_event_checker(state=state, event_setting=event_setting, now=now)
            word_list: list[str] = flag.split(":")
            if not word_list or len(word_list) < 2:
                log.error(f"global_leaving_event_check==> incorrect leaving_event flag: {flag}")
                return
            dev_eui = word_list[1]
            event_id = int(word_list[0])
            state = event_checker.get_event_report(tracker_id=dev_eui, event_id=event_id)
            if not state:
                log.info(f"leaving event({dev_eui}:{event_id}) will be skipped "
                         f"because can not find the tracker state: {dev_eui}")
                continue
            triggered_time = device_event_holder.get_device_event_timestamp(
                dev_eui=dev_eui,
                event_id=event_id
            )
            if triggered_time:
                log.info(f"leaving event({dev_eui}:{event_id}) will be skipped because of triggered")
                continue

            event_list = event_manager.get_events_for_device(dev_eui=dev_eui)

            if not event_list or len(event_list) == 0:
                log.info(f"leaving event({dev_eui}:{event_id}) will be skipped "
                         f"because can not find the event: {event_id}")

            event_setting = None
            for event in event_list:
                if event.id != event_id:
                    continue
                event_setting = event

            if not event_setting or not event_setting.enable_status or event_setting.delete_time:
                log.info(f"leaving event({dev_eui}:{event_id}) will be skipped "
                         f"because can not find the event: {event_id}")
                continue
            await device_leaving_event_checker(state=state, event_setting=event_setting, now=now)
        except Exception as err:
            log.error(f"global_leaving_event_check, flag:{flag}, err:\n{err}")




async def position_detection_task():
    while True:
        now = datetime.datetime.now().timestamp() * 1000
        log.info(f"leaving_event_trigger is running, now: {now}")
        await global_leaving_event_check(int(now))
        log.info(f"leaving_event_trigger is end, now: {datetime.datetime.now()}")
        await asyncio.sleep(30)
