"""
WebSocket 實時通信示範

展示如何使用 WebSocket 功能進行即時聊天。
"""

import asyncio
import json
from fastapi import FastAPI
import uvicorn

from medical_chatbot.websocket import (
    ConnectionManager,
    WebSocketHandler,
    setup_websocket,
)


# ============================================================================
# 基本用法
# ============================================================================


def basic_example():
    """基本 WebSocket 設置示範"""
    print("=" * 60)
    print("WebSocket 基本用法示範")
    print("=" * 60)

    # 創建 FastAPI 應用
    app = FastAPI(title="WebSocket 示範")

    # 設置 WebSocket（最簡單的方式）
    manager, handler = setup_websocket(app)

    print("""
WebSocket 已設置完成！

端點：
- ws://localhost:8000/ws/chat - 通用聊天端點
- ws://localhost:8000/ws/stream/{conversation_id} - 串流聊天端點
- GET /ws/stats - WebSocket 統計信息
- GET /ws/connections - 連接詳情

消息格式（發送）：
{
    "type": "chat",
    "data": {
        "message": "你好",
        "conversation_id": "optional-id"
    }
}

消息類型：
- ping: 心跳檢測
- chat: 非串流聊天
- chat_stream: 串流聊天
- join_room: 加入房間
- leave_room: 離開房間
- conversation_start: 開始對話
- conversation_end: 結束對話
- typing: 輸入狀態
""")

    return app


# ============================================================================
# 自定義消息處理
# ============================================================================


def custom_handler_example():
    """自定義消息處理器示範"""
    print("=" * 60)
    print("自定義消息處理器示範")
    print("=" * 60)

    # 創建連接管理器
    manager = ConnectionManager(
        heartbeat_interval=30.0,
        heartbeat_timeout=60.0,
        max_connections=100,
    )

    # 創建消息處理器
    handler = WebSocketHandler(connection_manager=manager)

    # 註冊自定義消息處理器
    async def handle_custom_message(connection, data):
        """處理自定義消息類型"""
        print(f"收到自定義消息: {data}")
        return {
            "type": "custom_response",
            "data": {
                "message": f"收到你的自定義消息: {data.get('content', '')}",
                "status": "success",
            },
        }

    handler.register_handler("custom_type", handle_custom_message)

    print("""
已註冊自定義消息處理器！

發送以下消息測試：
{
    "type": "custom_type",
    "data": {
        "content": "這是自定義內容"
    }
}
""")

    return manager, handler


# ============================================================================
# 事件回調
# ============================================================================


def callback_example():
    """事件回調示範"""
    print("=" * 60)
    print("事件回調示範")
    print("=" * 60)

    manager = ConnectionManager()

    # 註冊連接事件回調
    @manager.on_connect
    async def on_connect(connection):
        print(f"新連接: {connection.connection_id}")
        print(f"  用戶: {connection.user_id}")
        print(f"  連接時間: {connection.connected_at}")

    # 註冊斷開事件回調
    @manager.on_disconnect
    async def on_disconnect(connection):
        print(f"連接斷開: {connection.connection_id}")

    # 註冊消息事件回調
    @manager.on_message
    async def on_message(connection, message):
        print(f"收到消息 ({connection.connection_id}): {message}")

    print("""
事件回調已註冊！

支援的事件：
- on_connect: 新連接建立時觸發
- on_disconnect: 連接斷開時觸發
- on_message: 收到消息時觸發
""")

    return manager


# ============================================================================
# 房間功能
# ============================================================================


async def room_example():
    """房間功能示範"""
    print("=" * 60)
    print("房間功能示範")
    print("=" * 60)

    from unittest.mock import AsyncMock

    manager = ConnectionManager()

    # 創建模擬連接
    ws1 = AsyncMock()
    ws1.accept = AsyncMock()
    ws1.send_json = AsyncMock()
    ws2 = AsyncMock()
    ws2.accept = AsyncMock()
    ws2.send_json = AsyncMock()

    # 建立連接
    await manager.connect(websocket=ws1, connection_id="user-1", user_id="alice")
    await manager.connect(websocket=ws2, connection_id="user-2", user_id="bob")

    # 加入房間
    await manager.join_room("user-1", "chat-room-1")
    await manager.join_room("user-2", "chat-room-1")

    print("用戶已加入房間 'chat-room-1'")

    # 發送房間消息
    await manager.broadcast_to_room(
        "chat-room-1",
        {"message": "大家好！"},
        message_type="room_message",
        exclude={"user-1"},  # 排除發送者
    )

    print("已向房間廣播消息（排除發送者）")

    # 獲取房間連接
    connections = manager.get_room_connections("chat-room-1")
    print(f"房間內連接數: {len(connections)}")

    # 離開房間
    await manager.leave_room("user-1", "chat-room-1")
    print("user-1 已離開房間")

    # 統計信息
    stats = manager.get_stats()
    print(f"\n統計信息: {json.dumps(stats, indent=2)}")


# ============================================================================
# 完整應用示範
# ============================================================================


def full_app_example():
    """完整應用示範"""
    print("=" * 60)
    print("完整 WebSocket 應用示範")
    print("=" * 60)

    from fastapi import FastAPI, Query, WebSocket
    from medical_chatbot.websocket import create_websocket_router

    app = FastAPI(title="Medical Chatbot WebSocket API")

    # 創建連接管理器
    manager = ConnectionManager(
        heartbeat_interval=30.0,
        max_connections=1000,
    )

    # 創建處理器（這裡可以注入真正的生成器）
    handler = WebSocketHandler(
        connection_manager=manager,
        generator=None,  # 替換為真正的生成器
        safety_filter=None,  # 替換為真正的安全過濾器
    )

    # 創建並掛載路由
    ws_router = create_websocket_router(
        connection_manager=manager,
        handler=handler,
        prefix="/ws",
    )
    app.include_router(ws_router)

    # 添加生命週期事件
    @app.on_event("startup")
    async def startup():
        await manager.start_heartbeat()
        print("WebSocket 心跳檢測已啟動")

    @app.on_event("shutdown")
    async def shutdown():
        await manager.stop_heartbeat()
        print("WebSocket 服務已關閉")

    # 添加健康檢查端點
    @app.get("/health")
    async def health():
        return {
            "status": "healthy",
            "websocket": manager.get_stats(),
        }

    print("""
完整應用已創建！

運行: uvicorn websocket_example:app --reload

端點：
- ws://localhost:8000/ws/chat
- ws://localhost:8000/ws/stream/{conversation_id}
- GET /ws/stats
- GET /ws/connections
- GET /health
""")

    return app


# ============================================================================
# 主程序
# ============================================================================


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Medical Chatbot WebSocket 示範")
    print("=" * 60 + "\n")

    # 運行各個示範
    basic_example()
    print("\n")

    custom_handler_example()
    print("\n")

    callback_example()
    print("\n")

    # 運行異步示範
    asyncio.run(room_example())
    print("\n")

    # 創建完整應用
    app = full_app_example()

    # 可選：運行服務器
    # uvicorn.run(app, host="0.0.0.0", port=8000)
