"""
WebSocket 模組

提供 WebSocket 實時通信功能。
"""

from medical_chatbot.websocket.connection_manager import ConnectionManager
from medical_chatbot.websocket.handlers import WebSocketHandler
from medical_chatbot.websocket.fastapi_routes import create_websocket_router

__all__ = [
    "ConnectionManager",
    "WebSocketHandler",
    "create_websocket_router",
]
