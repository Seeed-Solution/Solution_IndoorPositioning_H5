
from server.components.device_holder import device_holder
from server.components.websocket_holder import websocket_holder

from server.dao.device_dao import device_dao

import server.constant.message_constant as message_constant
import server.constant.event_constant as event_constant


from server.models import (
    TrackerReport, TrackerState
)

import logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


# 初始化设备信息, 更新最新上报时间和在线状态
def pre_listener(report: TrackerReport):
    device = device_holder.get_tracker_state(report.trackerId)
    if device is None:
        try:
            log.info(f"the new tracker is detected({report.trackerId})...")
            device_result = device_dao.create_device(dev_eui=report.trackerId)
            device_holder.set_tracker_state(report.trackerId, TrackerState(
                trackerId=report.trackerId,
                last_update_time=report.receive_time * 1000,
                online="online"
            ))
            if device_result is not None:
                log.info(f"the new tracker is been saved({report.trackerId})...")
        except Exception as err:
            log.info(f"the new tracker({report.trackerId}) saving failure, e: \n{err}")
    else:
        device_holder.update_tracker_online_status(report.trackerId, "online")
        device_holder.update_tracker_last_update_time(report.trackerId, report.receive_time * 1000)

    if int(report.battery) != -1:
        device_holder.update_tracker_battery(report.trackerId, int(report.battery))


# 定位结果广播
async def post_listener(state: TrackerState):
    state.online = event_constant.ONLINE_STATUS_ACTIVE
    device_holder.set_tracker_state(state.trackerId, state)
    if state.type == message_constant.TRACKER_STATE_TYPE_BLE_CAL:
        await websocket_holder.broadcast(message_constant.get_tracker_update(state))
    elif state.type == message_constant.TRACKER_STATE_TYPE_BLE_RANGE:
        await websocket_holder.broadcast(message_constant.get_tracker_loc_appr(state))

    log.info(f"message_listener: post_listener finish for tracker:{state.trackerId}")