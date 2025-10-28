"""
WebSocket连接管理器
负责管理所有WebSocket连接，提供推送消息的接口
"""

import json
import logging
import threading
from typing import List, Dict, Any, Callable, Optional
from fastapi import WebSocket
import asyncio
import requests

from server.config import config_manager

log = logging.getLogger(__name__)

rt_cfg = config_manager.get_server_runtime_config()

def send_post_request(url: str, body: dict, headers: dict):
    try:
        response = requests.post(url, json=body, headers=headers)

        if response.status_code < 400:
            log.info(f"webhook performing successfully, host: {url}")
        else:
            log.error(f"webhook failed to execute, host: {url}\ncode:{response.status_code}\n{response.text}")
    except requests.RequestException as e:
        log.error(f"webhook failed to execute, host: {url}\nerror:{e}")

class WebSocketHolder:
    """WebSocket连接管理器"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self._lock = threading.Lock()
        self._auth_handler: Optional[Callable[[WebSocket], bool]] = None
    
    def set_auth_handler(self, handler: Callable[[WebSocket], bool]):
        """设置认证处理器，由main.py中的认证逻辑设置"""
        self._auth_handler = handler
    
    async def connect(self, websocket: WebSocket, auth_handler: Optional[Callable[[WebSocket], bool]] = None) -> bool:
        """
        连接WebSocket客户端
        
        Args:
            websocket: WebSocket连接实例
            auth_handler: 可选的认证处理器，如果不提供则使用默认的
            
        Returns:
            bool: 连接是否成功
        """
        # 使用传入的认证处理器或默认的认证处理器
        handler = auth_handler or self._auth_handler
        
        if handler:
            # 如果有认证处理器，让认证处理器处理连接
            try:
                is_authenticated = await handler(websocket)
                if is_authenticated:
                    with self._lock:
                        self.active_connections.append(websocket)
                    log.info(f"WebSocket client connected: {websocket.client}")
                    return True
                else:
                    log.warning(f"WebSocket connection rejected - authentication failed: {websocket.client}")
                    return False
            except Exception as e:
                log.error(f"Error during WebSocket authentication: {e}")
                return False
        else:
            # 如果没有认证处理器，直接接受连接
            await websocket.accept()
            with self._lock:
                self.active_connections.append(websocket)
            log.info(f"WebSocket client connected (no auth): {websocket.client}")
            return True
    
    def disconnect(self, websocket: WebSocket):
        """断开WebSocket连接"""
        with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
        log.info(f"WebSocket client disconnected: {websocket.client}")
    
    async def broadcast(self, data: Dict[str, Any]) -> int:
        """
        向所有连接的客户端广播消息
        
        Args:
            data: 要广播的数据字典
            
        Returns:
            int: 成功发送的连接数
        """
        if not self.active_connections:
            return 0
            
        message = json.dumps(data, ensure_ascii=False)
        disconnected_clients = []
        successful_sends = 0
        
        # 创建当前连接的副本以避免并发修改
        with self._lock:
            connections_to_send = self.active_connections.copy()
        
        for connection in connections_to_send:
            try:
                await connection.send_text(message)
                successful_sends += 1

                if rt_cfg.webhook.enable:
                    if rt_cfg.webhook.host and len(rt_cfg.webhook.host) > 0:
                        send_post_request(rt_cfg.webhook.host, data, rt_cfg.webhook.headers)
            except Exception as e:
                log.warning(f"Could not send to WebSocket client {connection.client}: {e}. Marking for disconnect.")
                disconnected_clients.append(connection)
        
        # 清理断开的客户端
        if disconnected_clients:
            with self._lock:
                for client in disconnected_clients:
                    if client in self.active_connections:
                        self.active_connections.remove(client)
        
        return successful_sends
    
    async def send_to_client(self, websocket: WebSocket, data: Dict[str, Any]) -> bool:
        """
        向特定客户端发送消息
        
        Args:
            websocket: 目标WebSocket连接
            data: 要发送的数据字典
            
        Returns:
            bool: 发送是否成功
        """
        try:
            message = json.dumps(data)
            await websocket.send_text(message)
            return True
        except Exception as e:
            log.warning(f"Could not send to WebSocket client {websocket.client}: {e}")
            # 从连接列表中移除失败的连接
            self.disconnect(websocket)
            return False
    
    def get_connection_count(self) -> int:
        """获取当前连接数"""
        with self._lock:
            return len(self.active_connections)
    
    def get_connection_info(self) -> List[Dict[str, str]]:
        """获取所有连接的信息"""
        with self._lock:
            return [
                {
                    "client": str(connection.client) if connection.client else "unknown",
                    "state": str(connection.client_state) if hasattr(connection, 'client_state') else "unknown"
                }
                for connection in self.active_connections
            ]
    
    async def close_all_connections(self, code: int = 1000, reason: str = "Server shutdown"):
        """
        关闭所有WebSocket连接
        
        Args:
            code: 关闭代码
            reason: 关闭原因
        """
        with self._lock:
            connections_to_close = self.active_connections.copy()
            self.active_connections.clear()
        
        close_tasks = []
        for connection in connections_to_close:
            try:
                # 先发送关闭通知
                await connection.send_text(json.dumps({
                    "type": "server_shutdown", 
                    "message": reason
                }))
                # 然后关闭连接
                close_tasks.append(connection.close(code=code, reason=reason))
            except Exception as e:
                log.warning(f"Error closing WebSocket connection: {e}")
        
        # 等待所有连接关闭
        if close_tasks:
            await asyncio.gather(*close_tasks, return_exceptions=True)
        
        log.info(f"Closed {len(connections_to_close)} WebSocket connections")
    
    def clear_connections(self):
        """清空所有连接（不发送关闭消息）"""
        with self._lock:
            self.active_connections.clear()
        log.info("Cleared all WebSocket connections")


# 全局WebSocket连接管理器实例
websocket_holder = WebSocketHolder()