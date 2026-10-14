"""Position-resolution tests for step 1: GNSS/BLE dual history and payload shape."""
import time
import server.constant.message_constant as message_constant
from server.handler import position_resolve_handler as prh
from server.components.device_holder import device_holder
from server.models import (
    TrackerReport, DetectedBeacon, TrackerState,
    PositionHistoryEntry, COORD_SYSTEM_METRIC, COORD_SYSTEM_WGS84,
)

EUI = "TESTEUI0000000A1"
NOW_MS = int(time.time() * 1000)


def _gnss_report(ts=NOW_MS, beacons=None):
    return TrackerReport(
        trackerId=EUI,
        timestamp=ts,
        detectedBeacons=beacons or [],
        loc={"lat": 22.5352, "lon": 113.9421},
        locType=message_constant.TRACKER_POSITIONING_TYPE_GPS,
        battery=87,
        sos=0,
    )


def test_legacy_triple_history_is_read_as_metric():
    state = TrackerState(trackerId=EUI, position_history=[(1.0, 2.0, 1757000000000)])
    entry = state.position_history[0]
    assert entry.coordSystem == COORD_SYSTEM_METRIC
    assert (entry.x, entry.y, entry.time) == (1.0, 2.0, 1757000000000)
    assert entry.lat is None and entry.lon is None


def test_gnss_only_report_produces_wgs84_state_without_xy():
    device_holder.set_tracker_state(EUI, TrackerState(trackerId=EUI))
    state = prh.do(_gnss_report())
    assert state.type == message_constant.TRACKER_STATE_TYPE_WGS84
    assert state.lat == 22.5352 and state.lon == 113.9421
    # GNSS must not be smuggled into the metric x/y fields any more.
    assert state.x is None and state.y is None
    assert len(state.position_history) == 1
    assert state.position_history[0].coordSystem == COORD_SYSTEM_WGS84


def test_gnss_appends_to_existing_metric_history():
    device_holder.set_tracker_state(EUI, TrackerState(
        trackerId=EUI,
        position_history=[PositionHistoryEntry(
            coordSystem=COORD_SYSTEM_METRIC, x=3.0, y=4.0,
            map="10.5 Floor", time=NOW_MS - 60_000)],
    ))
    state = prh.do(_gnss_report(ts=NOW_MS))
    systems = [e.coordSystem for e in state.position_history]
    # Both coordinate systems live in one time-ordered trail.
    assert systems == [COORD_SYSTEM_METRIC, COORD_SYSTEM_WGS84]
    assert [e.time for e in state.position_history] == sorted(
        e.time for e in state.position_history)


def test_history_older_than_window_is_pruned():
    old_ts = NOW_MS - prh.HISTORY_TIME_WINDOW_MS - 60_000
    device_holder.set_tracker_state(EUI, TrackerState(
        trackerId=EUI,
        position_history=[PositionHistoryEntry(
            coordSystem=COORD_SYSTEM_METRIC, x=1.0, y=1.0, time=old_ts)],
    ))
    state = prh.do(_gnss_report())
    assert all(e.coordSystem == COORD_SYSTEM_WGS84 for e in state.position_history)


def test_extract_gnss_fix_requires_both_components():
    assert prh.extract_gnss_fix(TrackerReport(
        trackerId=EUI, timestamp=1, loc={"lon": 113.0})) is None
    assert prh.extract_gnss_fix(TrackerReport(
        trackerId=EUI, timestamp=1, loc={"lat": 0.0, "lon": 0.0})) is not None


def test_report_without_position_stays_unknown():
    device_holder.set_tracker_state(EUI, TrackerState(trackerId=EUI))
    state = prh.do(TrackerReport(trackerId=EUI, timestamp=NOW_MS, loc={}))
    assert state.type == message_constant.TRACKER_STATE_TYPE_BLE_UNKNOWN
    assert state.lat is None


def test_tracker_update_payload_carries_wgs84_fields():
    state = TrackerState(
        trackerId=EUI, timestamp=1757000000000,
        lat=22.5352, lon=113.9421, alt=12.5, accuracy=8.0, fix_time=1757000000000,
        type=message_constant.TRACKER_STATE_TYPE_WGS84,
        position_history=[PositionHistoryEntry(
            coordSystem=COORD_SYSTEM_WGS84, lat=22.5352, lon=113.9421,
            time=1757000000000)],
    )
    msg = message_constant.get_tracker_update(state)
    data = msg["data"][EUI]
    assert data["position"]["lat"] == 22.5352
    assert data["position"]["lon"] == 113.9421
    assert data["position"]["coordSystem"] == "wgs84"
    assert data["type"] == message_constant.TRACKER_STATE_TYPE_WGS84
    assert data["accuracy"] == 8.0
    assert data["position_history"][0]["coordSystem"] == "wgs84"


def test_tracker_update_payload_metric_marks_coord_system():
    state = TrackerState(trackerId=EUI, timestamp=1, x=1.0, y=2.0,
                         type=message_constant.TRACKER_STATE_TYPE_BLE_CAL)
    data = message_constant.get_tracker_update(state)["data"][EUI]
    assert data["position"] == {"x": 1.0, "y": 2.0, "coordSystem": "metric"}
    assert data["lat"] is None
