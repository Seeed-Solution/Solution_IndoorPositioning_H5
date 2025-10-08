# -*- coding: utf-8 -*-
"""
事件管理器
负责管理事件触发条件的内存缓存，避免频繁的数据库查询
支持线程安全的增删改查操作
"""

import threading
import logging
from typing import Dict, List, Optional
from collections import defaultdict
from server.dao.event_trigger_dao import event_trigger_dao
from server.models import EventTriggerRecord

log = logging.getLogger(__name__)


class EventManager:
    """事件管理器 - 线程安全的事件缓存管理"""
    
    def __init__(self):
        # 线程锁，保证线程安全
        self._lock = threading.RLock()
        
        # 按设备EUI分组的事件缓存: {dev_eui: [EventTriggerRecord, ...]}
        self._device_events: Dict[str, List[EventTriggerRecord]] = defaultdict(list)
        
        # 是否已初始化
        self._initialized = False

    def initialize(self) -> bool:
        """初始化事件管理器，从数据库加载所有启用的事件"""
        with self._lock:
            try:
                log.info("Initializing EventManager...")
                
                # 清空现有缓存
                self._device_events.clear()
                
                # 从数据库加载所有启用的事件
                enabled_events, total = event_trigger_dao.get_enabled_event_triggers(page=1, page_size=10000)
                
                # 建立设备索引缓存
                for event in enabled_events:
                    self._add_event_to_cache(event)
                
                self._initialized = True
                log.info(f"EventManager initialized successfully. Loaded {len(enabled_events)} events.")
                return True
                
            except Exception as e:
                log.error(f"Failed to initialize EventManager: {e}", exc_info=True)
                return False

    def _add_event_to_cache(self, event: EventTriggerRecord):
        """将事件添加到缓存中（内部方法，需要在锁内调用）"""
        if not event or event.is_deleted() or not event.enable_status:
            return
        
        # 只添加到设备索引
        device_range = event.get_device_range_list()
        if device_range:
            for dev_eui in device_range:
                if dev_eui:  # 排除空字符串，保留通配符
                    self._device_events[dev_eui].append(event)

    def _remove_event_from_cache(self, event: EventTriggerRecord):
        """从缓存中移除事件（内部方法，需要在锁内调用）"""
        if not event:
            return
        
        # 只从设备索引中移除
        device_range = event.get_device_range_list()
        if device_range:
            for dev_eui in device_range:
                if dev_eui in self._device_events:
                    self._device_events[dev_eui] = [
                        e for e in self._device_events[dev_eui] if e.id != event.id
                    ]

    def create_event(self, event_name: str, event_type: int, 
                    device_range: List[str] = None, ble_range: List[str] = None,
                    time_range: int = 0, ble_rule: int = 0, dis_range: float = 0.0,
                    enable_status: bool = True) -> Optional[EventTriggerRecord]:
        """创建事件，先保存到数据库，再添加到缓存"""
        try:
            # 先保存到数据库
            event = event_trigger_dao.create_event_trigger(
                event_name=event_name,
                event_type=event_type,
                device_range=device_range,
                ble_range=ble_range,
                time_range=time_range,
                ble_rule=ble_rule,
                dis_range=dis_range,
                enable_status=enable_status
            )
            
            if event and enable_status:
                # 如果创建成功且启用，添加到缓存
                with self._lock:
                    self._add_event_to_cache(event)
                
                log.info(f"Created and cached event: {event_name} (ID: {event.id})")
            
            return event
            
        except Exception as e:
            log.error(f"Failed to create event {event_name}: {e}", exc_info=True)
            return None

    def update_event(self, event_id: int, **kwargs) -> Optional[EventTriggerRecord]:
        """更新事件，先更新数据库，再同步缓存"""
        try:
            # 先从数据库获取旧事件（用于移除旧的索引）
            old_event = event_trigger_dao.get_by_id(event_id)
            
            # 更新数据库
            updated_event = event_trigger_dao.update_event_trigger_info(event_id, **kwargs)
            
            if updated_event:
                with self._lock:
                    # 如果存在旧事件，先从缓存中移除
                    if old_event:
                        self._remove_event_from_cache(old_event)
                    
                    # 如果更新后的事件启用且未删除，添加到缓存
                    if updated_event.enable_status and not updated_event.is_deleted():
                        self._add_event_to_cache(updated_event)
                
                log.info(f"Updated and synced event cache: {event_id}")
            
            return updated_event
            
        except Exception as e:
            log.error(f"Failed to update event {event_id}: {e}", exc_info=True)
            return None

    def delete_event(self, event_id: int) -> bool:
        """删除事件（软删除），先更新数据库，再从缓存移除"""
        try:
            # 先获取要删除的事件
            old_event = event_trigger_dao.get_by_id(event_id)
            
            # 软删除数据库记录
            deleted_event = event_trigger_dao.soft_delete_event_trigger(event_id)
            
            if deleted_event and old_event:
                with self._lock:
                    # 从缓存中移除
                    self._remove_event_from_cache(old_event)
                
                log.info(f"Deleted and removed from cache event: {event_id}")
                return True
            
            return False
            
        except Exception as e:
            log.error(f"Failed to delete event {event_id}: {e}", exc_info=True)
            return False

    def enable_event(self, event_id: int) -> bool:
        """启用事件，更新数据库并添加到缓存"""
        try:
            # 更新数据库状态
            updated_event = event_trigger_dao.update_event_trigger_info(event_id, enable_status=True)
            
            if updated_event and not updated_event.is_deleted():
                with self._lock:
                    # 添加到缓存
                    self._add_event_to_cache(updated_event)
                
                log.info(f"Enabled and cached event: {event_id}")
                return True
            
            return False
            
        except Exception as e:
            log.error(f"Failed to enable event {event_id}: {e}", exc_info=True)
            return False

    def disable_event(self, event_id: int) -> bool:
        """禁用事件，更新数据库并从缓存移除"""
        try:
            # 先获取要禁用的事件
            old_event = event_trigger_dao.get_by_id(event_id)
            
            # 更新数据库状态
            updated_event = event_trigger_dao.update_event_trigger_info(event_id, enable_status=False)
            
            if updated_event and old_event:
                with self._lock:
                    # 从缓存中移除
                    self._remove_event_from_cache(old_event)
                
                log.info(f"Disabled and removed from cache event: {event_id}")
                return True
            
            return False
            
        except Exception as e:
            log.error(f"Failed to disable event {event_id}: {e}", exc_info=True)
            return False

    def get_events_for_device(self, dev_eui: str) -> List[EventTriggerRecord]:
        """获取指定设备的所有启用事件"""
        with self._lock:
            # 直接匹配的事件
            direct_events = self._device_events.get(dev_eui, []).copy()
            
            # 通配符事件
            wildcard_events = self._device_events.get('all', []).copy()
            
            # 合并并去重
            all_events = direct_events + wildcard_events
            unique_events = {event.id: event for event in all_events}
            
            return list(unique_events.values())

    def get_cache_stats(self) -> Dict[str, int]:
        """获取缓存统计信息"""
        with self._lock:
            total_events = sum(len(events) for events in self._device_events.values())
            return {
                "device_mappings": len(self._device_events),
                "total_cached_events": total_events,
                "initialized": self._initialized
            }

    def refresh_cache(self) -> bool:
        """刷新缓存，重新从数据库加载"""
        log.info("Refreshing event cache...")
        return self.initialize()

    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        with self._lock:
            return self._initialized


# 创建全局实例
event_manager = EventManager()