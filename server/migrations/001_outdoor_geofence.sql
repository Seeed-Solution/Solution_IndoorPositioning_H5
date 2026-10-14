-- 001_outdoor_geofence.sql
--
-- 室外定位扩展的库结构变更。DAO 初始化只会 create_all（server/dao/base_dao.py），
-- 对已存在的表不会补列，所以新增列必须走这份显式迁移。
--
-- 本批（步骤 1/2/4/5）只建结构，围栏表可以是空表；
-- 围栏判定引擎在步骤 3 落地。
--
-- 幂等性：migrate.py 会吞掉 "duplicate column name" 与
-- "no such table: event_triggers"，其余语句本身带 IF NOT EXISTS。

-- 围栏定义表。
--   geometry_json: GeoJSON。多边形为 Polygon / MultiPolygon；
--                  圆形为 Point，半径写在 radius_m。
--   crs:           几何所用坐标系，wgs84 | gcj02。
CREATE TABLE IF NOT EXISTS geofences (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          VARCHAR(100) NOT NULL,
    geometry_json TEXT         NOT NULL,
    radius_m      FLOAT            NULL,
    crs           VARCHAR(16)  NOT NULL DEFAULT 'wgs84',
    enabled       BOOLEAN      NOT NULL DEFAULT 1,
    created_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    delete_time   DATETIME         NULL
);

CREATE INDEX IF NOT EXISTS idx_geofences_name ON geofences (name);
CREATE INDEX IF NOT EXISTS idx_geofences_enabled ON geofences (enabled);
CREATE INDEX IF NOT EXISTS idx_geofences_delete_time ON geofences (delete_time);

-- event_triggers 增加围栏相关列。
--   location_mode: ble | geo。旧行一律 ble，行为不变。
--   transition:    enter | exit | both。
ALTER TABLE event_triggers ADD COLUMN geofence_id INTEGER NULL;
ALTER TABLE event_triggers ADD COLUMN location_mode VARCHAR(8) NOT NULL DEFAULT 'ble';
ALTER TABLE event_triggers ADD COLUMN transition VARCHAR(8) NOT NULL DEFAULT 'both';

CREATE INDEX IF NOT EXISTS idx_event_triggers_geofence_id ON event_triggers (geofence_id);
CREATE INDEX IF NOT EXISTS idx_event_triggers_location_mode ON event_triggers (location_mode);

-- 旧行显式回填（DEFAULT 已覆盖新增列，这里兜住手工写过 NULL 的行）。
UPDATE event_triggers SET location_mode = 'ble' WHERE location_mode IS NULL;
UPDATE event_triggers SET transition = 'both' WHERE transition IS NULL;
