from server.models import (
    WebUIBeaconConfig, DashboardConfig
)

from typing import Optional


class BeaconHolder:
    beacon_map: dict[str, WebUIBeaconConfig] = {}

    def get_beacon(self, mac_address: str) -> Optional[WebUIBeaconConfig]:
        if len(self.beacon_map) == 0:
            return None
        mac_formatted = mac_address.replace(":", "").lower()
        return self.beacon_map.get(mac_formatted, None)

    def get_all_beacon_by_map(self) -> dict[str, list[WebUIBeaconConfig]]:
        """根据map分组返回所有beacon"""
        grouped_beacons = {}
        for beacon in self.beacon_map.values():
            map_name = beacon.map if beacon.map else "unknown map"
            if map_name not in grouped_beacons:
                grouped_beacons[map_name] = []
            grouped_beacons[map_name].append(beacon)
        return grouped_beacons

    def update_by_dashboard_config(self, dashboard_cfg: DashboardConfig):
        if dashboard_cfg and dashboard_cfg.maps and len(dashboard_cfg.maps) > 0:
            for config in dashboard_cfg.maps:
                if not config.beacons or len(config.beacons) == 0:
                    continue
                for beacon in config.beacons:
                    if not beacon.map:
                        beacon.map = config.map.name
                    self.beacon_map[beacon.macAddress.replace(":", "").lower()] = beacon


beacon_holder = BeaconHolder()
