# -*- coding: utf-8 -*-
from datetime import datetime
from typing import List, Tuple, Optional
from sqlalchemy import Column, String, DateTime, Integer, Boolean, Index, CHAR
from server.dao.base_dao import BaseDao, Base
from server.models import DeviceRecord


class DeviceTable(Base):
    """设备信息表"""
    __tablename__ = 'devices_list'

    id = Column(Integer, primary_key=True, autoincrement=True)
    dev_eui = Column(CHAR(16), nullable=False, unique=True, comment='设备EUI')
    device_name = Column(CHAR(20), nullable=False, comment='设备名称')
    group_id = Column(Integer, nullable=False, default=0, comment='分组ID')
    is_favorite = Column(Boolean, nullable=False, default=False, comment='是否收藏')
    battery_level = Column(Integer, nullable=True, comment='电量（0-100）')
    create_time = Column(DateTime, nullable=False, comment='创建时间')
    delete_time = Column(DateTime, nullable=True, comment='删除时间（软删除）')
    last_data_update_time = Column(DateTime, nullable=True, comment='最后一次数据更新时间')

    # 创建索引提高查询性能
    __table_args__ = (
        Index('idx_dev_eui', 'dev_eui'),
        Index('idx_device_name', 'device_name'),
        Index('idx_group_id', 'group_id'),
        Index('idx_is_favorite', 'is_favorite'),
        Index('idx_create_time', 'create_time'),
        Index('idx_delete_time', 'delete_time'),
        Index('idx_last_data_update_time', 'last_data_update_time'),
    )


