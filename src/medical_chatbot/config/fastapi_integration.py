"""
FastAPI 配置整合

提供 FastAPI 應用的配置整合工具。
"""
from typing import Optional
from functools import lru_cache

from fastapi import Depends, HTTPException, status
from loguru import logger

from .config import Settings


# ============================================================================
# 單例配置
# ============================================================================


@lru_cache()
def get_settings() -> Settings:
    """
    獲取配置單例

    使用 lru_cache 確保配置只加載一次。

    Returns:
        Settings: 配置實例

    Example:
        ```python
        from fastapi import Depends

        @app.get("/info")
        async def get_info(settings: Settings = Depends(get_settings)):
            return {"environment": settings.ENVIRONMENT}
        ```
    """
    settings = Settings()
    logger.info(f"配置已加載: {settings.ENVIRONMENT} 環境")
    return settings


# ============================================================================
# 配置依賴
# ============================================================================


def get_database_url(settings: Settings = Depends(get_settings)) -> str:
    """獲取資料庫 URL"""
    return settings.DATABASE_URL


def get_redis_config(settings: Settings = Depends(get_settings)) -> dict:
    """獲取 Redis 配置"""
    return {
        "host": settings.REDIS_HOST,
        "port": settings.REDIS_PORT,
        "db": settings.REDIS_DB,
        "password": settings.REDIS_PASSWORD,
        "max_connections": settings.REDIS_MAX_CONNECTIONS,
    }


def get_model_config(settings: Settings = Depends(get_settings)) -> dict:
    """獲取模型配置"""
    return {
        "name": settings.MODEL_NAME,
        "device": settings.DEVICE,
        "max_length": settings.MAX_LENGTH,
        "temperature": settings.TEMPERATURE,
        "top_k": settings.TOP_K,
        "top_p": settings.TOP_P,
    }


def get_rate_limit_config(settings: Settings = Depends(get_settings)) -> dict:
    """獲取速率限制配置"""
    return {
        "strategy": settings.RATE_LIMIT_STRATEGY,
        "default_limit": settings.RATE_LIMIT_DEFAULT,
        "window": settings.RATE_LIMIT_WINDOW,
    }


# ============================================================================
# 配置驗證
# ============================================================================


def require_production_mode(settings: Settings = Depends(get_settings)):
    """
    要求生產模式

    用於保護只能在生產環境運行的端點。

    Raises:
        HTTPException: 如果不是生產環境
    """
    if settings.ENVIRONMENT != "production":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="此端點僅在生產環境可用",
        )


def require_debug_mode(settings: Settings = Depends(get_settings)):
    """
    要求調試模式

    用於保護調試端點。

    Raises:
        HTTPException: 如果不是調試模式
    """
    if not settings.DEBUG:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="此端點僅在調試模式可用",
        )


def require_testing_enabled(settings: Settings = Depends(get_settings)):
    """
    要求啟用測試

    Raises:
        HTTPException: 如果未啟用測試
    """
    if not settings.TESTING:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="此端點僅在測試模式可用",
        )


# ============================================================================
# 配置資訊端點
# ============================================================================


