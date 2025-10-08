from server.models import (  # Grouped imports for models
    DetectedBeacon, TrackerReport, TrackerState, WebUIBeaconConfig,
    MiniprogramConfig, WebUIConfig, DashboardConfig, MqttServerConfig,
    WebUISettings, PartialServerRuntimeConfig, PasswordChangeRequest, ServiceCredentialsRequest,
    LoginRequest,  # Import WebUISettings directly
    UserSessionInfo, GroupCreateRequest, GroupUpdateRequest, GroupListItem,
    DeviceCreateRequest, DeviceUpdateRequest, DeviceStatusUpdateRequest, DeviceListItem, DeviceSearchRequest,
    DeviceBatchUpdateGroupRequest, DeviceRecord, TrackerInfo, TrackerStateQueryRequest,
    EventTriggerCreateRequest, EventTriggerUpdateRequest, EventTriggerListItem, EventTriggerRecord
)
from server.components.event_manager import event_manager

from server.components import (
    device_holder, beacon_holder
)

from server.constant import event_constant

import logging

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

def single_event_consume(report: TrackerReport, alarm_setting: EventTriggerRecord) -> int:
    log.info(f"single_event_consume: {report.trackerId} in event: {alarm_setting.id}")
    # match alarm_setting.event_type:
    #     case event_constant.ALARM_TYPE_SOS:
    #         ## sos 状态与当前设备状态不一致, 则触发
    #         previous_sos = device_holder.get_tracker_state(report.trackerId)
    #         if report.sos != 2 and device_holder.get_tracker_state(report.trackerId):
    #             log.info(f'broadcast tracker sos event: {report.trackerId}')
    #
    #         ## 触发的处理, 创建对应的event 记录
    #         ## 返回对应event, 用于后续的广播
    #         ## 更新运行时的设备状态
    #
    #     case event_constant.ALARM_TYPE_OFFLINE:
    #
    #     case event_constant.ALARM_TYPE_CHECKIN:
    #
    #     case event_constant.ALARM_TYPE_POSITION_DETECTION:
    #

def alarm_handle(report: TrackerReport):
    log.info(f"alarm_handle: {report.trackerId}")
    finish_event: dict[int, int] = {}

    device_event = event_manager.get_events_for_device(report.trackerId)
    if not device_event or len(device_event) == 0:
        return
    for setting in device_event:
        if finish_event.get(setting.id, 0):
            continue
        single_event_consume(report, setting)
        finish_event[setting.id] = 1



