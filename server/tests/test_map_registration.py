"""Step 2: WebUIMapInfo.registration model + registration REST endpoints."""
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from server.models import (
    DashboardConfig,
    MapRegistration,
    WebUIMapInfo,
    GEOREF_POLAR_LIMIT_DEG,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
SHIPPED_CONFIG = REPO_ROOT / "server" / "config" / "json" / "dashboard_config.json"


# --------------------------------------------------------------------------- #
# Model
# --------------------------------------------------------------------------- #

def test_registration_is_optional_and_absent_means_indoor_only():
    info = WebUIMapInfo(width=50, height=40)
    assert info.registration is None


def test_registration_round_trips_through_json():
    info = WebUIMapInfo(
        width=50, height=40,
        registration={"origin_lat": 22.5231, "origin_lon": 113.9312,
                      "rotation_deg": 17.5, "scale": 1.02},
    )
    dumped = json.loads(info.model_dump_json())
    assert dumped["registration"]["origin_lat"] == pytest.approx(22.5231)
    restored = WebUIMapInfo(**dumped)
    assert restored.registration == info.registration


def test_registration_defaults_rotation_and_scale():
    reg = MapRegistration(origin_lat=0.0, origin_lon=0.0)
    assert reg.rotation_deg == 0.0
    assert reg.scale == 1.0


@pytest.mark.parametrize("payload", [
    {"origin_lat": 91.0, "origin_lon": 0.0},
    {"origin_lat": -91.0, "origin_lon": 0.0},
    {"origin_lat": 0.0, "origin_lon": 181.0},
    {"origin_lat": 0.0, "origin_lon": -181.0},
    {"origin_lat": 0.0, "origin_lon": 0.0, "scale": 0.0},
    {"origin_lat": 0.0, "origin_lon": 0.0, "scale": -1.0},
    {"origin_lat": 0.0, "origin_lon": 0.0, "scale": float("inf")},
    {"origin_lat": float("nan"), "origin_lon": 0.0},
    {"origin_lat": 0.0, "origin_lon": 0.0, "rotation_deg": float("nan")},
])
def test_registration_rejects_invalid(payload):
    with pytest.raises(ValidationError):
        MapRegistration(**payload)


def test_registration_refuses_polar_latitudes():
    ok = MapRegistration(origin_lat=GEOREF_POLAR_LIMIT_DEG, origin_lon=0.0)
    assert ok.origin_lat == GEOREF_POLAR_LIMIT_DEG
    with pytest.raises(ValidationError):
        MapRegistration(origin_lat=GEOREF_POLAR_LIMIT_DEG + 0.1, origin_lon=0.0)
    with pytest.raises(ValidationError):
        MapRegistration(origin_lat=-(GEOREF_POLAR_LIMIT_DEG + 0.1), origin_lon=0.0)


def test_shipped_config_still_loads_without_registration():
    with open(SHIPPED_CONFIG, encoding="utf-8") as fh:
        raw = json.load(fh)
    config = DashboardConfig(**raw)
    for entry in config.maps:
        if entry.map:
            assert entry.map.registration is None


# --------------------------------------------------------------------------- #
# REST endpoints
# --------------------------------------------------------------------------- #

@pytest.fixture
def api(tmp_path, monkeypatch):
    """FastAPI TestClient with dashboard_config.json redirected to tmp_path."""
    from fastapi.testclient import TestClient
    from server.config import config_manager
    from server.components.session_holder import session_holder
    from server.models import UserSessionInfo
    from server import main as main_mod

    cfg_path = tmp_path / "dashboard_config.json"
    cfg_path.write_text(json.dumps({
        "maps": [{
            "map": {"name": "Floor 1", "width": 50, "height": 40,
                    "background": "/uploads/floor1.png"},
            "beacons": [],
            "settings": {"signalPropagationFactor": 2.5},
        }],
    }), encoding="utf-8")
    monkeypatch.setattr(config_manager, "DASHBOARD_CONFIG_FILE_PATH", cfg_path)
    monkeypatch.setattr(config_manager, "dashboard_cfg", None)
    monkeypatch.setattr(main_mod, "dashboard_cfg", None)
    config_manager.load_dashboard_config()
    monkeypatch.setattr(main_mod, "dashboard_cfg", config_manager.dashboard_cfg)
    # auth_middleware 拦所有 /api/, check_authority 再查一次同一个 token。
    # 直接往内存 cache 里塞一条会话, 不碰 SQLite。
    token = "test-session-token"
    session_holder.cache[token] = UserSessionInfo(username="tester", role="tester")
    client = TestClient(main_mod.app, headers={"session-token": token})
    yield client, cfg_path
    session_holder.cache.pop(token, None)


def test_get_registration_null_before_configured(api):
    client, _ = api
    resp = client.get("/api/configuration/dashboard/maps/Floor 1/registration")
    assert resp.status_code == 200
    assert resp.json() is None


def test_get_registration_unknown_map_404(api):
    client, _ = api
    resp = client.get("/api/configuration/dashboard/maps/Nope/registration")
    assert resp.status_code == 404


def test_put_then_get_registration_persists_to_json(api):
    client, cfg_path = api
    body = {"origin_lat": 22.5231, "origin_lon": 113.9312,
            "rotation_deg": 17.5, "scale": 1.02}
    put = client.put("/api/configuration/dashboard/maps/Floor 1/registration", json=body)
    assert put.status_code == 200, put.text
    assert put.json()["registration"]["rotation_deg"] == pytest.approx(17.5)

    get = client.get("/api/configuration/dashboard/maps/Floor 1/registration")
    assert get.status_code == 200
    assert get.json()["origin_lon"] == pytest.approx(113.9312)

    # 落盘: 重新读文件也应带上 registration
    on_disk = json.loads(cfg_path.read_text(encoding="utf-8"))
    assert on_disk["maps"][0]["map"]["registration"]["origin_lat"] == pytest.approx(22.5231)


def test_put_registration_rejects_invalid(api):
    client, _ = api
    bad = client.put("/api/configuration/dashboard/maps/Floor 1/registration",
                     json={"origin_lat": 89.0, "origin_lon": 0.0})
    assert bad.status_code == 422
    bad2 = client.put("/api/configuration/dashboard/maps/Floor 1/registration",
                      json={"origin_lat": 0.0, "origin_lon": 0.0, "scale": 0})
    assert bad2.status_code == 422


def test_full_dashboard_config_api_keeps_registration(api):
    client, _ = api
    client.put("/api/configuration/dashboard/maps/Floor 1/registration",
               json={"origin_lat": 22.5231, "origin_lon": 113.9312})
    whole = client.get("/api/configuration/dashboard")
    assert whole.status_code == 200
    assert whole.json()["maps"][0]["map"]["registration"] is not None
