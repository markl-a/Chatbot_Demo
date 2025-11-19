"""
FastAPI 中間件整合

提供速率限制中間件和裝飾器。
"""
from typing import Optional, Callable
from functools import wraps

from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from loguru import logger

from .rate_limiter import RateLimiter, RateLimitStrategy
from ..utils.exceptions import RateLimitException


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI 速率限制中間件"""

    def __init__(
        self,
        app,
        rate_limiter: RateLimiter,
        key_func: Optional[Callable] = None,
        limit: Optional[int] = None,
        window: Optional[int] = None,
        enabled: bool = True,
        exclude_paths: Optional[list] = None,
    ):
        """
        初始化速率限制中間件

        Args:
            app: FastAPI 應用
            rate_limiter: 速率限制器實例
            key_func: 自訂鍵生成函數（預設使用客戶端 IP）
            limit: 限制次數（None 使用 RateLimiter 預設值）
            window: 時間窗口（秒，None 使用預設值）
            enabled: 是否啟用限制
            exclude_paths: 排除的路徑列表（不進行限制）
        """
        super().__init__(app)
        self.rate_limiter = rate_limiter
        self.key_func = key_func or self._default_key_func
        self.limit = limit
        self.window = window
        self.enabled = enabled
        self.exclude_paths = exclude_paths or []

        logger.info(
            f"速率限制中間件已啟用: limit={limit}, window={window}s, "
            f"exclude_paths={exclude_paths}"
        )

    async def dispatch(self, request: Request, call_next):
        """處理請求"""
        # 檢查是否啟用
        if not self.enabled:
            return await call_next(request)

        # 檢查是否排除
        if request.url.path in self.exclude_paths:
            return await call_next(request)

        # 獲取限制鍵
        key = self.key_func(request)

        try:
            # 檢查速率限制
            allowed, info = self.rate_limiter.check_limit(
                key, limit=self.limit, window=self.window
            )

            # 添加限制資訊到響應標頭
            response = await call_next(request)
            response.headers["X-RateLimit-Limit"] = str(info["limit"])
            response.headers["X-RateLimit-Remaining"] = str(info["remaining"])
            response.headers["X-RateLimit-Reset"] = str(info["reset_time"])

            if not allowed:
                # 超過限制，返回 429
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "error": "Rate limit exceeded",
                        "message": f"請求過於頻繁，請 {info['retry_after']} 秒後重試",
                        "limit": info["limit"],
                        "retry_after": info["retry_after"],
                    },
                    headers={
                        "X-RateLimit-Limit": str(info["limit"]),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(info["reset_time"]),
                        "Retry-After": str(info["retry_after"]),
                    },
                )

            return response

        except Exception as e:
            logger.error(f"速率限制中間件錯誤: {e}")
            # 發生錯誤時允許請求通過（容錯）
            return await call_next(request)

    @staticmethod
    def _default_key_func(request: Request) -> str:
        """
        預設鍵生成函數（使用客戶端 IP）

        Args:
            request: FastAPI 請求對象

        Returns:
            限制鍵
        """
        # 優先使用 X-Forwarded-For（代理/負載均衡）
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()

        # 使用客戶端 IP
        if request.client:
            return request.client.host

        # 降級為固定鍵（不推薦）
        return "unknown"


# ============================================================================
# 裝飾器
# ============================================================================


def rate_limit(
    rate_limiter: RateLimiter,
    limit: Optional[int] = None,
    window: Optional[int] = None,
    key_func: Optional[Callable] = None,
):
    """
    速率限制裝飾器

    Args:
        rate_limiter: 速率限制器實例
        limit: 限制次數（None 使用預設值）
        window: 時間窗口（秒，None 使用預設值）
        key_func: 自訂鍵生成函數

    Example:
        @app.post("/chat")
        @rate_limit(rate_limiter, limit=10, window=60)
        async def chat(request: Request):
            pass

    Example (使用 API Key):
        def get_api_key(request: Request) -> str:
            return request.headers.get("X-API-Key", "anonymous")

        @app.post("/api/chat")
        @rate_limit(rate_limiter, limit=100, window=60, key_func=get_api_key)
        async def api_chat(request: Request):
            pass
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 從參數中獲取 Request 對象
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break

            if not request:
                # 如果沒有 Request 參數，跳過限制
                logger.warning(f"{func.__name__} 沒有 Request 參數，跳過速率限制")
                return await func(*args, **kwargs)

            # 獲取限制鍵
            if key_func:
                key = key_func(request)
            else:
                # 預設使用客戶端 IP
                forwarded = request.headers.get("X-Forwarded-For")
                if forwarded:
                    key = forwarded.split(",")[0].strip()
                elif request.client:
                    key = request.client.host
                else:
                    key = "unknown"

            # 檢查速率限制
            allowed, info = rate_limiter.check_limit(key, limit=limit, window=window)

            if not allowed:
                # 超過限制
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "error": "Rate limit exceeded",
                        "message": f"請求過於頻繁，請 {info['retry_after']} 秒後重試",
                        "limit": info["limit"],
                        "retry_after": info["retry_after"],
                    },
                    headers={
                        "X-RateLimit-Limit": str(info["limit"]),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(info["reset_time"]),
                        "Retry-After": str(info["retry_after"]),
                    },
                )

            # 執行原函數
            return await func(*args, **kwargs)

        return wrapper

    return decorator


