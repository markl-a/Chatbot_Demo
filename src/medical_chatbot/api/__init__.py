"""API modules for medical chatbot"""

from medical_chatbot.api.server import create_app
from medical_chatbot.api.graceful_shutdown import (
    GracefulShutdownManager,
    GracefulShutdownMiddleware,
    ShutdownState,
    setup_graceful_shutdown,
    graceful_lifespan,
)

__all__ = [
    "create_app",
    # 優雅關閉
    "GracefulShutdownManager",
    "GracefulShutdownMiddleware",
    "ShutdownState",
    "setup_graceful_shutdown",
    "graceful_lifespan",
]