class DeviceDao(BaseDao[DeviceRecord]):
    """设备信息数据访问对象"""

    def __init__(self):
        super().__init__(DeviceTable, DeviceRecord)

    def create_device(self, dev_eui: str, device_name: Optional[str] = None,
                      group_id: Optional[int] = 0, is_favorite: bool = False,
                      battery_level: Optional[int] = None) -> DeviceRecord:
        """创建新设备"""
        if device_name is None:
            device_name = dev_eui
        return self.createWithUnique({"dev_eui": dev_eui},
                                     dev_eui=dev_eui,
                                     device_name=device_name,
                                     group_id=group_id,
                                     is_favorite=is_favorite,
                                     battery_level=battery_level,
                                     create_time=datetime.now(),
                                     delete_time=None,
                                     last_data_update_time=None)
        # return self.create(
        #     dev_eui=dev_eui,
        #     device_name=device_name,
        #     group_id=group_id,
        #     is_favorite=is_favorite,
        #     battery_level=battery_level,
        #     create_time=datetime.now(),
        #     delete_time=None,
        #     last_data_update_time=None
        # )

    def get_device_by_dev_eui(self, dev_eui: str, include_deleted: bool = False) -> Optional[DeviceRecord]:
        """根据设备EUI获取设备"""
        with self.get_session() as session:
            query = session.query(self.table_class).filter(
                self.table_class.dev_eui == dev_eui
            )
            if not include_deleted:
                query = query.filter(self.table_class.delete_time.is_(None))
            
            table_obj = query.first()
            return self._to_model(table_obj)

    def get_active_devices(self, page: int = 1, page_size: int = 20) -> Tuple[List[DeviceRecord], int]:
        """获取所有未删除的设备（分页）"""
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

    def get_all_device(self) -> List[DeviceRecord]:
        condition = {
            "delete_time": None
        }
        return self.find_all_by_filters(order_by="create_time", desc_order=True, **condition)

    def get_devices_by_group(self, group_id: Optional[int], page: int = 1, 
                           page_size: int = 20, include_deleted: bool = False) -> Tuple[List[DeviceRecord], int]:
        """根据分组ID获取设备列表"""
        filters = {"group_id": group_id}
        if not include_deleted:
            filters["delete_time"] = None
            
        return self.find_by_filters(
            page=page,
            page_size=page_size,
            order_by='create_time',
            desc_order=True,
            **filters
        )


    def get_favorite_devices(self, page: int = 1, page_size: int = 20) -> Tuple[List[DeviceRecord], int]:
        """获取收藏设备列表"""
        filters = {
            "is_favorite": True,
            "delete_time": None
        }
        return self.find_by_filters(
            page=page,
            page_size=page_size,
            order_by='create_time',
            desc_order=True,
            **filters
        )

    def search_devices(self, keyword: str, page: int = 1, page_size: int = 20,
                      include_deleted: bool = False) -> Tuple[List[DeviceRecord], int]:
        """按关键词搜索设备（按设备名称或EUI）"""
        with self.get_session() as session:
            query = session.query(self.table_class).filter(
                (self.table_class.device_name.like(f'%{keyword}%')) |
                (self.table_class.dev_eui.like(f'%{keyword}%'))
            )
            
            if not include_deleted:
                query = query.filter(self.table_class.delete_time.is_(None))
            
            query = query.order_by(self.table_class.create_time.desc())
            
            total = query.count()
            offset = (page - 1) * page_size
            table_objs = query.offset(offset).limit(page_size).all()
            
            return [self._to_model(obj) for obj in table_objs], total

    def update_device_info(self, dev_eui: str, **kwargs) -> Optional[DeviceRecord]:
        """更新设备信息"""
        return self.update_by_dev_eui(dev_eui, **kwargs)

    def update_device_status(self, dev_eui: str,
                           battery_level: Optional[int] = None,
                           last_message_timestamp_ms: Optional[int] = None) -> Optional[DeviceRecord]:
        """更新设备状态（在线状态、电量等）"""
        device = self.get_device_by_dev_eui(dev_eui, include_deleted=False)
        if not device:
            return None
        
        update_data = {
        }
        
        if battery_level is not None and battery_level != -1:
            update_data["battery_level"] = battery_level
            
        if last_message_timestamp_ms:
            update_data["last_data_update_time"] = datetime.fromtimestamp(last_message_timestamp_ms / 1000)
        else:
            update_data["last_data_update_time"] = datetime.now()
        
        return self.update_by_id(device.id, **update_data)

    def toggle_favorite(self, device_id: int) -> Optional[DeviceRecord]:
        """切换设备收藏状态"""
        device = self.get_by_id(device_id)
        if not device or device.is_deleted():
            return None
        
        return self.update_by_id(device_id, is_favorite=not device.is_favorite)

    def soft_delete_device(self, device_id: int) -> Optional[DeviceRecord]:
        """软删除设备"""
        return self.update_by_id(device_id, delete_time=datetime.now())

    def restore_device(self, device_id: int) -> Optional[DeviceRecord]:
        """恢复已删除的设备"""
        return self.update_by_id(device_id, delete_time=None)

    def hard_delete_device(self, device_id: int) -> bool:
        """硬删除设备（物理删除）"""
        return self.delete_by_id(device_id)

    def dev_eui_exists(self, dev_eui: str, exclude_id: Optional[int] = None,
                      include_deleted: bool = False) -> bool:
        """检查设备EUI是否已存在"""
        with self.get_session() as session:
            query = session.query(self.table_class).filter(
                self.table_class.dev_eui == dev_eui
            )
            
            if exclude_id:
                query = query.filter(self.table_class.id != exclude_id)
            
            if not include_deleted:
                query = query.filter(self.table_class.delete_time.is_(None))
            
            return query.first() is not None

    def count_devices(self, include_deleted: bool = False, group_id: Optional[int] = None) -> int:
        """统计设备数量"""
        with self.get_session() as session:
            query = session.query(self.table_class)
            
            if not include_deleted:
                query = query.filter(self.table_class.delete_time.is_(None))
            
            if group_id is not None:
                query = query.filter(self.table_class.group_id == group_id)
            return query.count()

    def update_devices_group(self, old_group_id: Optional[int], new_group_id: Optional[int]) -> int:
        """批量更新设备的分组ID（当分组被删除或合并时使用）"""
        with self.get_session() as session:
            updated_count = session.query(self.table_class).filter(
                self.table_class.group_id == old_group_id,
                self.table_class.delete_time.is_(None)
            ).update({
                self.table_class.group_id: new_group_id
            })
            return updated_count

    def batch_update_devices_group(self, dev_eui_list: List[str], new_group_id: int) -> int:
        """批量更新指定设备列表的分组ID"""
        if not dev_eui_list:
            return 0
            
        with self.get_session() as session:
            updated_count = session.query(self.table_class).filter(
                self.table_class.dev_eui.in_(dev_eui_list),
                self.table_class.delete_time.is_(None)
            ).update({
                self.table_class.group_id: new_group_id
            }, synchronize_session=False)  # 批量更新时需要设置此参数
            return updated_count

    def get_devices_by_battery_level(self, min_level: Optional[int] = None,
                                   max_level: Optional[int] = None,
                                   page: int = 1, page_size: int = 20) -> Tuple[List[DeviceRecord], int]:
        """根据电量范围获取设备列表"""
        with self.get_session() as session:
            query = session.query(self.table_class).filter(
                self.table_class.delete_time.is_(None)
            )
            
            if min_level is not None:
                query = query.filter(self.table_class.battery_level >= min_level)
            
            if max_level is not None:
                query = query.filter(self.table_class.battery_level <= max_level)
            
            # 按电量升序排列（低电量优先）
            query = query.order_by(self.table_class.battery_level.asc())
            
            total = query.count()
            offset = (page - 1) * page_size
            table_objs = query.offset(offset).limit(page_size).all()
            
            return [self._to_model(obj) for obj in table_objs], total


# 创建全局实例
device_dao = DeviceDao()