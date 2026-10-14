from server.dao.device_dao import device_dao
from server.dao.device_alarm_record_dao import alarm_record_dao

from server.components.event_manager import event_manager

from server.components.device_holder import device_holder
from server.components.websocket_holder import websocket_holder

import server.constant.event_constant as event_constant
import server.constant.message_constant as message_constant

from server.models import (
    DeviceRecord, TrackerState, EventTriggerRecord
)

import json
from datetime import datetime
import asyncio

import logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


DEFAULT_ONLINE_CHECK_INTERVAL_MS = 15 * 60 * 1000


async def offline_event_action(state: TrackerState, alarm_setting: EventTriggerRecord, timestamp: int):
    loc = {}
    if state.x and state.y:
        loc["x"] = state.x
        loc["y"] = state.y
    if state.radius:
        loc["radius"] = state.radius
    alarm_record_dao.create_record(
        dev_eui=state.trackerId,
        alarm_time=datetime.fromtimestamp(timestamp),
        pos_type=state.type,
        loc=loc,
        beacons=state.used_beacons,
        status=1,
        event_type=event_constant.ALARM_TYPE_OFFLINE,
        event_id=alarm_setting.id,
        event_name=alarm_setting.event_name,
        map_name=state.map
    )
    await websocket_holder.broadcast(message_constant.get_online_message(state, timestamp))


async def devices_offline_check(device_list: list[DeviceRecord], timestamp: int):
    if not device_list or len(device_list) == 0:
        log.info("task: device-offline-checker is done: none device in application...")
        return
    timestamp_ms = timestamp * 1000
    for device in device_list:
        tracker_state = device_holder.get_tracker_state(device.dev_eui)
        old_online_status = tracker_state.online
        if (old_online_status == event_constant.ONLINE_STATUS_OFFLINE or
                old_online_status == event_constant.ONLINE_STATUS_UNKNOWN):
            continue
        online_status = event_constant.ONLINE_STATUS_ACTIVE
        if (timestamp_ms - tracker_state.last_update_time) > DEFAULT_ONLINE_CHECK_INTERVAL_MS:
            online_status = event_constant.ONLINE_STATUS_OFFLINE
        else:
            continue
        # unknown => offline tracker-state更新, ws不推送, event不触发
        device_holder.update_tracker_online_status(device.dev_eui, online_status)
        log.info(f"device-offline-checker: the device({device.dev_eui}) turn into offline in time: {timestamp}")

        if old_online_status == event_constant.ONLINE_STATUS_UNKNOWN:
            continue

        event_list = event_manager.get_events_for_device(device.dev_eui)
        if not event_list or len(event_list) == 0:
            continue
        for event in event_list:
            if event.event_type != event_constant.ALARM_TYPE_OFFLINE or not event.enable_status:
                continue
            await offline_event_action(tracker_state, event, timestamp)


async def do():
    while True:
        now = datetime.now()
        log.info(f"task: device-offline-checker is running in ({datetime.now()})...")
        device_list: list[DeviceRecord] = device_dao.get_all_device()
        await devices_offline_check(device_list, int(now.timestamp()))
        log.info(f"task: device-offline-checker is running in ({datetime.now()})...")
        await asyncio.sleep(60)



