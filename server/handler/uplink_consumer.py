import server.config.config_manager as config_manager

import server.handler.message_format_hanlder as message_formatter
import server.handler.message_listen_handler as message_listener
import server.handler.position_resolve_handler as position_resolver
import server.handler.event_consumer as event_consumer
from server.models import TrackerReport


import logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


async def do(topic: str, payload_bytes: bytes, source_type: str = "chirpstack"):
    rt_cfg = config_manager.get_server_runtime_config()

    report = await message_formatter.do(topic, payload_bytes, source_type)
    # log.info(f"=======DEBUG=======\ntopic:{topic}\nreport:\n{report}")
    if not report:
        return

    device_eui = report.trackerId
    if not rt_cfg.allow_all_tracker and device_eui not in rt_cfg.allow_tracker_list:
        log.debug(f"the device: {device_eui} not in allow_list, ignore this message.")
        return
    try:
        message_listener.pre_listener(report)
        latest_state = position_resolver.do(report)
        log.info(f"tracker(id: {report.trackerId}) location resolving done, state: \n {latest_state}")
        await message_listener.post_listener(latest_state)
        await event_consumer.message_handle(latest_state)
    except Exception as err:
        log.error(f"uplink consumer: the message from device({device_eui}) error: \n${err}")


## 接收任意dev_eui 仅用于debug
async def do_for_tracker_report(report: TrackerReport):
    device_eui = report.trackerId
    try:
        message_listener.pre_listener(report)
        latest_state = position_resolver.do(report)
        log.info(f"tracker(id: {report.trackerId}) location resolving done, state: \n {latest_state}")
        await message_listener.post_listener(latest_state)
        await event_consumer.message_handle(latest_state)
    except Exception as err:
        log.error(f"uplink consumer: the message from device({device_eui}) error: \n${err}")

