# -*- coding: utf-8 -*-
from datetime import datetime
from typing import List, Tuple, Optional
from sqlalchemy import Column, String, DateTime, Integer, Boolean, Index, Float, Text
from server.dao.base_dao import BaseDao, Base
from server.models import EventTriggerRecord


class EventTriggerTable(Base):
    """事件触发条件表"""
    __tablename__ = 'event_triggers'

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_name = Column(String(50), nullable=False, comment='事件名称')
    event_type = Column(Integer, nullable=False, default=0, comment='事件类型') ## 1:sos, 2:offline, 3:checkin, 4:leaving
    device_range = Column(Text, nullable=False, default='[]', comment='设备范围JSON')
    ble_range = Column(Text, nullable=False, default='[]', comment='BLE范围JSON')
    time_range = Column(Integer, nullable=False, default=0, comment='时间范围')
    ble_rule = Column(Integer, nullable=False, default=0, comment='BLE规则')
    dis_range = Column(Float, nullable=False, default=0.0, comment='距离范围')
    enable_status = Column(Boolean, nullable=False, default=True, comment='启用状态')
    create_time = Column(DateTime, nullable=False, comment='创建时间')
    delete_time = Column(DateTime, nullable=True, comment='删除时间（软删除）')
    # 步骤 3 新增列，与 migrations/001_outdoor_geofence.sql 对齐
    geofence_id = Column(Integer, nullable=True, comment='地理围栏ID')
    location_mode = Column(String(8), nullable=False, default='ble', comment='判定模式 ble|geo')
    transition = Column(String(8), nullable=False, default='both', comment='进出方向 enter|exit|both')

    # 创建索引提高查询性能
    __table_args__ = (
        Index(f'idx_{__tablename__}_event_name', 'event_name'),
        Index(f'idx_{__tablename__}_event_type', 'event_type'),
        Index(f'idx_{__tablename__}_enable_status', 'enable_status'),
        Index(f'idx_{__tablename__}_create_time', 'create_time'),
        Index(f'idx_{__tablename__}_delete_time', 'delete_time'),
    )


