"""
WebSocket 連接管理器

管理 WebSocket 連接的生命週期、廣播和房間功能。
"""

import asyncio
import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

from fastapi import WebSocket, WebSocketDisconnect
from loguru import logger


class ConnectionState(Enum):
    """連接狀態"""
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"


@dataclass
class WebSocketConnection:
    """WebSocket 連接信息"""
    websocket: WebSocket
    connection_id: str
    user_id: Optional[str] = None
    rooms: Set[str] = field(default_factory=set)
    state: ConnectionState = ConnectionState.CONNECTING
    connected_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ConnectionManager:
    """
    WebSocket 連接管理器

    支援：
    - 連接生命週期管理
    - 房間/群組功能
    - 廣播消息
    - 心跳檢測
    - 連接統計
    """

    def __init__(
        self,
        heartbeat_interval: float = 30.0,
        heartbeat_timeout: float = 60.0,
        max_connections: int = 1000,
        max_message_size: int = 65536,
    ):
        """
        初始化連接管理器

        Args:
            heartbeat_interval: 心跳間隔（秒）
            heartbeat_timeout: 心跳超時（秒）
            max_connections: 最大連接數
            max_message_size: 最大消息大小（字節）
        """
        self.heartbeat_interval = heartbeat_interval
        self.heartbeat_timeout = heartbeat_timeout
        self.max_connections = max_connections
        self.max_message_size = max_message_size

        # 連接存儲
        self._connections: Dict[str, WebSocketConnection] = {}
        self._user_connections: Dict[str, Set[str]] = {}  # user_id -> connection_ids
        self._rooms: Dict[str, Set[str]] = {}  # room_name -> connection_ids

        # 統計
        self._total_connections = 0
        self._total_messages_sent = 0
        self._total_messages_received = 0

        # 心跳任務
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._running = False

        # 事件回調
        self._on_connect_callbacks: List[Callable] = []
        self._on_disconnect_callbacks: List[Callable] = []
        self._on_message_callbacks: List[Callable] = []

        logger.info(f"WebSocket 連接管理器初始化完成 (最大連接數: {max_connections})")

    # ========================================================================
    # 連接管理
    # ========================================================================

    async def connect(
        self,
        websocket: WebSocket,
        connection_id: str,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> WebSocketConnection:
        """
        建立 WebSocket 連接

        Args:
            websocket: WebSocket 實例
            connection_id: 連接 ID
            user_id: 用戶 ID（可選）
            metadata: 元數據（可選）

        Returns:
            WebSocketConnection 實例

        Raises:
            ConnectionRefusedError: 超過最大連接數
        """
        # 檢查連接數限制
        if len(self._connections) >= self.max_connections:
            logger.warning(f"連接被拒絕：超過最大連接數 {self.max_connections}")
            raise ConnectionRefusedError(f"超過最大連接數 {self.max_connections}")

        # 接受連接
        await websocket.accept()

        # 創建連接對象
        connection = WebSocketConnection(
            websocket=websocket,
            connection_id=connection_id,
            user_id=user_id,
            state=ConnectionState.CONNECTED,
            metadata=metadata or {},
        )

        # 存儲連接
        self._connections[connection_id] = connection
        self._total_connections += 1

        # 建立用戶映射
        if user_id:
            if user_id not in self._user_connections:
                self._user_connections[user_id] = set()
            self._user_connections[user_id].add(connection_id)

        # 觸發連接回調
        for callback in self._on_connect_callbacks:
            try:
                await callback(connection)
            except Exception as e:
                logger.error(f"連接回調執行失敗: {e}")

        logger.info(f"WebSocket 連接建立: {connection_id} (用戶: {user_id})")
        return connection

    async def disconnect(self, connection_id: str, code: int = 1000, reason: str = "正常關閉"):
        """
        斷開 WebSocket 連接

        Args:
            connection_id: 連接 ID
            code: 關閉代碼
            reason: 關閉原因
        """
        if connection_id not in self._connections:
            return

        connection = self._connections[connection_id]
        connection.state = ConnectionState.DISCONNECTING

        try:
            await connection.websocket.close(code=code, reason=reason)
        except Exception as e:
            logger.debug(f"關閉連接時發生錯誤: {e}")

        # 清理連接
        await self._cleanup_connection(connection_id)

        # 觸發斷開回調
        for callback in self._on_disconnect_callbacks:
            try:
                await callback(connection)
            except Exception as e:
                logger.error(f"斷開回調執行失敗: {e}")

        logger.info(f"WebSocket 連接斷開: {connection_id} (原因: {reason})")

    async def _cleanup_connection(self, connection_id: str):
        """清理連接資源"""
        if connection_id not in self._connections:
            return

        connection = self._connections[connection_id]
        connection.state = ConnectionState.DISCONNECTED

        # 從用戶映射中移除
        if connection.user_id and connection.user_id in self._user_connections:
            self._user_connections[connection.user_id].discard(connection_id)
            if not self._user_connections[connection.user_id]:
                del self._user_connections[connection.user_id]

        # 從所有房間中移除
        for room in list(connection.rooms):
            await self.leave_room(connection_id, room)

        # 刪除連接
        del self._connections[connection_id]

    def get_connection(self, connection_id: str) -> Optional[WebSocketConnection]:
        """獲取連接信息"""
        return self._connections.get(connection_id)

    def get_user_connections(self, user_id: str) -> List[WebSocketConnection]:
        """獲取用戶的所有連接"""
        connection_ids = self._user_connections.get(user_id, set())
        return [self._connections[cid] for cid in connection_ids if cid in self._connections]

    # ========================================================================
    # 房間管理
    # ========================================================================

    async def join_room(self, connection_id: str, room: str):
        """
        加入房間

        Args:
            connection_id: 連接 ID
            room: 房間名稱
        """
        if connection_id not in self._connections:
            return

        connection = self._connections[connection_id]
        connection.rooms.add(room)

        if room not in self._rooms:
            self._rooms[room] = set()
        self._rooms[room].add(connection_id)

        logger.debug(f"連接 {connection_id} 加入房間 {room}")

    async def leave_room(self, connection_id: str, room: str):
        """
        離開房間

        Args:
            connection_id: 連接 ID
            room: 房間名稱
        """
        if connection_id not in self._connections:
            return

        connection = self._connections[connection_id]
        connection.rooms.discard(room)

        if room in self._rooms:
            self._rooms[room].discard(connection_id)
            if not self._rooms[room]:
                del self._rooms[room]

        logger.debug(f"連接 {connection_id} 離開房間 {room}")

    def get_room_connections(self, room: str) -> List[WebSocketConnection]:
        """獲取房間內的所有連接"""
        connection_ids = self._rooms.get(room, set())
        return [self._connections[cid] for cid in connection_ids if cid in self._connections]

    # ========================================================================
    # 消息發送
    # ========================================================================

    async def send_personal(
        self,
        connection_id: str,
        message: Dict[str, Any],
        message_type: str = "message",
    ):
        """
        發送個人消息

        Args:
            connection_id: 連接 ID
            message: 消息內容
            message_type: 消息類型
        """
        if connection_id not in self._connections:
            return

        connection = self._connections[connection_id]
        await self._send_message(connection, message, message_type)

    async def send_to_user(
        self,
        user_id: str,
        message: Dict[str, Any],
        message_type: str = "message",
    ):
        """
        發送消息給用戶（所有連接）

        Args:
            user_id: 用戶 ID
            message: 消息內容
            message_type: 消息類型
        """
        connections = self.get_user_connections(user_id)
        for connection in connections:
            await self._send_message(connection, message, message_type)

    async def broadcast(
        self,
        message: Dict[str, Any],
        message_type: str = "broadcast",
        exclude: Optional[Set[str]] = None,
    ):
        """
        廣播消息給所有連接

        Args:
            message: 消息內容
            message_type: 消息類型
            exclude: 要排除的連接 ID 集合
        """
        exclude = exclude or set()
        tasks = []

        for connection_id, connection in self._connections.items():
            if connection_id not in exclude:
                tasks.append(self._send_message(connection, message, message_type))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def broadcast_to_room(
        self,
        room: str,
        message: Dict[str, Any],
        message_type: str = "room_message",
        exclude: Optional[Set[str]] = None,
    ):
        """
        廣播消息給房間內的所有連接

        Args:
            room: 房間名稱
            message: 消息內容
            message_type: 消息類型
            exclude: 要排除的連接 ID 集合
        """
        exclude = exclude or set()
        connections = self.get_room_connections(room)
        tasks = []

        for connection in connections:
            if connection.connection_id not in exclude:
                tasks.append(self._send_message(connection, message, message_type))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _send_message(
        self,
        connection: WebSocketConnection,
        message: Dict[str, Any],
        message_type: str,
    ):
        """發送消息的內部方法"""
        if connection.state != ConnectionState.CONNECTED:
            return

        try:
            payload = {
                "type": message_type,
                "data": message,
                "timestamp": time.time(),
            }
            await connection.websocket.send_json(payload)
            self._total_messages_sent += 1
            connection.last_activity = time.time()
        except Exception as e:
            logger.error(f"發送消息失敗 ({connection.connection_id}): {e}")
            # 標記連接為斷開
            await self._cleanup_connection(connection.connection_id)

    # ========================================================================
    # 消息接收
    # ========================================================================

    async def receive_message(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """
        接收消息

        Args:
            connection_id: 連接 ID

        Returns:
            接收到的消息，或 None（如果連接不存在）
        """
        if connection_id not in self._connections:
            return None

        connection = self._connections[connection_id]

        try:
            data = await connection.websocket.receive_json()
            self._total_messages_received += 1
            connection.last_activity = time.time()

            # 觸發消息回調
            for callback in self._on_message_callbacks:
                try:
                    await callback(connection, data)
                except Exception as e:
                    logger.error(f"消息回調執行失敗: {e}")

            return data
        except WebSocketDisconnect:
            await self._cleanup_connection(connection_id)
            return None
        except Exception as e:
            logger.error(f"接收消息失敗 ({connection_id}): {e}")
            return None

    # ========================================================================
    # 心跳管理
    # ========================================================================

    async def start_heartbeat(self):
        """啟動心跳檢測"""
        if self._running:
            return

        self._running = True
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        logger.info("心跳檢測已啟動")

    async def stop_heartbeat(self):
        """停止心跳檢測"""
        self._running = False
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
        logger.info("心跳檢測已停止")

    async def _heartbeat_loop(self):
        """心跳循環"""
        while self._running:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                await self._check_connections()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"心跳檢測錯誤: {e}")

    async def _check_connections(self):
        """檢查連接健康狀態"""
        current_time = time.time()
        stale_connections = []

        for connection_id, connection in self._connections.items():
            # 檢查是否超時
            if current_time - connection.last_activity > self.heartbeat_timeout:
                stale_connections.append(connection_id)
            else:
                # 發送心跳
                try:
                    await self._send_message(
                        connection,
                        {"ping": current_time},
                        "heartbeat",
                    )
                except Exception:
                    stale_connections.append(connection_id)

        # 清理過期連接
        for connection_id in stale_connections:
            logger.warning(f"連接超時，正在斷開: {connection_id}")
            await self.disconnect(connection_id, code=1001, reason="心跳超時")

    # ========================================================================
    # 事件回調
    # ========================================================================

    def on_connect(self, callback: Callable):
        """註冊連接事件回調"""
        self._on_connect_callbacks.append(callback)
        return callback

    def on_disconnect(self, callback: Callable):
        """註冊斷開事件回調"""
        self._on_disconnect_callbacks.append(callback)
        return callback

    def on_message(self, callback: Callable):
        """註冊消息事件回調"""
        self._on_message_callbacks.append(callback)
        return callback

    # ========================================================================
    # 統計和監控
    # ========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """獲取連接統計信息"""
        return {
            "active_connections": len(self._connections),
            "total_connections": self._total_connections,
            "total_messages_sent": self._total_messages_sent,
            "total_messages_received": self._total_messages_received,
            "active_rooms": len(self._rooms),
            "active_users": len(self._user_connections),
            "max_connections": self.max_connections,
        }

    def get_connection_details(self) -> List[Dict[str, Any]]:
        """獲取所有連接的詳細信息"""
        return [
            {
                "connection_id": conn.connection_id,
                "user_id": conn.user_id,
                "state": conn.state.value,
                "rooms": list(conn.rooms),
                "connected_at": conn.connected_at,
                "last_activity": conn.last_activity,
            }
            for conn in self._connections.values()
        ]

    # ========================================================================
    # 上下文管理
    # ========================================================================

    async def __aenter__(self):
        """進入上下文時啟動心跳"""
        await self.start_heartbeat()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """退出上下文時停止心跳並清理連接"""
        await self.stop_heartbeat()

        # 關閉所有連接
        for connection_id in list(self._connections.keys()):
            await self.disconnect(connection_id, code=1001, reason="服務關閉")
