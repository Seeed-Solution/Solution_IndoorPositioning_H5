"""
设备状态管理器
负责管理所有设备的实时状态数据
"""

from typing import Dict, Optional, List
from server.models import TrackerState
import threading


class DeviceHolder:
    """设备状态管理器"""
    
    def __init__(self):
        self._tracker_states: Dict[str, TrackerState] = {}
        self._lock = threading.Lock()
    
    def get_tracker_state(self, tracker_id: str) -> Optional[TrackerState]:
        """获取指定设备的状态"""
        with self._lock:
            return self._tracker_states.get(tracker_id, None)
    
    def set_tracker_state(self, tracker_id: str, state: TrackerState) -> None:
        """设置指定设备的状态"""
        with self._lock:
            self._tracker_states[tracker_id] = state
    
    def update_tracker_online_status(self, tracker_id: str, online_status: str) -> None:
        """更新设备在线状态"""
        with self._lock:
            if tracker_id in self._tracker_states:
                self._tracker_states[tracker_id].online = online_status
    
    def update_tracker_last_update_time(self, tracker_id: str, timestamp: int) -> None:
        """更新设备最后更新时间"""
        with self._lock:
            if tracker_id in self._tracker_states:
                self._tracker_states[tracker_id].last_update_time = timestamp
    
    def update_tracker_battery(self, tracker_id: str, battery: int) -> None:
        """更新设备电池电量"""
        with self._lock:
            if tracker_id in self._tracker_states:
                self._tracker_states[tracker_id].battery = battery
    
    def update_tracker_sos(self, tracker_id: str, sos: int) -> None:
        """更新设备SOS状态"""
        with self._lock:
            if tracker_id in self._tracker_states:
                self._tracker_states[tracker_id].sos = sos
    
    def get_tracker_sos(self, tracker_id: str) -> Optional[int]:
        """获取设备SOS状态"""
        with self._lock:
            tracker = self._tracker_states.get(tracker_id)
            return tracker.sos if tracker else None
    
    def get_all_tracker_states(self) -> Dict[str, TrackerState]:
        """获取所有设备状态的副本"""
        with self._lock:
            return self._tracker_states.copy()
    
    def get_tracker_count(self) -> int:
        """获取设备数量"""
        with self._lock:
            return len(self._tracker_states)
    
    def clear_all_tracker_states(self) -> None:
        """清空所有设备状态"""
        with self._lock:
            self._tracker_states.clear()
    
    def remove_tracker_state(self, tracker_id: str) -> bool:
        """移除指定设备状态"""
        with self._lock:
            if tracker_id in self._tracker_states:
                del self._tracker_states[tracker_id]
                return True
            return False
    
    def has_tracker(self, tracker_id: str) -> bool:
        """检查设备是否存在"""
        with self._lock:
            return tracker_id in self._tracker_states
    
    def get_tracker_ids(self) -> List[str]:
        """获取所有设备ID列表"""
        with self._lock:
            return list(self._tracker_states.keys())


# 全局设备状态管理器实例
device_holder = DeviceHolder()