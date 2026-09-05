# -*- coding: utf-8 -*-
"""地理围栏 DAO.

表结构由 ``server/migrations/001_outdoor_geofence.sql`` 建好；
这里的 ORM 定义必须与那份迁移保持一致（BaseDao 的 create_all 只在
全新库上生效，对已存在的表不会补列）。
"""
from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy import Column, String, DateTime, Integer, Boolean, Index, Float, Text

from server.dao.base_dao import BaseDao, Base
from server.models import GeofenceRecord


class GeofenceTable(Base):
    """地理围栏表"""
    __tablename__ = 'geofences'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, comment='围栏名称')
    geometry_json = Column(Text, nullable=False, comment='GeoJSON 几何')
    radius_m = Column(Float, nullable=True, comment='圆形围栏半径（米）')
    crs = Column(String(16), nullable=False, default='wgs84', comment='坐标系 wgs84|gcj02')
    enabled = Column(Boolean, nullable=False, default=True, comment='是否启用')
    created_at = Column(DateTime, nullable=False, default=datetime.now, comment='创建时间')
    delete_time = Column(DateTime, nullable=True, comment='删除时间（软删除）')

    __table_args__ = (
        Index(f'idx_{__tablename__}_name', 'name'),
        Index(f'idx_{__tablename__}_enabled', 'enabled'),
        Index(f'idx_{__tablename__}_delete_time', 'delete_time'),
    )


class GeofenceDao(BaseDao[GeofenceRecord]):
    """地理围栏数据访问对象"""

    def __init__(self):
        super().__init__(GeofenceTable, GeofenceRecord)

    def create_geofence(self, name: str, geometry_json: str, radius_m: Optional[float] = None,
                        crs: str = 'wgs84', enabled: bool = True) -> GeofenceRecord:
        return self.create(
            name=name,
            geometry_json=geometry_json,
            radius_m=radius_m,
            crs=crs or 'wgs84',
            enabled=enabled,
            created_at=datetime.now(),
            delete_time=None,
        )

    def get_active_geofences(self, page: int = 1, page_size: int = 100
                             ) -> Tuple[List[GeofenceRecord], int]:
        """未删除的围栏（分页）"""
        return self.find_by_filters(
            page=page, page_size=page_size,
            order_by='created_at', desc_order=True,
            delete_time=None,
        )

    def get_enabled_geofences(self) -> List[GeofenceRecord]:
        """所有启用且未删除的围栏"""
        return self.find_all_by_filters(
            order_by='created_at', desc_order=True,
            enabled=True, delete_time=None,
        )

    def get_geofence_by_name(self, name: str, include_deleted: bool = False
                             ) -> Optional[GeofenceRecord]:
        with self.get_session() as session:
            query = session.query(self.table_class).filter(self.table_class.name == name)
            if not include_deleted:
                query = query.filter(self.table_class.delete_time.is_(None))
            return self._to_model(query.first())

    def name_exists(self, name: str, exclude_id: Optional[int] = None) -> bool:
        with self.get_session() as session:
            query = session.query(self.table_class).filter(
                self.table_class.name == name,
                self.table_class.delete_time.is_(None),
            )
            if exclude_id:
                query = query.filter(self.table_class.id != exclude_id)
            return query.first() is not None

    def update_geofence(self, fence_id: int, **kwargs) -> Optional[GeofenceRecord]:
        return self.update_by_id(fence_id, **kwargs)

    def soft_delete_geofence(self, fence_id: int) -> Optional[GeofenceRecord]:
        return self.update_by_id(fence_id, delete_time=datetime.now())


# 全局实例
geofence_dao = GeofenceDao()
