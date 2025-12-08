"""
WebSocket 消息處理器

處理不同類型的 WebSocket 消息。
"""

import asyncio
import time
import uuid
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from loguru import logger

from medical_chatbot.websocket.connection_manager import ConnectionManager, WebSocketConnection


class MessageType(Enum):
    """消息類型"""
    # 系統消息
    PING = "ping"
    PONG = "pong"
    ERROR = "error"

    # 聊天消息
    CHAT = "chat"
    CHAT_RESPONSE = "chat_response"
    CHAT_STREAM = "chat_stream"
    CHAT_STREAM_END = "chat_stream_end"

    # 對話管理
    CONVERSATION_START = "conversation_start"
    CONVERSATION_END = "conversation_end"
    CONVERSATION_HISTORY = "conversation_history"

    # 房間消息
    JOIN_ROOM = "join_room"
    LEAVE_ROOM = "leave_room"
    ROOM_MESSAGE = "room_message"

    # 狀態更新
    STATUS_UPDATE = "status_update"
    TYPING = "typing"

    # 系統通知
    NOTIFICATION = "notification"
    SYSTEM = "system"


class WebSocketHandler:
    """
    WebSocket 消息處理器

    支援：
    - 消息路由
    - 聊天處理
    - 串流回覆
    - 對話歷史管理
    """

    def __init__(
        self,
        connection_manager: ConnectionManager,
        generator: Optional[Any] = None,
        safety_filter: Optional[Any] = None,
    ):
        """
        初始化處理器

        Args:
            connection_manager: 連接管理器
            generator: 文本生成器（可選）
            safety_filter: 安全過濾器（可選）
        """
        self.manager = connection_manager
        self.generator = generator
        self.safety_filter = safety_filter

        # 對話歷史存儲
        self._conversations: Dict[str, List[Dict[str, str]]] = {}

        # 消息處理器映射
        self._handlers: Dict[str, Callable] = {}
        self._register_default_handlers()

        logger.info("WebSocket 消息處理器初始化完成")

    def _register_default_handlers(self):
        """註冊默認消息處理器"""
        self.register_handler(MessageType.PING.value, self._handle_ping)
        self.register_handler(MessageType.CHAT.value, self._handle_chat)
        self.register_handler(MessageType.CHAT_STREAM.value, self._handle_chat_stream)
        self.register_handler(MessageType.JOIN_ROOM.value, self._handle_join_room)
        self.register_handler(MessageType.LEAVE_ROOM.value, self._handle_leave_room)
        self.register_handler(MessageType.CONVERSATION_START.value, self._handle_conversation_start)
        self.register_handler(MessageType.CONVERSATION_END.value, self._handle_conversation_end)
        self.register_handler(MessageType.CONVERSATION_HISTORY.value, self._handle_conversation_history)
        self.register_handler(MessageType.TYPING.value, self._handle_typing)

    def register_handler(self, message_type: str, handler: Callable):
        """
        註冊消息處理器

        Args:
            message_type: 消息類型
            handler: 處理函數
        """
        self._handlers[message_type] = handler
        logger.debug(f"註冊消息處理器: {message_type}")

    async def handle_message(
        self,
        connection: WebSocketConnection,
        message: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        處理收到的消息

        Args:
            connection: WebSocket 連接
            message: 消息內容

        Returns:
            回覆消息（可選）
        """
        message_type = message.get("type", "unknown")
        data = message.get("data", {})

        logger.debug(f"處理消息: {message_type} (連接: {connection.connection_id})")

        handler = self._handlers.get(message_type)
        if handler:
            try:
                return await handler(connection, data)
            except Exception as e:
                logger.error(f"消息處理失敗 ({message_type}): {e}")
                return await self._create_error_response(str(e))
        else:
            logger.warning(f"未知消息類型: {message_type}")
            return await self._create_error_response(f"未知消息類型: {message_type}")

    # ========================================================================
    # 系統消息處理
    # ========================================================================

    async def _handle_ping(
        self,
        connection: WebSocketConnection,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """處理 ping 消息"""
        return {
            "type": MessageType.PONG.value,
            "data": {
                "timestamp": time.time(),
                "echo": data.get("timestamp"),
            },
        }

    async def _create_error_response(self, error: str) -> Dict[str, Any]:
        """創建錯誤回覆"""
        return {
            "type": MessageType.ERROR.value,
            "data": {
                "error": error,
                "timestamp": time.time(),
            },
        }

    # ========================================================================
    # 聊天消息處理
    # ========================================================================

    async def _handle_chat(
        self,
        connection: WebSocketConnection,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """處理聊天消息（非串流）"""
        message = data.get("message", "")
        conversation_id = data.get("conversation_id", connection.connection_id)

        if not message:
            return await self._create_error_response("消息不能為空")

        # 安全過濾
        sanitized_message = message
        is_emergency = False
        if self.safety_filter:
            sanitized_message = self.safety_filter.sanitize_input(message)

        # 獲取對話歷史
        history = self._conversations.get(conversation_id, [])

        # 添加用戶消息到歷史
        history.append({"role": "user", "content": sanitized_message})

        # 生成回覆
        response_text = "抱歉，生成器未初始化。"
        if self.generator:
            try:
                response_text = self.generator.chat(messages=history)
            except Exception as e:
                logger.error(f"生成回覆失敗: {e}")
                response_text = f"生成回覆時發生錯誤: {str(e)}"

        # 安全過濾回覆
        if self.safety_filter:
            response_text, is_emergency = self.safety_filter.filter_response(
                sanitized_message, response_text
            )

        # 添加助手回覆到歷史
        history.append({"role": "assistant", "content": response_text})
        self._conversations[conversation_id] = history

        return {
            "type": MessageType.CHAT_RESPONSE.value,
            "data": {
                "message": response_text,
                "conversation_id": conversation_id,
                "is_emergency": is_emergency,
                "timestamp": time.time(),
            },
        }

    async def _handle_chat_stream(
        self,
        connection: WebSocketConnection,
        data: Dict[str, Any],
    ):
        """處理串流聊天消息"""
        message = data.get("message", "")
        conversation_id = data.get("conversation_id", connection.connection_id)

        if not message:
            await self.manager.send_personal(
                connection.connection_id,
                await self._create_error_response("消息不能為空"),
            )
            return None

        # 安全過濾
        sanitized_message = message
        if self.safety_filter:
            sanitized_message = self.safety_filter.sanitize_input(message)

        # 獲取對話歷史
        history = self._conversations.get(conversation_id, [])
        history.append({"role": "user", "content": sanitized_message})

        # 串流生成回覆
        full_response = ""

        if self.generator and hasattr(self.generator, "generate_stream"):
            try:
                async for token in self.generator.generate_stream(
                    user_input=sanitized_message,
                    conversation_history=history[:-1],  # 不包含當前消息
                ):
                    full_response += token
                    await self.manager.send_personal(
                        connection.connection_id,
                        {
                            "token": token,
                            "conversation_id": conversation_id,
                        },
                        message_type=MessageType.CHAT_STREAM.value,
                    )
                    await asyncio.sleep(0)  # 讓出控制權
            except Exception as e:
                logger.error(f"串流生成失敗: {e}")
                full_response = f"生成回覆時發生錯誤: {str(e)}"
        elif self.generator:
            # 模擬串流（逐字發送）
            try:
                full_response = self.generator.chat(messages=history)
                for char in full_response:
                    await self.manager.send_personal(
                        connection.connection_id,
                        {
                            "token": char,
                            "conversation_id": conversation_id,
                        },
                        message_type=MessageType.CHAT_STREAM.value,
                    )
                    await asyncio.sleep(0.02)
            except Exception as e:
                logger.error(f"生成失敗: {e}")
                full_response = f"生成回覆時發生錯誤: {str(e)}"
        else:
            full_response = "抱歉，生成器未初始化。"
            await self.manager.send_personal(
                connection.connection_id,
                {
                    "token": full_response,
                    "conversation_id": conversation_id,
                },
                message_type=MessageType.CHAT_STREAM.value,
            )

        # 安全過濾完整回覆
        is_emergency = False
        if self.safety_filter:
            full_response, is_emergency = self.safety_filter.filter_response(
                sanitized_message, full_response
            )

        # 保存到歷史
        history.append({"role": "assistant", "content": full_response})
        self._conversations[conversation_id] = history

        # 發送結束標記
        await self.manager.send_personal(
            connection.connection_id,
            {
                "message": full_response,
                "conversation_id": conversation_id,
                "is_emergency": is_emergency,
                "timestamp": time.time(),
            },
            message_type=MessageType.CHAT_STREAM_END.value,
        )

        return None  # 已經通過 send_personal 發送回覆

    # ========================================================================
    # 房間管理
    # ========================================================================

    async def _handle_join_room(
        self,
        connection: WebSocketConnection,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """處理加入房間請求"""
        room = data.get("room", "")

        if not room:
            return await self._create_error_response("房間名稱不能為空")

        await self.manager.join_room(connection.connection_id, room)

        # 通知房間內其他成員
        await self.manager.broadcast_to_room(
            room,
            {
                "user_id": connection.user_id,
                "connection_id": connection.connection_id,
                "action": "joined",
            },
            message_type=MessageType.NOTIFICATION.value,
            exclude={connection.connection_id},
        )

        return {
            "type": MessageType.SYSTEM.value,
            "data": {
                "message": f"已加入房間: {room}",
                "room": room,
                "timestamp": time.time(),
            },
        }

    async def _handle_leave_room(
        self,
        connection: WebSocketConnection,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """處理離開房間請求"""
        room = data.get("room", "")

        if not room:
            return await self._create_error_response("房間名稱不能為空")

        # 通知房間內其他成員
        await self.manager.broadcast_to_room(
            room,
            {
                "user_id": connection.user_id,
                "connection_id": connection.connection_id,
                "action": "left",
            },
            message_type=MessageType.NOTIFICATION.value,
            exclude={connection.connection_id},
        )

        await self.manager.leave_room(connection.connection_id, room)

        return {
            "type": MessageType.SYSTEM.value,
            "data": {
                "message": f"已離開房間: {room}",
                "room": room,
                "timestamp": time.time(),
            },
        }

    # ========================================================================
    # 對話管理
    # ========================================================================

    async def _handle_conversation_start(
        self,
        connection: WebSocketConnection,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """處理開始對話請求"""
        conversation_id = data.get("conversation_id") or str(uuid.uuid4())
        system_prompt = data.get("system_prompt")

        # 初始化對話歷史
        history = []
        if system_prompt:
            history.append({"role": "system", "content": system_prompt})

        self._conversations[conversation_id] = history

        return {
            "type": MessageType.CONVERSATION_START.value,
            "data": {
                "conversation_id": conversation_id,
                "message": "對話已開始",
                "timestamp": time.time(),
            },
        }

    async def _handle_conversation_end(
        self,
        connection: WebSocketConnection,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """處理結束對話請求"""
        conversation_id = data.get("conversation_id", connection.connection_id)

        # 清除對話歷史
        if conversation_id in self._conversations:
            del self._conversations[conversation_id]

        return {
            "type": MessageType.CONVERSATION_END.value,
            "data": {
                "conversation_id": conversation_id,
                "message": "對話已結束",
                "timestamp": time.time(),
            },
        }

    async def _handle_conversation_history(
        self,
        connection: WebSocketConnection,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """處理獲取對話歷史請求"""
        conversation_id = data.get("conversation_id", connection.connection_id)

        history = self._conversations.get(conversation_id, [])

        return {
            "type": MessageType.CONVERSATION_HISTORY.value,
            "data": {
                "conversation_id": conversation_id,
                "history": history,
                "message_count": len(history),
                "timestamp": time.time(),
            },
        }

    # ========================================================================
    # 狀態更新
    # ========================================================================

    async def _handle_typing(
        self,
        connection: WebSocketConnection,
        data: Dict[str, Any],
    ) -> None:
        """處理輸入狀態更新"""
        room = data.get("room")
        is_typing = data.get("is_typing", False)

        notification = {
            "user_id": connection.user_id,
            "connection_id": connection.connection_id,
            "is_typing": is_typing,
            "timestamp": time.time(),
        }

        if room:
            # 廣播到房間
            await self.manager.broadcast_to_room(
                room,
                notification,
                message_type=MessageType.TYPING.value,
                exclude={connection.connection_id},
            )

        return None  # 不需要回覆

    # ========================================================================
    # 對話歷史管理
    # ========================================================================

    def get_conversation(self, conversation_id: str) -> List[Dict[str, str]]:
        """獲取對話歷史"""
        return self._conversations.get(conversation_id, [])

    def clear_conversation(self, conversation_id: str):
        """清除對話歷史"""
        if conversation_id in self._conversations:
            del self._conversations[conversation_id]

    def clear_all_conversations(self):
        """清除所有對話歷史"""
        self._conversations.clear()
