"""location_mode=geo 的 checkin / position_detection: 只看经纬度, 不依赖 beacon."""
import asyncio

import pytest

from server import geofence as ge
from server.constant import event_constant
from server.handler import event_consumer
from server.models import EventTriggerRecord, TrackerState

SQUARE = {
    "type": "Polygon",
    "coordinates": [[
        [113.0, 22.0], [113.02, 22.0], [113.02, 22.02], [113.0, 22.02], [113.0, 22.0],
    ]],
}
INSIDE = (22.01, 113.01)
OUTSIDE = (22.05, 113.05)
S = 1000


class FakeAlarmDao:
    def __init__(self):
        self.records = []

    def create_record(self, **kwargs):
        self.records.append(kwargs)
        return kwargs


class FakeWebsocketHolder:
    def __init__(self):
        self.messages = []

    async def broadcast(self, message):
        self.messages.append(message)


@pytest.fixture
def geo_env(monkeypatch):
    """把围栏、告警库、广播全部换成内存假件, 不碰 sqlite 和网络."""
    fence = ge.build_geofence(SQUARE, fence_id=7, name="厂区北门")
    dao = FakeAlarmDao()
    ws = FakeWebsocketHolder()
    states = {}

    monkeypatch.setattr(event_consumer, "alarm_record_dao", dao)
    monkeypatch.setattr(event_consumer, "websocket_holder", ws)
    monkeypatch.setattr(event_consumer.geofence_holder, "get_fence",
                        lambda fence_id: fence if fence_id == 7 else None)
    monkeypatch.setattr(
        event_consumer.geofence_holder, "get_hysteresis",
        lambda dev_eui, event_id: states.setdefault((dev_eui, event_id), ge.FenceHysteresis()))
    return {"fence": fence, "dao": dao, "ws": ws}


def make_setting(event_type=event_constant.ALARM_TYPE_CHECKIN, transition="both",
                 geofence_id=7, event_id=42):
    return EventTriggerRecord(
        id=event_id,
        event_name="围栏告警",
        event_type=event_type,
        device_range='["DEV1"]',
        ble_range='[]',
        location_mode="geo",
        transition=transition,
        geofence_id=geofence_id,
    )


def make_state(point, t, accuracy=None):
    return TrackerState(
        trackerId="DEV1",
        timestamp=t,
        last_update_time=t,
        lat=point[0],
        lon=point[1],
        accuracy=accuracy,
        type="wGS84",
    )


def consume(state, setting):
    return asyncio.run(event_consumer.single_event_consume(state, setting))


def test_geo_checkin_fires_on_enter(geo_env):
    setting = make_setting()
    consume(make_state(OUTSIDE, 0), setting)
    consume(make_state(INSIDE, 1 * S), setting)
    consume(make_state(INSIDE, 6 * S), setting)
    assert geo_env["dao"].records == []
    consume(make_state(INSIDE, 12 * S), setting)

    assert len(geo_env["dao"].records) == 1
    record = geo_env["dao"].records[0]
    loc = record["loc"]
    assert loc["lat"] == INSIDE[0]
    assert loc["lon"] == INSIDE[1]
    assert loc["coordSystem"] == "wgs84"
    assert loc["fence_id"] == 7
    assert loc["transition"] == ge.TRANSITION_ENTER
    assert record["event_id"] == 42
    assert len(geo_env["ws"].messages) == 1
    assert geo_env["ws"].messages[0]["data"]["DEV1"]["geofence"]["transition"] == "enter"


def test_geo_checkin_needs_no_beacons(geo_env):
    """BLE 模式下 used_beacons 为空会直接返回; geo 模式必须照样告警."""
    setting = make_setting()
    for t, point in [(0, OUTSIDE), (1 * S, INSIDE), (6 * S, INSIDE), (12 * S, INSIDE)]:
        state = make_state(point, t)
        assert state.used_beacons == []
        consume(state, setting)
    assert len(geo_env["dao"].records) == 1


def test_geo_position_detection_fires_on_exit(geo_env):
    setting = make_setting(event_type=event_constant.ALARM_TYPE_POSITION_DETECTION)
    consume(make_state(INSIDE, 0), setting)
    consume(make_state(OUTSIDE, 1 * S), setting)
    consume(make_state(OUTSIDE, 6 * S), setting)
    consume(make_state(OUTSIDE, 12 * S), setting)

    assert len(geo_env["dao"].records) == 1
    assert geo_env["dao"].records[0]["loc"]["transition"] == ge.TRANSITION_EXIT
    assert geo_env["dao"].records[0]["event_type"] == event_constant.ALARM_TYPE_POSITION_DETECTION


def test_transition_enter_ignores_exit(geo_env):
    setting = make_setting(transition="enter")
    consume(make_state(INSIDE, 0), setting)
    for t in (1 * S, 6 * S, 12 * S):
        consume(make_state(OUTSIDE, t), setting)
    assert geo_env["dao"].records == []


def test_transition_exit_ignores_enter(geo_env):
    setting = make_setting(transition="exit")
    consume(make_state(OUTSIDE, 0), setting)
    for t in (1 * S, 6 * S, 12 * S):
        consume(make_state(INSIDE, t), setting)
    assert geo_env["dao"].records == []


def test_doorway_loitering_produces_no_alarm(geo_env):
    """门口来回: 每次进出都不满足 3 点 + 10 s, 一条告警都不该出."""
    setting = make_setting()
    consume(make_state(OUTSIDE, 0), setting)
    t = 0
    for i in range(12):
        t += 3 * S
        point = INSIDE if i % 2 == 0 else OUTSIDE
        consume(make_state(point, t), setting)
    assert geo_env["dao"].records == []


def test_uplink_without_position_is_skipped(geo_env):
    setting = make_setting()
    state = TrackerState(trackerId="DEV1", timestamp=0, type="unknown")
    assert consume(state, setting) is None
    assert geo_env["dao"].records == []


def test_missing_fence_is_skipped(geo_env):
    setting = make_setting(geofence_id=999)
    for t, point in [(0, OUTSIDE), (1 * S, INSIDE), (6 * S, INSIDE), (12 * S, INSIDE)]:
        consume(make_state(point, t), setting)
    assert geo_env["dao"].records == []


def test_ble_mode_is_untouched(geo_env):
    """location_mode=ble 的老告警不走围栏分支."""
    setting = make_setting()
    setting.location_mode = "ble"
    assert setting.is_geo_mode() is False
    for t, point in [(0, OUTSIDE), (1 * S, INSIDE), (6 * S, INSIDE), (12 * S, INSIDE)]:
        consume(make_state(point, t), setting)
    assert geo_env["dao"].records == []