class EventTriggerDao(BaseDao[EventTriggerRecord]):
    """事件触发条件数据访问对象"""

    def __init__(self):
        super().__init__(EventTriggerTable, EventTriggerRecord)
        # 初始化默认数据
        self._init_default_data()

    def create_event_trigger(self, event_name: str, event_type: int, 
                           device_range: List[str] = None, ble_range: List[str] = None,
                           time_range: int = 0, ble_rule: int = 0, dis_range: float = 0.0,
                           enable_status: bool = True, geofence_id: Optional[int] = None,
                           location_mode: str = 'ble', transition: str = 'both') -> EventTriggerRecord:
        """创建新的事件触发条件"""
        import json
        
        device_range_json = json.dumps(device_range or [], ensure_ascii=False)
        ble_range_json = json.dumps(ble_range or [], ensure_ascii=False)
        
        return self.create(
            event_name=event_name,
            event_type=event_type,
            device_range=device_range_json,
            ble_range=ble_range_json,
            time_range=time_range,
            ble_rule=ble_rule,
            dis_range=dis_range,
            enable_status=enable_status,
            create_time=datetime.now(),
            delete_time=None,
            geofence_id=geofence_id,
            location_mode=location_mode or 'ble',
            transition=transition or 'both'
        )

    def get_event_trigger_by_name(self, event_name: str, include_deleted: bool = False) -> Optional[EventTriggerRecord]:
        """根据事件名称获取事件触发条件"""
        with self.get_session() as session:
            query = session.query(self.table_class).filter(
                self.table_class.event_name == event_name
            )
            if not include_deleted:
                query = query.filter(self.table_class.delete_time.is_(None))
            
            table_obj = query.first()
            return self._to_model(table_obj)

    def get_active_event_triggers(self, page: int = 1, page_size: int = 20) -> Tuple[List[EventTriggerRecord], int]:
        """获取所有未删除的事件触发条件（分页）"""
        condition = {
            "delete_time": None
        }
        return self.find_by_filters(
            page=page,
            page_size=page_size,
            order_by='create_time',
            desc_order=True,
            **condition
        )

    def get_enabled_event_triggers(self, page: int = 1, page_size: int = 20) -> Tuple[List[EventTriggerRecord], int]:
        """获取所有启用的事件触发条件（分页）"""
        condition = {
            "enable_status": True,
            "delete_time": None
        }
        return self.find_by_filters(
            page=page,
            page_size=page_size,
            order_by='create_time',
            desc_order=True,
            **condition
        )

    def get_event_triggers_by_type(self, event_type: int, page: int = 1, 
                                 page_size: int = 20, include_deleted: bool = False) -> Tuple[List[EventTriggerRecord], int]:
        """根据事件类型获取事件触发条件列表"""
        filters = {"event_type": event_type}
        if not include_deleted:
            filters["delete_time"] = None
            
        return self.find_by_filters(
            page=page,
            page_size=page_size,
            order_by='create_time',
            desc_order=True,
            **filters
        )

    def get_all_event_by_type(self, event_type: int) -> List[EventTriggerRecord]:
        filters = {
            "event_type": event_type,
            "delete_time": None
        }
        return self.find_all_by_filters(
            order_by='create_time',
            desc_order=True,
            **filters)



    def search_event_triggers(self, keyword: str, page: int = 1, page_size: int = 20,
                            include_deleted: bool = False) -> Tuple[List[EventTriggerRecord], int]:
        """按关键词搜索事件触发条件（按事件名称）"""
        with self.get_session() as session:
            query = session.query(self.table_class).filter(
                self.table_class.event_name.like(f'%{keyword}%')
            )
            
            if not include_deleted:
                query = query.filter(self.table_class.delete_time.is_(None))
            
            query = query.order_by(self.table_class.create_time.desc())
            
            total = query.count()
            offset = (page - 1) * page_size
            table_objs = query.offset(offset).limit(page_size).all()
            
            return [self._to_model(obj) for obj in table_objs], total

    def update_event_trigger_info(self, event_id: int, **kwargs) -> Optional[EventTriggerRecord]:
        """更新事件触发条件信息"""
        # 处理列表字段
        if 'device_range_list' in kwargs:
            import json
            kwargs['device_range'] = json.dumps(kwargs.pop('device_range_list'), ensure_ascii=False)
        if 'ble_range_list' in kwargs:
            import json
            kwargs['ble_range'] = json.dumps(kwargs.pop('ble_range_list'), ensure_ascii=False)
        
        return self.update_by_id(event_id, **kwargs)

    def toggle_event_trigger_status(self, event_id: int) -> Optional[EventTriggerRecord]:
        """切换事件触发条件启用状态"""
        event_trigger = self.get_by_id(event_id)
        if not event_trigger or event_trigger.is_deleted():
            return None
        
        return self.update_by_id(event_id, enable_status=not event_trigger.enable_status)

    def soft_delete_event_trigger(self, event_id: int) -> Optional[EventTriggerRecord]:
        """软删除事件触发条件"""
        return self.update_by_id(event_id, delete_time=datetime.now())

    def restore_event_trigger(self, event_id: int) -> Optional[EventTriggerRecord]:
        """恢复已删除的事件触发条件"""
        return self.update_by_id(event_id, delete_time=None)

    def hard_delete_event_trigger(self, event_id: int) -> bool:
        """硬删除事件触发条件（物理删除）"""
        return self.delete_by_id(event_id)

    def event_name_exists(self, event_name: str, exclude_id: Optional[int] = None,
                         include_deleted: bool = False) -> bool:
        """检查事件名称是否已存在"""
        with self.get_session() as session:
            query = session.query(self.table_class).filter(
                self.table_class.event_name == event_name
            )
            
            if exclude_id:
                query = query.filter(self.table_class.id != exclude_id)
            
            if not include_deleted:
                query = query.filter(self.table_class.delete_time.is_(None))
            
            return query.first() is not None

    def count_event_triggers(self, include_deleted: bool = False, event_type: Optional[int] = None,
                           enable_status: Optional[bool] = None) -> int:
        """统计事件触发条件数量"""
        with self.get_session() as session:
            query = session.query(self.table_class)
            
            if not include_deleted:
                query = query.filter(self.table_class.delete_time.is_(None))
            
            if event_type is not None:
                query = query.filter(self.table_class.event_type == event_type)
            
            if enable_status is not None:
                query = query.filter(self.table_class.enable_status == enable_status)
            
            return query.count()

    def get_event_triggers_for_device(self, dev_eui: str, enabled_only: bool = True) -> List[EventTriggerRecord]:
        """获取包含指定设备的事件触发条件"""
        with self.get_session() as session:
            query = session.query(self.table_class)
            
            if enabled_only:
                query = query.filter(
                    self.table_class.enable_status == True,
                    self.table_class.delete_time.is_(None)
                )
            else:
                query = query.filter(self.table_class.delete_time.is_(None))
            
            # 获取所有记录，然后在Python中过滤
            all_triggers = query.all()
            matching_triggers = []
            
            for trigger in all_triggers:
                trigger_model = self._to_model(trigger)
                device_range_list = trigger_model.get_device_range_list()
                
                # 检查设备是否在范围内（支持通配符或全匹配）
                if not device_range_list or dev_eui in device_range_list or '*' in device_range_list:
                    matching_triggers.append(trigger_model)
            
            return matching_triggers

    def get_event_triggers_for_ble(self, ble_mac: str, enabled_only: bool = True) -> List[EventTriggerRecord]:
        """获取包含指定BLE MAC的事件触发条件"""
        with self.get_session() as session:
            query = session.query(self.table_class)
            
            if enabled_only:
                query = query.filter(
                    self.table_class.enable_status == True,
                    self.table_class.delete_time.is_(None)
                )
            else:
                query = query.filter(self.table_class.delete_time.is_(None))
            
            # 获取所有记录，然后在Python中过滤
            all_triggers = query.all()
            matching_triggers = []
            
            for trigger in all_triggers:
                trigger_model = self._to_model(trigger)
                ble_range_list = trigger_model.get_ble_range_list()
                
                # 检查BLE MAC是否在范围内（支持通配符或全匹配）
                if not ble_range_list or ble_mac in ble_range_list or '*' in ble_range_list:
                    matching_triggers.append(trigger_model)
            
            return matching_triggers

    def get_event_triggers_by_distance_range(self, min_distance: float, max_distance: float,
                                           enabled_only: bool = True) -> List[EventTriggerRecord]:
        """根据距离范围获取事件触发条件"""
        with self.get_session() as session:
            query = session.query(self.table_class).filter(
                self.table_class.dis_range >= min_distance,
                self.table_class.dis_range <= max_distance
            )
            
            if enabled_only:
                query = query.filter(
                    self.table_class.enable_status == True,
                    self.table_class.delete_time.is_(None)
                )
            else:
                query = query.filter(self.table_class.delete_time.is_(None))
            
            table_objs = query.all()
            return [self._to_model(obj) for obj in table_objs]

    def _is_table_empty(self) -> bool:
        """检查表是否为空（只考虑未被软删除的数据）"""
        with self.get_session() as session:
            count = session.query(self.table_class).count()
            return count == 0

    def _init_default_data(self):
        """初始化默认数据，只在表为空时执行"""
        if self._is_table_empty():
            import json
            from datetime import datetime
            
            # 创建两条初始数据
            default_data = [
                {
                    "event_name": "SOS Alarm",
                    "event_type": 1,
                    "device_range": json.dumps(["all"], ensure_ascii=False),
                    "ble_range": json.dumps([], ensure_ascii=False),
                    "time_range": 0,
                    "ble_rule": 0,
                    "dis_range": 0.0,
                    "enable_status": True,
                    "create_time": datetime.now(),
                    "delete_time": None
                },
                {
                    "event_name": "Offline Alarm",
                    "event_type": 2,
                    "device_range": json.dumps(["all"], ensure_ascii=False),
                    "ble_range": json.dumps([], ensure_ascii=False),
                    "time_range": 0,
                    "ble_rule": 0,
                    "dis_range": 0.0,
                    "enable_status": True,
                    "create_time": datetime.now(),
                    "delete_time": None
                }
            ]
            
            # 批量插入初始数据
            with self.get_session() as session:
                for data in default_data:
                    instance = self.table_class(**data)
                    session.add(instance)


# 创建全局实例
event_trigger_dao = EventTriggerDao()
