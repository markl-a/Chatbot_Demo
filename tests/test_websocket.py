"""
WebSocket 測試

測試 WebSocket 連接和消息處理。
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from medical_chatbot.websocket.connection_manager import (
    ConnectionManager,
    ConnectionState,
    WebSocketConnection,
)
from medical_chatbot.websocket.handlers import WebSocketHandler, MessageType


# ============================================================================
# ConnectionManager 測試
# ============================================================================


class TestConnectionManager:
    """連接管理器測試"""

    @pytest.fixture
    def manager(self):
        """創建連接管理器"""
        return ConnectionManager(
            heartbeat_interval=1.0,
            heartbeat_timeout=5.0,
            max_connections=100,
        )

    @pytest.fixture
    def mock_websocket(self):
        """創建模擬 WebSocket"""
        ws = AsyncMock()
        ws.accept = AsyncMock()
        ws.send_json = AsyncMock()
        ws.receive_json = AsyncMock()
        ws.close = AsyncMock()
        return ws

    @pytest.mark.asyncio
    async def test_connect(self, manager, mock_websocket):
        """測試連接建立"""
        connection = await manager.connect(
            websocket=mock_websocket,
            connection_id="test-conn-1",
            user_id="user-1",
        )

        assert connection is not None
        assert connection.connection_id == "test-conn-1"
        assert connection.user_id == "user-1"
        assert connection.state == ConnectionState.CONNECTED
        mock_websocket.accept.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect(self, manager, mock_websocket):
        """測試連接斷開"""
        await manager.connect(
            websocket=mock_websocket,
            connection_id="test-conn-1",
            user_id="user-1",
        )

        await manager.disconnect("test-conn-1")

        assert manager.get_connection("test-conn-1") is None
        mock_websocket.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_max_connections(self, manager, mock_websocket):
        """測試最大連接數限制"""
        # 設置較小的最大連接數
        manager.max_connections = 2

        # 建立兩個連接
        ws1 = AsyncMock()
        ws1.accept = AsyncMock()
        ws2 = AsyncMock()
        ws2.accept = AsyncMock()
        ws3 = AsyncMock()
        ws3.accept = AsyncMock()

        await manager.connect(websocket=ws1, connection_id="conn-1")
        await manager.connect(websocket=ws2, connection_id="conn-2")

        # 第三個連接應該被拒絕
        with pytest.raises(ConnectionRefusedError):
            await manager.connect(websocket=ws3, connection_id="conn-3")

    @pytest.mark.asyncio
    async def test_send_personal_message(self, manager, mock_websocket):
        """測試發送個人消息"""
        await manager.connect(
            websocket=mock_websocket,
            connection_id="test-conn-1",
        )

        await manager.send_personal(
            "test-conn-1",
            {"text": "Hello"},
            message_type="greeting",
        )

        mock_websocket.send_json.assert_called_once()
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["type"] == "greeting"
        assert call_args["data"]["text"] == "Hello"

    @pytest.mark.asyncio
    async def test_broadcast(self, manager):
        """測試廣播消息"""
        # 創建多個連接
        ws1 = AsyncMock()
        ws1.accept = AsyncMock()
        ws1.send_json = AsyncMock()
        ws2 = AsyncMock()
        ws2.accept = AsyncMock()
        ws2.send_json = AsyncMock()

        await manager.connect(websocket=ws1, connection_id="conn-1")
        await manager.connect(websocket=ws2, connection_id="conn-2")

        await manager.broadcast({"message": "Hello everyone"})

        ws1.send_json.assert_called_once()
        ws2.send_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcast_exclude(self, manager):
        """測試廣播排除"""
        ws1 = AsyncMock()
        ws1.accept = AsyncMock()
        ws1.send_json = AsyncMock()
        ws2 = AsyncMock()
        ws2.accept = AsyncMock()
        ws2.send_json = AsyncMock()

        await manager.connect(websocket=ws1, connection_id="conn-1")
        await manager.connect(websocket=ws2, connection_id="conn-2")

        await manager.broadcast(
            {"message": "Hello"},
            exclude={"conn-1"},
        )

        ws1.send_json.assert_not_called()
        ws2.send_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_room_join_leave(self, manager, mock_websocket):
        """測試房間加入和離開"""
        await manager.connect(
            websocket=mock_websocket,
            connection_id="test-conn-1",
        )

        await manager.join_room("test-conn-1", "room-1")

        connection = manager.get_connection("test-conn-1")
        assert "room-1" in connection.rooms

        connections = manager.get_room_connections("room-1")
        assert len(connections) == 1

        await manager.leave_room("test-conn-1", "room-1")

        connection = manager.get_connection("test-conn-1")
        assert "room-1" not in connection.rooms

    @pytest.mark.asyncio
    async def test_broadcast_to_room(self, manager):
        """測試房間廣播"""
        ws1 = AsyncMock()
        ws1.accept = AsyncMock()
        ws1.send_json = AsyncMock()
        ws2 = AsyncMock()
        ws2.accept = AsyncMock()
        ws2.send_json = AsyncMock()
        ws3 = AsyncMock()
        ws3.accept = AsyncMock()
        ws3.send_json = AsyncMock()

        await manager.connect(websocket=ws1, connection_id="conn-1")
        await manager.connect(websocket=ws2, connection_id="conn-2")
        await manager.connect(websocket=ws3, connection_id="conn-3")

        await manager.join_room("conn-1", "room-1")
        await manager.join_room("conn-2", "room-1")
        # conn-3 不在房間內

        await manager.broadcast_to_room("room-1", {"message": "Room message"})

        ws1.send_json.assert_called_once()
        ws2.send_json.assert_called_once()
        ws3.send_json.assert_not_called()

    @pytest.mark.asyncio
    async def test_user_connections(self, manager):
        """測試用戶連接管理"""
        ws1 = AsyncMock()
        ws1.accept = AsyncMock()
        ws2 = AsyncMock()
        ws2.accept = AsyncMock()

        await manager.connect(websocket=ws1, connection_id="conn-1", user_id="user-1")
        await manager.connect(websocket=ws2, connection_id="conn-2", user_id="user-1")

        connections = manager.get_user_connections("user-1")
        assert len(connections) == 2

    @pytest.mark.asyncio
    async def test_stats(self, manager, mock_websocket):
        """測試統計信息"""
        await manager.connect(
            websocket=mock_websocket,
            connection_id="test-conn-1",
        )

        stats = manager.get_stats()

        assert stats["active_connections"] == 1
        assert stats["total_connections"] == 1
        assert stats["max_connections"] == 100

    @pytest.mark.asyncio
    async def test_on_connect_callback(self, manager, mock_websocket):
        """測試連接回調"""
        callback_called = False
        connection_received = None

        async def on_connect(connection):
            nonlocal callback_called, connection_received
            callback_called = True
            connection_received = connection

        manager.on_connect(on_connect)

        await manager.connect(
            websocket=mock_websocket,
            connection_id="test-conn-1",
        )

        assert callback_called
        assert connection_received.connection_id == "test-conn-1"


# ============================================================================
# WebSocketHandler 測試
# ============================================================================


class TestWebSocketHandler:
    """消息處理器測試"""

    @pytest.fixture
    def manager(self):
        """創建連接管理器"""
        return ConnectionManager()

    @pytest.fixture
    def handler(self, manager):
        """創建消息處理器"""
        return WebSocketHandler(connection_manager=manager)

    @pytest.fixture
    def mock_connection(self):
        """創建模擬連接"""
        ws = AsyncMock()
        return WebSocketConnection(
            websocket=ws,
            connection_id="test-conn-1",
            user_id="user-1",
            state=ConnectionState.CONNECTED,
        )

    @pytest.mark.asyncio
    async def test_handle_ping(self, handler, mock_connection):
        """測試 ping 消息處理"""
        message = {
            "type": "ping",
            "data": {"timestamp": 12345},
        }

        response = await handler.handle_message(mock_connection, message)

        assert response["type"] == "pong"
        assert response["data"]["echo"] == 12345

    @pytest.mark.asyncio
    async def test_handle_chat(self, handler, mock_connection):
        """測試聊天消息處理（無生成器）"""
        message = {
            "type": "chat",
            "data": {"message": "你好"},
        }

        response = await handler.handle_message(mock_connection, message)

        assert response["type"] == "chat_response"
        assert "message" in response["data"]

    @pytest.mark.asyncio
    async def test_handle_conversation_start(self, handler, mock_connection):
        """測試開始對話"""
        message = {
            "type": "conversation_start",
            "data": {"system_prompt": "你是一位醫生"},
        }

        response = await handler.handle_message(mock_connection, message)

        assert response["type"] == "conversation_start"
        assert "conversation_id" in response["data"]

    @pytest.mark.asyncio
    async def test_handle_conversation_end(self, handler, mock_connection):
        """測試結束對話"""
        # 先開始對話
        start_message = {
            "type": "conversation_start",
            "data": {},
        }
        start_response = await handler.handle_message(mock_connection, start_message)
        conversation_id = start_response["data"]["conversation_id"]

        # 結束對話
        end_message = {
            "type": "conversation_end",
            "data": {"conversation_id": conversation_id},
        }

        response = await handler.handle_message(mock_connection, end_message)

        assert response["type"] == "conversation_end"

    @pytest.mark.asyncio
    async def test_handle_unknown_message(self, handler, mock_connection):
        """測試未知消息類型"""
        message = {
            "type": "unknown_type",
            "data": {},
        }

        response = await handler.handle_message(mock_connection, message)

        assert response["type"] == "error"

    @pytest.mark.asyncio
    async def test_conversation_history(self, handler, mock_connection):
        """測試對話歷史"""
        # 開始對話
        start_response = await handler.handle_message(
            mock_connection,
            {"type": "conversation_start", "data": {}},
        )
        conversation_id = start_response["data"]["conversation_id"]

        # 獲取歷史
        history_response = await handler.handle_message(
            mock_connection,
            {
                "type": "conversation_history",
                "data": {"conversation_id": conversation_id},
            },
        )

        assert history_response["type"] == "conversation_history"
        assert "history" in history_response["data"]

    def test_register_custom_handler(self, handler, mock_connection):
        """測試註冊自定義處理器"""
        custom_called = False

        async def custom_handler(connection, data):
            nonlocal custom_called
            custom_called = True
            return {"type": "custom_response", "data": {}}

        handler.register_handler("custom_type", custom_handler)

        # 驗證處理器已註冊
        assert "custom_type" in handler._handlers
