from server.dao.device_dao import device_dao
from server.dao.event_trigger_dao import event_trigger_dao

from server.components.device_holder import device_holder

import server.constant.event_constant as event_constant

from server.models import (
    DeviceRecord
)

import json
from datetime import datetime

import logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


DEFAULT_ONLINE_CHECK_INTERVAL_MS = 15 * 60 * 1000

# def device_online_status_action(dev_eui: str, status: str):

def devices_offline_check(device_list: list[DeviceRecord], timestamp: int):
    if not device_list or len(device_list) == 0:
        log.info("task: device-offline-checker is done: none device in application...")
        return
    for device in device_list:
        tracker_state = device_holder.get_tracker_state(device.dev_eui)
        if not tracker_state:
            log.info(f"task: device-offline-checker can not find the device({device.dev_eui})")
            continue
        online_status = tracker_state.online
        last_report_time = tracker_state.last_update_time
        last_online_status = event_constant.ONLINE_STATUS_OFFLINE if (
                (timestamp - last_report_time) > DEFAULT_ONLINE_CHECK_INTERVAL_MS
        ) else event_constant.ONLINE_STATUS_ACTIVE



def do():
    now = datetime.now()
    log.info(f"task: device-offline-checker is running in (now)...")
    device_list: list[DeviceRecord] = device_dao.get_all_device()


