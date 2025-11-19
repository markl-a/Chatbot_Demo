"""
健康檢查模組

提供應用和組件的健康狀態檢查。
"""
from .health_checker import HealthChecker, HealthStatus, ComponentStatus
from .fastapi_routes import (
    create_health_router,
    setup_health_routes,
    setup_kubernetes_health_routes,
)

__all__ = [
    # 核心類
    "HealthChecker",
    "HealthStatus",
    "ComponentStatus",
    # FastAPI 整合
    "create_health_router",
    "setup_health_routes",
    "setup_kubernetes_health_routes",
]