# ============================================================================
# 工具函數
# ============================================================================


def get_client_ip(request: Request) -> str:
    """
    獲取客戶端真實 IP

    Args:
        request: FastAPI 請求對象

    Returns:
        客戶端 IP
    """
    # 檢查代理標頭
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    # 使用客戶端 IP
    if request.client:
        return request.client.host

    return "unknown"


def get_api_key(request: Request, header_name: str = "X-API-Key") -> str:
    """
    獲取 API Key

    Args:
        request: FastAPI 請求對象
        header_name: API Key 標頭名稱

    Returns:
        API Key 或 "anonymous"
    """
    return request.headers.get(header_name, "anonymous")


def get_user_id(request: Request) -> str:
    """
    獲取用戶 ID（從請求狀態）

    Args:
        request: FastAPI 請求對象

    Returns:
        用戶 ID 或 "anonymous"
    """
    # 假設用戶 ID 存儲在 request.state 中（由認證中間件設置）
    return getattr(request.state, "user_id", "anonymous")


def composite_key(request: Request, *keys: str) -> str:
    """
    生成組合鍵

    Args:
        request: FastAPI 請求對象
        *keys: 鍵名稱（ip, api_key, user_id, path）

    Returns:
        組合鍵

    Example:
        >>> composite_key(request, "ip", "path")
        "192.168.1.1:/api/chat"
    """
    parts = []

    for key_type in keys:
        if key_type == "ip":
            parts.append(get_client_ip(request))
        elif key_type == "api_key":
            parts.append(get_api_key(request))
        elif key_type == "user_id":
            parts.append(get_user_id(request))
        elif key_type == "path":
            parts.append(request.url.path)
        else:
            parts.append(key_type)

    return ":".join(parts)


# ============================================================================
# 預定義鍵生成函數
# ============================================================================


def ip_key_func(request: Request) -> str:
    """基於 IP 的鍵"""
    return get_client_ip(request)


def api_key_func(request: Request) -> str:
    """基於 API Key 的鍵"""
    return get_api_key(request)


def user_key_func(request: Request) -> str:
    """基於用戶 ID 的鍵"""
    return get_user_id(request)


def ip_path_key_func(request: Request) -> str:
    """基於 IP + 路徑的鍵"""
    return composite_key(request, "ip", "path")


def api_key_path_func(request: Request) -> str:
    """基於 API Key + 路徑的鍵"""
    return composite_key(request, "api_key", "path")
