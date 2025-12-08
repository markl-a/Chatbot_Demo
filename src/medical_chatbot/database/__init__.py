"""
資料庫模組

提供資料庫連接、模型和管理功能。
"""
from .models import (
    Base,
    User,
    Session,
    Message,
    KnowledgeDocument,
    APIKey,
    Feedback,
)
from .manager import DatabaseManager
from .pool_manager import (
    DatabasePoolManager,
    PoolStats,
)

__all__ = [
    "Base",
    "User",
    "Session",
    "Message",
    "KnowledgeDocument",
    "APIKey",
    "Feedback",
    "DatabaseManager",
    # 連接池管理
    "DatabasePoolManager",
    "PoolStats",
]
