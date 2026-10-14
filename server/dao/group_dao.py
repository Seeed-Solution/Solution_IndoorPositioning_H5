# -*- coding: utf-8 -*-
from datetime import datetime
from typing import List, Tuple, Optional
from sqlalchemy import Column, String, DateTime, Integer, Index
from server.dao.base_dao import BaseDao, Base
from server.models import GroupRecord


class GroupTable(Base):
    """分组表"""
    __tablename__ = 'device_groups'

    id = Column(Integer, primary_key=True, autoincrement=True)
    group_name = Column(String(100), nullable=False, comment='分组名称')
    create_time = Column(DateTime, nullable=False, comment='创建时间')
    delete_time = Column(DateTime, nullable=True, comment='删除时间（软删除）')

    # 创建索引提高查询性能
    __table_args__ = (
        Index(f'idx_{__tablename__}_group_name', 'group_name'),
        Index(f'idx_{__tablename__}_create_time', 'create_time'),
        Index(f'idx_{__tablename__}_delete_time', 'delete_time'),
    )


class GroupDao(BaseDao[GroupRecord]):
    """分组管理数据访问对象"""

    def __init__(self):
        super().__init__(GroupTable, GroupRecord)

    def create_group(self, group_name: str) -> GroupRecord:
        """创建新分组"""
        return self.create(
            group_name=group_name,
            create_time=datetime.now(),
            delete_time=None
        )

    def get_group_by_name(self, group_name: str, include_deleted: bool = False) -> Optional[GroupRecord]:
        """根据分组名称获取分组"""
        with self.get_session() as session:
            query = session.query(self.table_class).filter(
                self.table_class.group_name == group_name
            )
            if not include_deleted:
                query = query.filter(self.table_class.delete_time.is_(None))
            
            table_obj = query.first()
            return self._to_model(table_obj)

    def get_active_groups(self, page: int = 1, page_size: int = 20) -> Tuple[List[GroupRecord], int]:
        """获取所有未删除的分组（分页）"""
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

    def get_all_groups(self, page: int = 1, page_size: int = 20, 
                      include_deleted: bool = False) -> Tuple[List[GroupRecord], int]:
        """获取所有分组（包括已删除的，分页）"""
        if include_deleted:
            # 获取所有分组
            with self.get_session() as session:
                query = session.query(self.table_class).order_by(
                    self.table_class.create_time.desc()
                )
                total = query.count()
                offset = (page - 1) * page_size
                table_objs = query.offset(offset).limit(page_size).all()
                return [self._to_model(obj) for obj in table_objs], total
        else:
            return self.get_active_groups(page, page_size)

    def update_group_name(self, group_id: int, new_name: str) -> Optional[GroupRecord]:
        """更新分组名称"""
        return self.update_by_id(group_id, group_name=new_name)

    def soft_delete_group(self, group_id: int) -> Optional[GroupRecord]:
        """软删除分组（设置删除时间）"""
        return self.update_by_id(group_id, delete_time=datetime.now())

    def restore_group(self, group_id: int) -> Optional[GroupRecord]:
        """恢复已删除的分组"""
        return self.update_by_id(group_id, delete_time=None)

    def hard_delete_group(self, group_id: int) -> bool:
        """硬删除分组（物理删除）"""
        return self.delete_by_id(group_id)

    def search_groups(self, keyword: str, page: int = 1, page_size: int = 20, 
                     include_deleted: bool = False) -> Tuple[List[GroupRecord], int]:
        """按关键词搜索分组"""
        with self.get_session() as session:
            query = session.query(self.table_class).filter(
                self.table_class.group_name.like(f'%{keyword}%')
            )
            
            if not include_deleted:
                query = query.filter(self.table_class.delete_time.is_(None))
            
            query = query.order_by(self.table_class.create_time.desc())
            
            total = query.count()
            offset = (page - 1) * page_size
            table_objs = query.offset(offset).limit(page_size).all()
            
            return [self._to_model(obj) for obj in table_objs], total

    def count_groups(self, include_deleted: bool = False) -> int:
        """统计分组数量"""
        with self.get_session() as session:
            query = session.query(self.table_class)
            if not include_deleted:
                query = query.filter(self.table_class.delete_time.is_(None))
            return query.count()

    def group_name_exists(self, group_name: str, exclude_id: Optional[int] = None, 
                         include_deleted: bool = False) -> bool:
        """检查分组名称是否已存在"""
        with self.get_session() as session:
            query = session.query(self.table_class).filter(
                self.table_class.group_name == group_name
            )
            
            if exclude_id:
                query = query.filter(self.table_class.id != exclude_id)
            
            if not include_deleted:
                query = query.filter(self.table_class.delete_time.is_(None))
            
            return query.first() is not None


# 创建全局实例
group_dao = GroupDao()