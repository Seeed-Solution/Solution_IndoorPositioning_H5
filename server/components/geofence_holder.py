# -*- coding: utf-8 -*-
"""围栏缓存 + 每个 (设备, 事件) 的围栏滞回状态.

- 编译后的 :class:`server.geofence.Geofence` 按 fence_id 缓存，
  CRUD 之后调用 :meth:`invalidate` 让它重新编译。
- 滞回状态按 ``(dev_eui, event_id)`` 隔离：同一个围栏被两个告警引用时，
  两条告警各自独立地走「连续 3 点 + 10 s」。
"""

import logging
import threading
from typing import Dict, Optional, Tuple

from server.geofence import FenceHysteresis, Geofence, build_from_record

log = logging.getLogger(__name__)


class GeofenceHolder:
    def __init__(self):
        self._lock = threading.RLock()
        self._fences: Dict[int, Optional[Geofence]] = {}
        self._states: Dict[Tuple[str, int], FenceHysteresis] = {}

    def get_fence(self, fence_id: Optional[int]) -> Optional[Geofence]:
        """按 ID 取围栏，未缓存时从库里读并编译。几何非法返回 None。"""
        if fence_id is None:
            return None
        with self._lock:
            if fence_id in self._fences:
                return self._fences[fence_id]
        fence = None
        try:
            from server.dao.geofence_dao import geofence_dao

            record = geofence_dao.get_by_id(fence_id)
            if record and not record.is_deleted() and record.enabled:
                fence = build_from_record(record)
            elif record:
                log.info("geofence %s 已删除或未启用，跳过", fence_id)
            else:
                log.warning("geofence %s 不存在", fence_id)
        except Exception as err:  # 几何非法不该拖垮告警流水线
            log.error("geofence %s 编译失败: %s", fence_id, err)
            fence = None
        with self._lock:
            self._fences[fence_id] = fence
        return fence

    def invalidate(self, fence_id: Optional[int] = None) -> None:
        """围栏被增删改后清缓存；不传 ID 就全清。"""
        with self._lock:
            if fence_id is None:
                self._fences.clear()
            else:
                self._fences.pop(fence_id, None)

    def get_hysteresis(self, dev_eui: str, event_id: int) -> FenceHysteresis:
        key = (dev_eui, event_id)
        with self._lock:
            state = self._states.get(key)
            if state is None:
                state = FenceHysteresis()
                self._states[key] = state
            return state

    def reset_hysteresis(self, dev_eui: Optional[str] = None,
                         event_id: Optional[int] = None) -> None:
        with self._lock:
            if dev_eui is None and event_id is None:
                self._states.clear()
                return
            for key in list(self._states):
                if (dev_eui is None or key[0] == dev_eui) and \
                        (event_id is None or key[1] == event_id):
                    del self._states[key]

    def clear(self) -> None:
        with self._lock:
            self._fences.clear()
            self._states.clear()


geofence_holder = GeofenceHolder()
