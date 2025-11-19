"""
FastAPI 健康檢查路由

提供健康檢查端點。
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger

from .health_checker import HealthChecker, HealthStatus


# ============================================================================
# 健康檢查路由
# ============================================================================


def create_health_router(
    health_checker: HealthChecker,
    prefix: str = "/health",
    tags: Optional[List[str]] = None,
) -> APIRouter:
    """
    創建健康檢查路由器

    Args:
        health_checker: 健康檢查器實例
        prefix: 路由前綴
        tags: 標籤列表

    Returns:
        配置好的路由器

    Example:
        ```python
        from fastapi import FastAPI
        from src.medical_chatbot.health import HealthChecker, create_health_router

        app = FastAPI()
        health_checker = HealthChecker(...)
        router = create_health_router(health_checker)
        app.include_router(router)
        ```
    """
    router = APIRouter(prefix=prefix, tags=tags or ["health"])

    @router.get("")
    async def health_check():
        """
        基本健康檢查

        Returns:
            簡單的健康狀態

        Example:
            ```bash
            curl http://localhost:8000/health
            ```
        """
        return {
            "status": "healthy",
            "message": "服務運行正常",
        }

    @router.get("/ping")
    async def ping():
        """
        Ping 端點

        用於負載均衡器和監控系統的簡單檢查。

        Returns:
            Pong 回覆
        """
        return {"message": "pong"}

    @router.get("/ready")
    async def readiness_check():
        """
        就緒檢查

        檢查服務是否準備好接受請求。
        檢查所有關鍵組件（資料庫、Redis、模型）。

        Returns:
            就緒狀態

        Raises:
            HTTPException: 如果服務未就緒（503）

        Example:
            ```bash
            curl http://localhost:8000/health/ready
            ```
        """
        # 檢查關鍵組件
        critical_components = ["database", "redis", "model"]
        results = health_checker.check_all(include=critical_components)

        # 檢查是否有不健康的組件
        unhealthy = [
            name
            for name, status in results.items()
            if status.status == HealthStatus.UNHEALTHY
        ]

        if unhealthy:
            logger.warning(f"就緒檢查失敗: {unhealthy}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "ready": False,
                    "message": f"服務未就緒: {', '.join(unhealthy)}",
                    "unhealthy_components": unhealthy,
                },
            )

        return {
            "ready": True,
            "message": "服務已就緒",
        }

    @router.get("/live")
    async def liveness_check():
        """
        存活檢查

        檢查服務是否存活。
        這是一個輕量級檢查，不檢查外部依賴。

        Returns:
            存活狀態

        Example:
            ```bash
            curl http://localhost:8000/health/live
            ```
        """
        return {
            "alive": True,
            "message": "服務存活",
        }

    @router.get("/detailed")
    async def detailed_health_check():
        """
        詳細健康檢查

        檢查所有組件並返回詳細報告。

        Returns:
            完整的健康報告

        Example:
            ```bash
            curl http://localhost:8000/health/detailed
            ```

        Response:
            ```json
            {
              "status": "healthy",
              "timestamp": "2024-01-01T12:00:00",
              "checks": {
                "database": {
                  "status": "healthy",
                  "response_time": 0.05,
                  ...
                },
                ...
              },
              "summary": {
                "total_checks": 5,
                "healthy": 5,
                "degraded": 0,
                "unhealthy": 0
              }
            }
            ```
        """
        report = health_checker.get_health_report()

        # 如果有不健康的組件，返回 503 狀態碼
        if report["status"] != HealthStatus.HEALTHY.value:
            logger.warning(f"健康檢查異常: {report['status']}")
            # 但仍返回完整報告（不拋出異常）
            # 這樣客戶端可以看到詳細的問題

        return report

    @router.get("/detailed/async")
    async def detailed_health_check_async():
        """
        詳細健康檢查（異步）

        使用異步方式並行檢查所有組件，速度更快。

        Returns:
            完整的健康報告

        Example:
            ```bash
            curl http://localhost:8000/health/detailed/async
            ```
        """
        report = await health_checker.get_health_report_async()
        return report

    @router.get("/component/{component_name}")
    async def check_specific_component(component_name: str):
        """
        檢查特定組件

        Args:
            component_name: 組件名稱（database, redis, model, disk, memory）

        Returns:
            組件健康狀態

        Raises:
            HTTPException: 如果組件不存在（404）

        Example:
            ```bash
            curl http://localhost:8000/health/component/database
            curl http://localhost:8000/health/component/redis
            ```
        """
        if component_name not in health_checker.checks:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"未知的組件: {component_name}",
            )

        component_status = health_checker.check_component(component_name)

        return component_status.to_dict()

    @router.get("/components")
    async def list_components():
        """
        列出所有可檢查的組件

        Returns:
            組件列表

        Example:
            ```bash
            curl http://localhost:8000/health/components
            ```
        """
        return {
            "components": list(health_checker.checks.keys()),
            "total": len(health_checker.checks),
        }

    @router.get("/summary")
    async def health_summary():
        """
        健康摘要

        快速檢查並返回簡化的摘要。

        Returns:
            健康摘要

        Example:
            ```bash
            curl http://localhost:8000/health/summary
            ```
        """
        results = health_checker.check_all()

        # 計算摘要
        total = len(results)
        healthy = sum(1 for r in results.values() if r.status == HealthStatus.HEALTHY)
        degraded = sum(1 for r in results.values() if r.status == HealthStatus.DEGRADED)
        unhealthy = sum(
            1 for r in results.values() if r.status == HealthStatus.UNHEALTHY
        )

        # 整體狀態
        if unhealthy > 0:
            overall = "unhealthy"
        elif degraded > 0:
            overall = "degraded"
        else:
            overall = "healthy"

        return {
            "status": overall,
            "summary": {
                "total": total,
                "healthy": healthy,
                "degraded": degraded,
                "unhealthy": unhealthy,
            },
        }

    return router


# ============================================================================
# 便捷設置函數
# ============================================================================


def setup_health_routes(
    app,
    health_checker: HealthChecker,
    prefix: str = "/health",
    tags: Optional[List[str]] = None,
):
    """
    設置健康檢查路由

    Args:
        app: FastAPI 應用實例
        health_checker: 健康檢查器實例
        prefix: 路由前綴
        tags: 標籤列表

    Example:
        ```python
        from fastapi import FastAPI
        from src.medical_chatbot.health import HealthChecker, setup_health_routes

        app = FastAPI()
        health_checker = HealthChecker(...)
        setup_health_routes(app, health_checker)
        ```
    """
    router = create_health_router(health_checker, prefix=prefix, tags=tags)
    app.include_router(router)

    logger.info(f"健康檢查路由已註冊: {prefix}")


# ============================================================================
# Kubernetes 風格的健康檢查
# ============================================================================


def setup_kubernetes_health_routes(
    app,
    health_checker: HealthChecker,
):
    """
    設置 Kubernetes 風格的健康檢查路由

    創建標準的 /healthz 和 /readyz 端點，
    符合 Kubernetes 的健康檢查慣例。

    Args:
        app: FastAPI 應用實例
        health_checker: 健康檢查器實例

    Example:
        ```python
        from fastapi import FastAPI
        from src.medical_chatbot.health import (
            HealthChecker,
            setup_kubernetes_health_routes,
        )

        app = FastAPI()
        health_checker = HealthChecker(...)
        setup_kubernetes_health_routes(app, health_checker)
        ```

    Kubernetes 配置:
        ```yaml
        livenessProbe:
          httpGet:
            path: /healthz
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10

        readinessProbe:
          httpGet:
            path: /readyz
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
        ```
    """

    @app.get("/healthz", tags=["health"])
    async def healthz():
        """Kubernetes liveness probe"""
        return {"status": "ok"}

    @app.get("/readyz", tags=["health"])
    async def readyz():
        """Kubernetes readiness probe"""
        # 檢查關鍵組件
        critical_components = ["database", "redis", "model"]
        results = health_checker.check_all(include=critical_components)

        # 檢查是否有不健康的組件
        unhealthy = [
            name
            for name, status in results.items()
            if status.status == HealthStatus.UNHEALTHY
        ]

        if unhealthy:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Not ready: {', '.join(unhealthy)}",
            )

        return {"status": "ok"}

    logger.info("Kubernetes 健康檢查路由已註冊: /healthz, /readyz")