def setup_config_routes(app):
    """
    設置配置相關路由

    Args:
        app: FastAPI 應用實例

    Example:
        ```python
        from fastapi import FastAPI
        from src.medical_chatbot.config import setup_config_routes

        app = FastAPI()
        setup_config_routes(app)
        ```
    """
    from fastapi import APIRouter

    router = APIRouter(prefix="/config", tags=["config"])

    @router.get("/info")
    async def get_config_info(settings: Settings = Depends(get_settings)):
        """
        獲取配置資訊

        Returns:
            配置的非敏感資訊
        """
        return {
            "environment": settings.ENVIRONMENT,
            "debug": settings.DEBUG,
            "testing": settings.TESTING,
            "app_name": settings.APP_NAME,
            "app_version": settings.APP_VERSION,
            "model_name": settings.MODEL_NAME,
            "device": settings.DEVICE,
        }

    @router.get("/database")
    async def get_database_info(settings: Settings = Depends(get_settings)):
        """
        獲取資料庫配置資訊

        Returns:
            資料庫配置（隱藏敏感資訊）
        """
        # 隱藏密碼
        url = settings.DATABASE_URL
        if "@" in url:
            # 格式: dialect://user:password@host/db
            parts = url.split("@")
            if ":" in parts[0]:
                protocol_user = parts[0].rsplit(":", 1)[0]
                url = f"{protocol_user}:***@{parts[1]}"

        return {
            "url": url,
            "pool_size": settings.DATABASE_POOL_SIZE,
            "max_overflow": settings.DATABASE_MAX_OVERFLOW,
            "echo": settings.DATABASE_ECHO,
        }

    @router.get("/redis")
    async def get_redis_info(settings: Settings = Depends(get_settings)):
        """
        獲取 Redis 配置資訊

        Returns:
            Redis 配置（隱藏敏感資訊）
        """
        return {
            "host": settings.REDIS_HOST,
            "port": settings.REDIS_PORT,
            "db": settings.REDIS_DB,
            "max_connections": settings.REDIS_MAX_CONNECTIONS,
            "has_password": bool(settings.REDIS_PASSWORD),
        }

    @router.get("/model")
    async def get_model_info(settings: Settings = Depends(get_settings)):
        """
        獲取模型配置資訊

        Returns:
            模型配置
        """
        return {
            "name": settings.MODEL_NAME,
            "device": settings.DEVICE,
            "max_length": settings.MAX_LENGTH,
            "temperature": settings.TEMPERATURE,
            "top_k": settings.TOP_K,
            "top_p": settings.TOP_P,
            "batch_size": settings.BATCH_SIZE,
        }

    @router.get("/cache")
    async def get_cache_info(settings: Settings = Depends(get_settings)):
        """
        獲取快取配置資訊

        Returns:
            快取配置
        """
        return {
            "strategy": settings.CACHE_STRATEGY,
            "ttl": settings.CACHE_TTL,
            "max_size": settings.CACHE_MAX_SIZE,
        }

    @router.get("/rate-limit")
    async def get_rate_limit_info(settings: Settings = Depends(get_settings)):
        """
        獲取速率限制配置資訊

        Returns:
            速率限制配置
        """
        return {
            "strategy": settings.RATE_LIMIT_STRATEGY,
            "default_limit": settings.RATE_LIMIT_DEFAULT,
            "window": settings.RATE_LIMIT_WINDOW,
        }

    @router.post("/reload", dependencies=[Depends(require_debug_mode)])
    async def reload_config():
        """
        重新加載配置（僅調試模式）

        清除快取的配置並重新加載。

        Returns:
            重新加載結果
        """
        get_settings.cache_clear()
        new_settings = get_settings()

        logger.info("配置已重新加載")

        return {
            "status": "success",
            "message": "配置已重新加載",
            "environment": new_settings.ENVIRONMENT,
        }

    app.include_router(router)

    logger.info("配置路由已註冊")


# ============================================================================
# 啟動事件
# ============================================================================


def setup_startup_events(app):
    """
    設置啟動事件

    Args:
        app: FastAPI 應用實例
    """

    @app.on_event("startup")
    async def log_configuration():
        """記錄啟動時的配置"""
        settings = get_settings()

        logger.info("=" * 80)
        logger.info(f"應用啟動: {settings.APP_NAME} v{settings.APP_VERSION}")
        logger.info(f"環境: {settings.ENVIRONMENT}")
        logger.info(f"調試模式: {settings.DEBUG}")
        logger.info(f"模型: {settings.MODEL_NAME}")
        logger.info(f"設備: {settings.DEVICE}")
        logger.info("=" * 80)


def setup_shutdown_events(app):
    """
    設置關閉事件

    Args:
        app: FastAPI 應用實例
    """

    @app.on_event("shutdown")
    async def log_shutdown():
        """記錄關閉"""
        settings = get_settings()
        logger.info(f"應用關閉: {settings.APP_NAME}")


# ============================================================================
# 完整設置
# ============================================================================


def setup_config_integration(app, include_routes: bool = True):
    """
    完整的配置整合設置

    Args:
        app: FastAPI 應用實例
        include_routes: 是否包含配置路由

    Example:
        ```python
        from fastapi import FastAPI
        from src.medical_chatbot.config import setup_config_integration

        app = FastAPI()
        setup_config_integration(app)
        ```
    """
    # 設置事件
    setup_startup_events(app)
    setup_shutdown_events(app)

    # 設置路由（可選）
    if include_routes:
        setup_config_routes(app)

    logger.info("配置整合設置完成")
