"""Uplink parsing tests for step 1 of the outdoor-positioning spec.

Covers: 4197/4198 -> lon/lat mapping, zero coordinates, missing components,
wrong key names, GNSS+BLE dual carry, and beacon preservation.
"""
import json

import pytest

import server.constant.message_constant as message_constant
from server.handler import message_format_hanlder as fmt


def _b(obj) -> bytes:
    return json.dumps(obj).encode("utf-8")


async def _replay_sensecap(fixture) -> "object":
    """Feed every message of the fixture; the 3000 packet returns the report."""
    report = None
    for msg in fixture["messages"]:
        result = await fmt.parse_sensecap_payload(msg["topic"], _b(msg["payload"]))
        if result is not None:
            report = result
    return report


# --------------------------------------------------------------------------- #
# SenseCAP
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_sensecap_maps_4197_to_lon_and_4198_to_lat(sensecap_fixture):
    report = await _replay_sensecap(sensecap_fixture)
    assert report is not None
    # 4197 carries 113.9421 (longitude), 4198 carries 22.5352 (latitude).
    assert report.loc == {"lat": 22.5352, "lon": 113.9421}
    assert report.locType == message_constant.TRACKER_POSITIONING_TYPE_GPS
    assert "alt" not in report.loc


@pytest.mark.asyncio
async def test_sensecap_keeps_beacons_alongside_gnss(sensecap_fixture):
    report = await _replay_sensecap(sensecap_fixture)
    macs = [b.macAddress for b in report.detectedBeacons]
    # GNSS no longer returns early, so the BLE scan in the same packet survives.
    assert macs == ["C3:00:00:3E:7D:DA", "C3:00:00:3E:7D:EF"]
    assert report.battery == 87
    assert report.sos == 0


@pytest.mark.asyncio
async def test_sensecap_accepts_zero_coordinates(sensecap_fixture):
    for msg in sensecap_fixture["messages"]:
        if msg["topic"].endswith("/4197"):
            msg["payload"]["value"] = 0
        if msg["topic"].endswith("/4198"):
            msg["payload"]["value"] = 0.0
    report = await _replay_sensecap(sensecap_fixture)
    # 0,0 is a legal fix: presence is checked with `is not None`, not truthiness.
    assert report.loc == {"lat": 0.0, "lon": 0.0}
    assert report.locType == message_constant.TRACKER_POSITIONING_TYPE_GPS


@pytest.mark.asyncio
async def test_sensecap_incomplete_fix_falls_back_to_ble(sensecap_fixture):
    sensecap_fixture["messages"] = [
        m for m in sensecap_fixture["messages"] if not m["topic"].endswith("/4198")
    ]
    report = await _replay_sensecap(sensecap_fixture)
    assert report.loc == {}
    assert report.locType == message_constant.TRACKER_POSITIONING_TYPE_BLE
    assert len(report.detectedBeacons) == 2


@pytest.mark.asyncio
async def test_sensecap_no_position_at_all_is_unknown(sensecap_fixture):
    sensecap_fixture["messages"] = [
        m for m in sensecap_fixture["messages"]
        if m["topic"].rsplit("/", 1)[-1] in ("4200", "3000")
    ]
    report = await _replay_sensecap(sensecap_fixture)
    assert report.loc == {}
    assert report.detectedBeacons == []
    assert report.locType == message_constant.TRACKER_POSITIONING_TYPE_UNKNOWN


@pytest.mark.asyncio
async def test_sensecap_bad_topic_returns_none():
    assert await fmt.parse_sensecap_payload("/nope/1/2", _b({"value": 1})) is None


# --------------------------------------------------------------------------- #
# ChirpStack
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_chirpstack_maps_lon_lat_and_keeps_beacons(chirpstack_fixture):
    report = await fmt.parse_chirpstack_payload(
        chirpstack_fixture["topic"], _b(chirpstack_fixture["payload"]))
    assert report.loc == {"lat": 22.5352, "lon": 113.9421}
    assert report.locType == message_constant.TRACKER_POSITIONING_TYPE_GPS
    # The GNSS early-return used to drop these.
    assert [b.macAddress for b in report.detectedBeacons] == [
        "C3:00:00:3E:7D:DA", "C3:00:00:3E:7D:EF"]
    assert report.sos == 1
    assert report.battery == 87
    assert report.trackerId == "2CF7F1C0530004AD"


@pytest.mark.asyncio
async def test_chirpstack_requires_both_lat_and_lon(chirpstack_fixture):
    entries = chirpstack_fixture["payload"]["object"]["messages"][0]
    chirpstack_fixture["payload"]["object"]["messages"][0] = [
        e for e in entries if e["measurementId"] != "4198"]
    report = await fmt.parse_chirpstack_payload(
        chirpstack_fixture["topic"], _b(chirpstack_fixture["payload"]))
    assert report.loc == {}
    assert report.locType == message_constant.TRACKER_POSITIONING_TYPE_BLE
    assert len(report.detectedBeacons) == 2


@pytest.mark.asyncio
async def test_chirpstack_accepts_zero_coordinates(chirpstack_fixture):
    for entry in chirpstack_fixture["payload"]["object"]["messages"][0]:
        if entry["measurementId"] in ("4197", "4198"):
            entry["measurementValue"] = 0
    report = await fmt.parse_chirpstack_payload(
        chirpstack_fixture["topic"], _b(chirpstack_fixture["payload"]))
    assert report.loc == {"lat": 0.0, "lon": 0.0}


@pytest.mark.asyncio
async def test_chirpstack_tolerates_macaddress_key(chirpstack_fixture):
    for entry in chirpstack_fixture["payload"]["object"]["messages"][0]:
        if entry["measurementId"] == "5002":
            entry["measurementValue"] = [{"macAddress": "aa:bb:cc:dd:ee:ff", "rssi": -60}]
    report = await fmt.parse_chirpstack_payload(
        chirpstack_fixture["topic"], _b(chirpstack_fixture["payload"]))
    assert [b.macAddress for b in report.detectedBeacons] == ["AA:BB:CC:DD:EE:FF"]


@pytest.mark.asyncio
async def test_chirpstack_empty_messages_returns_none(chirpstack_fixture):
    chirpstack_fixture["payload"]["object"]["messages"] = []
    assert await fmt.parse_chirpstack_payload(
        chirpstack_fixture["topic"], _b(chirpstack_fixture["payload"])) is None


def test_build_gnss_loc_rejects_non_numeric():
    assert fmt.build_gnss_loc("abc", 1.0) == {}
    assert fmt.build_gnss_loc(None, 1.0) == {}
    assert fmt.build_gnss_loc("113.9", "22.5") == {"lat": 22.5, "lon": 113.9}
