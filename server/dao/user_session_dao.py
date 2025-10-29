# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy import Column, String, DateTime, Index
from server.dao.base_dao import BaseDao, Base
from server.models import UserSessionRecord


class UserSessionTable(Base):
    """用户会话表"""
    __tablename__ = 'user_sessions'
    
    session_token = Column(String(50), primary_key=True, comment='会话令牌')
    username = Column(String(50), nullable=False, comment='用户名')
    login_time = Column(DateTime, nullable=False, comment='登录时间')
    expire_time = Column(DateTime, nullable=False, comment='过期时间')
    
    # 创建索引提高查询性能
    __table_args__ = (
        Index(f'idx_{__tablename__}_username', 'username'),
        Index(f'idx_{__tablename__}_expire_time', 'expire_time'),
    )


class UserSessionDao(BaseDao[UserSessionRecord]):
    """用户会话数据访问对象"""
    
    def __init__(self):
        super().__init__(UserSessionTable, UserSessionRecord)
    
    def create_session(self, session_token: str, username: str, expire_hours: int = 24) -> UserSessionRecord:
        """创建新的用户会话"""
        login_time = datetime.now()
        expire_time = login_time + timedelta(hours=expire_hours)
        
        # 先删除该用户的所有旧会话（可选，取决于是否允许多会话）
        # with self.get_session() as session:
        #     session.query(UserSessionTable).filter(
        #         UserSessionTable.username == username
        #     ).delete()
        
        return self.create(
            session_token=session_token,
            username=username,
            login_time=login_time,
            expire_time=expire_time
        )
    
    def get_session_by_token(self, session_token: str) -> Optional[UserSessionRecord]:
        filters = {"session_token": session_token}
        records, total = self.find_by_filters(page=1, page_size=1, order_by='login_time', desc_order=True, **filters)
        if records and len(records) > 0:
            return records[0]
        return None


    
    def delete_session(self, session_token: str) -> bool:
        """删除指定会话"""
        with self.get_session() as session:
            deleted_count = session.query(UserSessionTable).filter(
                UserSessionTable.session_token == session_token
            ).delete()
            return deleted_count > 0
    
    def delete_user_sessions(self, username: str) -> int:
        """删除用户的所有会话"""
        with self.get_session() as session:
            return session.query(UserSessionTable).filter(
                UserSessionTable.username == username
            ).delete()

    def is_session_valid(self, session_token: str) -> bool:
        filters = {"session_token": session_token}
        records, total = self.find_by_filters(page=1, page_size=1, order_by='login_time', desc_order=True, **filters)
        if records and len(records) > 0:
            record = records[0]
            return not record.is_expired()
        return False

    def cleanup_expired_sessions(self) -> int:
        """清理所有过期的会话"""
        with self.get_session() as session:
            now = datetime.now()
            deleted_count = session.query(UserSessionTable).filter(
                UserSessionTable.expire_time < now
            ).delete()
            return deleted_count


# 创建全局实例
user_session_dao = UserSessionDao()
