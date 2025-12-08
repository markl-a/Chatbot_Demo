"""
WebSocket FastAPI 路由

提供 WebSocket 端點的 FastAPI 整合。
"""

import uuid
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect, status
from loguru import logger

from medical_chatbot.websocket.connection_manager import ConnectionManager
from medical_chatbot.websocket.handlers import WebSocketHandler


def create_websocket_router(
    connection_manager: Optional[ConnectionManager] = None,
    handler: Optional[WebSocketHandler] = None,
    prefix: str = "/ws",
    tags: list = None,
) -> APIRouter:
    """
    創建 WebSocket 路由

    Args:
        connection_manager: 連接管理器（可選，將自動創建）
        handler: 消息處理器（可選，將自動創建）
        prefix: 路由前綴
        tags: API 標籤

    Returns:
        FastAPI APIRouter
    """
    router = APIRouter(prefix=prefix, tags=tags or ["WebSocket"])

    # 創建默認管理器和處理器
    if connection_manager is None:
        connection_manager = ConnectionManager()

    if handler is None:
        handler = WebSocketHandler(connection_manager)

    @router.websocket("/chat")
    async def websocket_chat(
        websocket: WebSocket,
        token: Optional[str] = Query(None, description="認證令牌"),
        user_id: Optional[str] = Query(None, description="用戶 ID"),
    ):
        """
        WebSocket 聊天端點

        支援的消息類型：
        - ping: 心跳檢測
        - chat: 發送聊天消息（非串流）
        - chat_stream: 發送聊天消息（串流）
        - join_room: 加入房間
        - leave_room: 離開房間
        - conversation_start: 開始新對話
        - conversation_end: 結束對話
        - conversation_history: 獲取對話歷史
        - typing: 輸入狀態更新

        消息格式：
        ```json
        {
            "type": "chat",
            "data": {
                "message": "你好",
                "conversation_id": "optional-id"
            }
        }
        ```
        """
        connection_id = str(uuid.uuid4())

        try:
            # 建立連接
            connection = await connection_manager.connect(
                websocket=websocket,
                connection_id=connection_id,
                user_id=user_id,
                metadata={"token": token},
            )

            # 發送歡迎消息
            await connection_manager.send_personal(
                connection_id,
                {
                    "message": "連接成功",
                    "connection_id": connection_id,
                    "user_id": user_id,
                },
                message_type="connected",
            )

            # 消息循環
            while True:
                message = await connection_manager.receive_message(connection_id)

                if message is None:
                    # 連接已斷開
                    break

                # 處理消息
                response = await handler.handle_message(connection, message)

                # 發送回覆（如果有）
                if response:
                    await connection_manager.send_personal(
                        connection_id,
                        response.get("data", {}),
                        message_type=response.get("type", "response"),
                    )

        except WebSocketDisconnect:
            logger.info(f"WebSocket 連接斷開: {connection_id}")
        except Exception as e:
            logger.error(f"WebSocket 錯誤 ({connection_id}): {e}")
        finally:
            await connection_manager.disconnect(connection_id)

    @router.websocket("/stream/{conversation_id}")
    async def websocket_stream(
        websocket: WebSocket,
        conversation_id: str,
        token: Optional[str] = Query(None, description="認證令牌"),
    ):
        """
        WebSocket 串流端點

        專用於串流聊天的 WebSocket 連接。
        每個連接對應一個對話。

        消息格式：
        ```json
        {
            "message": "你好",
            "temperature": 0.7,
            "max_tokens": 256
        }
        ```
        """
        connection_id = f"stream-{conversation_id}-{uuid.uuid4().hex[:8]}"

        try:
            # 建立連接
            connection = await connection_manager.connect(
                websocket=websocket,
                connection_id=connection_id,
                metadata={
                    "token": token,
                    "conversation_id": conversation_id,
                    "stream_mode": True,
                },
            )

            # 發送就緒消息
            await connection_manager.send_personal(
                connection_id,
                {
                    "message": "串流連接就緒",
                    "connection_id": connection_id,
                    "conversation_id": conversation_id,
                },
                message_type="ready",
            )

            # 消息循環
            while True:
                message = await connection_manager.receive_message(connection_id)

                if message is None:
                    break

                # 處理串流聊天
                await handler._handle_chat_stream(
                    connection,
                    {
                        "message": message.get("message", ""),
                        "conversation_id": conversation_id,
                        **message,
                    },
                )

        except WebSocketDisconnect:
            logger.info(f"串流連接斷開: {connection_id}")
        except Exception as e:
            logger.error(f"串流錯誤 ({connection_id}): {e}")
        finally:
            await connection_manager.disconnect(connection_id)

    @router.get("/stats")
    async def websocket_stats() -> Dict[str, Any]:
        """獲取 WebSocket 統計信息"""
        return connection_manager.get_stats()

    @router.get("/connections")
    async def websocket_connections() -> list:
        """獲取所有連接詳情"""
        return connection_manager.get_connection_details()

    return router


# ============================================================================
# 便捷函數
# ============================================================================


def setup_websocket(
    app,
    generator=None,
    safety_filter=None,
    prefix: str = "/ws",
):
    """
    設置 WebSocket 功能

    Args:
        app: FastAPI 應用
        generator: 文本生成器
        safety_filter: 安全過濾器
        prefix: 路由前綴

    Returns:
        (ConnectionManager, WebSocketHandler) 元組
    """
    # 創建管理器和處理器
    manager = ConnectionManager()
    handler = WebSocketHandler(
        connection_manager=manager,
        generator=generator,
        safety_filter=safety_filter,
    )

    # 創建並掛載路由
    router = create_websocket_router(
        connection_manager=manager,
        handler=handler,
        prefix=prefix,
    )
    app.include_router(router)

    # 設置生命週期事件
    @app.on_event("startup")
    async def start_websocket():
        await manager.start_heartbeat()
        logger.info("WebSocket 服務已啟動")

    @app.on_event("shutdown")
    async def stop_websocket():
        await manager.stop_heartbeat()
        logger.info("WebSocket 服務已關閉")

    return manager, handler
