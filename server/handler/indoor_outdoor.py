# -*- coding: utf-8 -*-
"""室内 / 室外迟滞状态机.

spec 默认参数（``HysteresisConfig``，可通过 :func:`configure` 覆盖）：

- 转室外：20 s 内连续 3 个 ``accuracy <= 25 m`` 的 GNSS fix，
  且 15 s 内没有有效 BLE。
- 转室内：10 s 内连续两次采样，每次至少 2 个「已配置」的 BLE 信标。
- 两个条件都不成立时保持当前状态，这就是迟滞本身
  （门口来回走不会抖动）。

``accuracy`` 为 None 时按通过精度门槛处理，并在日志里标注
（SenseCAP/ChirpStack 的测点里没有精度，见 docs/IMPL-NOTES.md）。

第一批把展示类型简化成「有 GPS fix 就是 wGS84」，这里替换掉它。
"""

from __future__ import annotations

import logging
import threading
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict, Optional

log = logging.getLogger(__name__)

MODE_INDOOR = "indoor"
MODE_OUTDOOR = "outdoor"


@dataclass
class HysteresisConfig:
    """迟滞参数。默认值来自 spec 步骤 3。"""
    outdoor_window_ms: int = 20_000
    outdoor_fix_count: int = 3
    outdoor_accuracy_max_m: float = 25.0
    outdoor_ble_quiet_ms: int = 15_000
    indoor_window_ms: int = 10_000
    indoor_sample_count: int = 2
    indoor_min_beacons: int = 2


_config = HysteresisConfig()


def configure(**kwargs) -> HysteresisConfig:
    """覆盖默认迟滞参数（部署时可按现场调）。"""
    global _config
    for key, value in kwargs.items():
        if value is None:
            continue
        if not hasattr(_config, key):
            raise KeyError(f"unknown hysteresis parameter: {key}")
        setattr(_config, key, value)
    return _config


def get_config() -> HysteresisConfig:
    return _config


@dataclass
class DeviceHysteresis:
    """单个设备的室内外迟滞状态。"""
    mode: Optional[str] = None
    gnss_fixes: Deque[int] = field(default_factory=deque)      # 通过精度门槛的 fix 时间
    ble_samples: Deque[int] = field(default_factory=deque)     # >= indoor_min_beacons 的采样时间
    last_valid_ble_ms: Optional[int] = None                    # 最近一次看到已配置信标

    def _trim(self, cfg: HysteresisConfig, now_ms: int):
        while self.gnss_fixes and now_ms - self.gnss_fixes[0] > cfg.outdoor_window_ms:
            self.gnss_fixes.popleft()
        while self.ble_samples and now_ms - self.ble_samples[0] > cfg.indoor_window_ms:
            self.ble_samples.popleft()

    def update(
        self,
        now_ms: int,
        has_fix: bool,
        accuracy: Optional[float],
        configured_beacon_count: int,
        cfg: Optional[HysteresisConfig] = None,
        dev_eui: str = "",
    ) -> Optional[str]:
        cfg = cfg or _config

        if has_fix:
            if accuracy is None:
                log.info("hysteresis %s: GNSS fix 无 accuracy, 按通过精度门槛处理", dev_eui or "-")
                self.gnss_fixes.append(now_ms)
            elif accuracy <= cfg.outdoor_accuracy_max_m:
                self.gnss_fixes.append(now_ms)
            else:
                log.info("hysteresis %s: 丢弃精度 %.1f m 的 fix", dev_eui or "-", accuracy)

        if configured_beacon_count > 0:
            self.last_valid_ble_ms = now_ms
        if configured_beacon_count >= cfg.indoor_min_beacons:
            self.ble_samples.append(now_ms)

        self._trim(cfg, now_ms)

        # 室内优先判定：有 BLE 就不可能满足「15 s 无有效 BLE」。
        if len(self.ble_samples) >= cfg.indoor_sample_count:
            self.mode = MODE_INDOOR
            return self.mode

        ble_quiet = (
            self.last_valid_ble_ms is None
            or now_ms - self.last_valid_ble_ms >= cfg.outdoor_ble_quiet_ms
        )
        if len(self.gnss_fixes) >= cfg.outdoor_fix_count and ble_quiet:
            self.mode = MODE_OUTDOOR
            return self.mode

        # 都不满足：保持当前状态（可能仍是 None，表示还没定论）。
        return self.mode


class IndoorOutdoorStateMachine:
    """按设备隔离的迟滞状态机，线程安全。"""

    def __init__(self):
        self._lock = threading.RLock()
        self._devices: Dict[str, DeviceHysteresis] = {}

    def update(self, dev_eui: str, now_ms: int, has_fix: bool,
               accuracy: Optional[float], configured_beacon_count: int) -> Optional[str]:
        with self._lock:
            state = self._devices.get(dev_eui)
            if state is None:
                state = DeviceHysteresis()
                self._devices[dev_eui] = state
            return state.update(
                now_ms=now_ms,
                has_fix=has_fix,
                accuracy=accuracy,
                configured_beacon_count=configured_beacon_count,
                cfg=_config,
                dev_eui=dev_eui,
            )

    def get_mode(self, dev_eui: str) -> Optional[str]:
        with self._lock:
            state = self._devices.get(dev_eui)
            return state.mode if state else None

    def reset(self, dev_eui: Optional[str] = None) -> None:
        with self._lock:
            if dev_eui is None:
                self._devices.clear()
            else:
                self._devices.pop(dev_eui, None)


state_machine = IndoorOutdoorStateMachine()
