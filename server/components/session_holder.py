from cachetools import TTLCache
from server.dao.user_session_dao import user_session_dao as session_dao
import logging

ONE_DAY = 86400
log = logging.getLogger(__name__)


class SessionHolder:
    """
    会话管理器，使用TTLCache作为缓存层，SQLite作为持久化存储
    """

    cache: TTLCache = None

    def __init__(self, ttl_in_day: int = 1):
        self.cache = TTLCache(maxsize=999999, ttl=ONE_DAY * ttl_in_day)


    def get(self, session_token: str, default_value=None):
        """
        获取session值
        先从缓存查找，如果不存在则从SQLite查找
        """
        # 先检查缓存
        cache_value = self.cache.get(session_token)
        if cache_value is not None:
            return cache_value

        if session_dao:
            try:
                if session_dao.is_session_valid(session_token):
                    # 会话有效，将其添加到缓存中
                    self.cache[session_token] = 1  # 简单的存在标志
                    return 1
            except Exception as e:
                log.error(f"Error checking session in SQLite: {e}")
        
        return default_value

    def set(self, session_token: str, value, username: str = None):
        """
        设置session值
        同时更新缓存和SQLite
        """
        self.cache[session_token] = value

        if username and session_dao:
            try:
                session_dao.create_session(session_token, username)
                log.info(f"Session saved to SQLite for user: {username}")
            except Exception as e:
                log.error(f"Error saving session to SQLite: {e}")
    
    def remove(self, session_token: str):
        """
        删除session token
        同时从缓存和SQLite中删除
        """
        # 从缓存删除
        if session_token in self.cache:
            del self.cache[session_token]

        if session_dao:
            try:
                success = session_dao.delete_session(session_token)
                if success:
                    log.info(f"Session removed from SQLite: {session_token}")
                else:
                    log.warning(f"Session not found in SQLite for deletion: {session_token}")
            except Exception as e:
                log.error(f"Error removing session from SQLite: {e}")
    
    def cleanup_expired_sessions(self):
        """清理所有过期的会话"""
        if session_dao:
            try:
                deleted_count = session_dao.cleanup_expired_sessions()
                log.info(f"Cleaned up {deleted_count} expired sessions from SQLite")
                return deleted_count
            except Exception as e:
                log.error(f"Error cleaning up expired sessions: {e}")
                return 0
        return 0


session_holder = SessionHolder()
