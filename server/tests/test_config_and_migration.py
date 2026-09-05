"""Step 4: outdoor config backward compatibility + explicit SQL migration."""
import json
import sqlite3
from pathlib import Path

from server.models import DashboardConfig
from server.migrations import migrate as migrate_mod

REPO_ROOT = Path(__file__).resolve().parents[2]
LEGACY_TRIGGER_DDL = """
CREATE TABLE event_triggers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_name VARCHAR(50) NOT NULL,
    event_type INTEGER NOT NULL DEFAULT 0,
    device_range TEXT NOT NULL DEFAULT '[]',
    ble_range TEXT NOT NULL DEFAULT '[]',
    time_range INTEGER NOT NULL DEFAULT 0,
    ble_rule INTEGER NOT NULL DEFAULT 0,
    dis_range FLOAT NOT NULL DEFAULT 0.0,
    enable_status BOOLEAN NOT NULL DEFAULT 1,
    create_time DATETIME NOT NULL,
    delete_time DATETIME NULL
)
"""


# --------------------------------------------------------------------------- #
# Config
# --------------------------------------------------------------------------- #

def test_existing_dashboard_config_file_still_loads():
    path = REPO_ROOT / "server" / "config" / "json" / "dashboard_config.json"
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    assert "outdoor" not in raw  # the shipped file predates this field
    config = DashboardConfig(**raw)
    assert len(config.maps) == len(raw["maps"])
    # Missing outdoor section is auto-filled with OSM.
    assert config.outdoor.defaultSource == "osm"
    assert config.outdoor.tileSources[0].url.startswith("https://")
    assert config.outdoor.tileSources[0].gcj02Correction is False


def test_outdoor_section_is_honoured():
    config = DashboardConfig(**{
        "maps": [],
        "outdoor": {
            "tileSources": [{
                "id": "amap", "name": "AMap",
                "url": "https://webrd0{s}.is.autonavi.com/appmaptile?x={x}&y={y}&z={z}",
                "coordSystem": "gcj02", "gcj02Correction": True,
            }],
            "defaultSource": "amap",
        },
    })
    assert config.outdoor.defaultSource == "amap"
    assert config.outdoor.tileSources[0].gcj02Correction is True


def test_unknown_default_source_falls_back_to_first():
    config = DashboardConfig(**{"maps": [], "outdoor": {"defaultSource": "does-not-exist"}})
    assert config.outdoor.defaultSource == config.outdoor.tileSources[0].id


def test_empty_tile_sources_are_refilled():
    config = DashboardConfig(**{"maps": [], "outdoor": {"tileSources": []}})
    assert len(config.outdoor.tileSources) >= 1


# --------------------------------------------------------------------------- #
# Migration
# --------------------------------------------------------------------------- #

def _legacy_db(tmp_path: Path) -> Path:
    db = tmp_path / "legacy.db"
    conn = sqlite3.connect(db)
    conn.execute(LEGACY_TRIGGER_DDL)
    conn.execute(
        "INSERT INTO event_triggers (event_name, event_type, create_time) VALUES (?, ?, ?)",
        ("legacy sos rule", 1, "2026-01-01 00:00:00"))
    conn.commit()
    conn.close()
    return db


def test_migration_adds_geofence_table_and_trigger_columns(tmp_path):
    db = _legacy_db(tmp_path)
    assert migrate_mod.migrate(str(db)) == 0

    conn = sqlite3.connect(db)
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "geofences" in tables

    geofence_cols = {r[1] for r in conn.execute("PRAGMA table_info(geofences)")}
    assert {"id", "name", "geometry_json", "radius_m", "crs", "enabled",
            "created_at"} <= geofence_cols
    # 本批只建结构，围栏表允许为空。
    assert conn.execute("SELECT COUNT(*) FROM geofences").fetchone()[0] == 0

    trigger_cols = {r[1] for r in conn.execute("PRAGMA table_info(event_triggers)")}
    assert {"geofence_id", "location_mode", "transition"} <= trigger_cols

    # 旧行保留, location_mode 回填为 ble。
    rows = conn.execute(
        "SELECT event_name, location_mode, transition, geofence_id FROM event_triggers"
    ).fetchall()
    assert rows == [("legacy sos rule", "ble", "both", None)]
    conn.close()


def test_migration_is_idempotent(tmp_path):
    db = _legacy_db(tmp_path)
    assert migrate_mod.migrate(str(db)) == 0
    assert migrate_mod.migrate(str(db)) == 0
    conn = sqlite3.connect(db)
    assert conn.execute("SELECT COUNT(*) FROM event_triggers").fetchone()[0] == 1
    applied = conn.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0]
    assert applied == 1
    conn.close()


def test_migration_reports_missing_database(tmp_path):
    assert migrate_mod.migrate(str(tmp_path / "nope.db")) == 1
