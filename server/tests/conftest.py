import copy
import json
from pathlib import Path

import pytest

from server.components.uplink_collector import cache as uplink_cache

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "uplinks"


@pytest.fixture(autouse=True)
def clear_uplink_cache():
    """UplinkCollector is a process-wide TTLCache; isolate every test."""
    uplink_cache.clear()
    yield
    uplink_cache.clear()


def _load(name: str) -> dict:
    with open(FIXTURE_DIR / name, encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture
def sensecap_fixture():
    return copy.deepcopy(_load("sensecap_gnss_ble.json"))


@pytest.fixture
def chirpstack_fixture():
    return copy.deepcopy(_load("chirpstack_gnss_ble.json"))
