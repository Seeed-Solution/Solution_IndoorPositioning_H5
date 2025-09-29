# -*- coding: utf-8 -*-
import os
from contextlib import contextmanager
from typing import List, Optional, TypeVar, Generic, Type, Any, Dict
from datetime import datetime
from sqlalchemy import create_engine, and_, desc
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.orm import declarative_base

T = TypeVar('T')  # Python model type
S = TypeVar('S')  # SQLAlchemy table type

Base = declarative_base()

"""初始化数据库连接和目录"""
db_dir = "db"
if not os.path.exists(db_dir):
    os.makedirs(db_dir)
_engine = create_engine("sqlite:///db/app.db", echo=False)
_session_factory = sessionmaker(bind=_engine)


class BaseDao(Generic[T]):
    _initialized = False
    
    def __init__(self, table_class: Type[S], model_class: Type[T]):
        self.table_class = table_class
        self.model_class = model_class
        
        # 创建表结构
        if not self._initialized:
            self._create_tables()
            self._initialized = True
    
    def _create_tables(self):
        Base.metadata.create_all(_engine)
    
    def _to_model(self, table_obj: S) -> T:
        """将SQLAlchemy对象转换为Python模型对象"""
        if table_obj is None:
            return None
        
        # 获取所有字段值
        data = {}
        for column in self.table_class.__table__.columns:
            data[column.name] = getattr(table_obj, column.name)
        
        # 使用from_dict方法创建模型对象（如果有的话）
        if hasattr(self.model_class, 'from_dict'):
            return self.model_class.from_dict(data)
        else:
            return self.model_class(**data)
    
    @contextmanager
    def get_session(self):
        """获取数据库会话的上下文管理器"""
        session = _session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def create(self, **kwargs) -> T:
        """创建单条记录"""
        with self.get_session() as session:
            instance = self.table_class(**kwargs)
            session.add(instance)
            session.flush()
            session.refresh(instance)
            return self._to_model(instance)

    def createWithUnique(self, condition: dict, **kwargs):
        with self.get_session() as session:
            session.begin()
            query_obj = session.query(self.table_class)
            filter_obj = {}
            for key, value in condition.items():
                filter_obj = query_obj.filter(getattr(self.table_class, key) == value)
            table_obj = filter_obj.first()
            if table_obj is not None:
                return None
            instance = self.table_class(**kwargs)
            session.add(instance)
            session.flush()
            session.refresh(instance)
            return self._to_model(instance)

    
    def get_by_id(self, record_id: int) -> Optional[T]:
        """根据ID获取单条记录"""
        with self.get_session() as session:
            table_obj = session.query(self.table_class).filter(
                self.table_class.id == record_id
            ).first()
            return self._to_model(table_obj)

    def get_by_dev_eui(self, dev_eui: str) -> Optional[T]:
        """根据ID获取单条记录"""
        with self.get_session() as session:
            table_obj = session.query(self.table_class).filter(
                self.table_class.dev_eui == dev_eui
            ).first()
            return self._to_model(table_obj)
    
    def get_all(self, limit: Optional[int] = None, offset: int = 0) -> List[T]:
        """获取所有记录"""
        with self.get_session() as session:
            query = session.query(self.table_class).offset(offset)
            if limit:
                query = query.limit(limit)
            table_objs = query.all()
            return [self._to_model(obj) for obj in table_objs]
    
    def update_by_dev_eui(self, dev_eui: str, **kwargs) -> Optional[T]:
        """根据dev_eui更新记录"""
        with self.get_session() as session:
            instance = session.query(self.table_class).filter(
                self.table_class.dev_eui == dev_eui
            ).first()
            if instance:
                for key, value in kwargs.items():
                    if hasattr(instance, key):
                        setattr(instance, key, value)
                session.flush()
                session.refresh(instance)
                return self._to_model(instance)
            return None

    def update_by_id(self, id: int, **kwargs) -> Optional[T]:
        """根据ID更新记录"""
        with self.get_session() as session:
            instance = session.query(self.table_class).filter(
                self.table_class.id == id
            ).first()
            if instance:
                for key, value in kwargs.items():
                    if hasattr(instance, key):
                        setattr(instance, key, value)
                session.flush()
                session.refresh(instance)
                return self._to_model(instance)
            return None
    
    def delete_by_id(self, record_id: int) -> bool:
        """根据ID删除记录"""
        with self.get_session() as session:
            deleted_count = session.query(self.table_class).filter(
                self.table_class.id == record_id
            ).delete()
            return deleted_count > 0
    
    def delete_by_ids(self, record_ids: List[int]) -> int:
        """根据ID列表批量删除记录"""
        if not record_ids:
            return 0
        
        with self.get_session() as session:
            return session.query(self.table_class).filter(
                self.table_class.id.in_(record_ids)
            ).delete(synchronize_session=False)
    
    def count(self, **filters) -> int:
        """统计记录数"""
        with self.get_session() as session:
            query = session.query(self.table_class)
            for key, value in filters.items():
                if hasattr(self.table_class, key):
                    query = query.filter(getattr(self.table_class, key) == value)
            return query.count()
    
    def find_by_filters(self, page: int = 1, page_size: int = 20, 
                       order_by: Optional[str] = None, desc_order: bool = True,
                       **filters) -> tuple[List[T], int]:
        """根据条件分页查询"""
        with self.get_session() as session:
            query = session.query(self.table_class)
            
            # 添加过滤条件
            for key, value in filters.items():
                if hasattr(self.table_class, key):
                    if value is None:
                        query = query.filter(getattr(self.table_class, key).is_(None))
                    else:
                        query = query.filter(getattr(self.table_class, key) == value)
            
            # 排序
            if order_by and hasattr(self.table_class, order_by):
                order_column = getattr(self.table_class, order_by)
                if desc_order:
                    query = query.order_by(desc(order_column))
                else:
                    query = query.order_by(order_column)
            
            total = query.count()
            offset = (page - 1) * page_size
            table_objs = query.offset(offset).limit(page_size).all()
            
            return [self._to_model(obj) for obj in table_objs], total
