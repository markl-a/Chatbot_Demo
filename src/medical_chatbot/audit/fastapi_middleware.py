"""
FastAPI 審計中間件

自動記錄 API 請求和回覆。
"""
from typing import Optional, Callable, Any
from functools import wraps
import time

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.datastructures import Headers
from loguru import logger

from .audit_logger import AuditLogger, AuditEventType, AuditLevel


# ============================================================================
# 審計中間件
# ============================================================================


class AuditMiddleware(BaseHTTPMiddleware):
    """審計中間件"""

    def __init__(
        self,
        app,
        audit_logger: AuditLogger,
        exclude_paths: Optional[list] = None,
        log_request_body: bool = False,
        log_response_body: bool = False,
    ):
        """
        初始化審計中間件

        Args:
            app: FastAPI 應用
            audit_logger: 審計日誌記錄器
            exclude_paths: 排除的路徑列表
            log_request_body: 是否記錄請求主體
            log_response_body: 是否記錄回覆主體
        """
        super().__init__(app)
        self.audit_logger = audit_logger
        self.exclude_paths = exclude_paths or ["/health", "/metrics", "/docs", "/openapi.json"]
        self.log_request_body = log_request_body
        self.log_response_body = log_response_body

        logger.info("審計中間件初始化完成")

    async def dispatch(self, request: Request, call_next):
        """處理請求"""
        # 檢查是否排除此路徑
        if self._should_exclude(request.url.path):
            return await call_next(request)

        # 記錄請求開始時間
        start_time = time.time()

        # 獲取請求資訊
        request_info = await self._get_request_info(request)

        # 處理請求
        try:
            response = await call_next(request)
            status_code = response.status_code

        except Exception as e:
            # 記錄錯誤
            self.audit_logger.log(
                event_type=AuditEventType.API_ERROR,
                message=f"API 請求異常: {request.method} {request.url.path}",
                level=AuditLevel.ERROR,
                user_id=request_info.get("user_id"),
                ip_address=request_info.get("ip_address"),
                resource=request.url.path,
                action=request.method,
                result="error",
                metadata={
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            raise

        # 計算回應時間
        response_time = time.time() - start_time

        # 記錄 API 調用
        self.audit_logger.log_api_call(
            endpoint=request.url.path,
            method=request.method,
            user_id=request_info.get("user_id"),
            status_code=status_code,
            response_time=response_time,
        )

        # 添加回應時間到 header
        response.headers["X-Response-Time"] = f"{response_time:.4f}"

        return response

    def _should_exclude(self, path: str) -> bool:
        """檢查是否應該排除此路徑"""
        for exclude_path in self.exclude_paths:
            if path.startswith(exclude_path):
                return True
        return False

    async def _get_request_info(self, request: Request) -> dict:
        """獲取請求資訊"""
        # 獲取 IP 地址
        ip_address = self._get_client_ip(request)

        # 獲取用戶 ID（從 header 或 token）
        user_id = self._get_user_id(request)

        # 獲取 User-Agent
        user_agent = request.headers.get("user-agent")

        info = {
            "ip_address": ip_address,
            "user_id": user_id,
            "user_agent": user_agent,
            "method": request.method,
            "path": request.url.path,
            "query_params": dict(request.query_params),
        }

        # 記錄請求主體（如果需要）
        if self.log_request_body and request.method in ["POST", "PUT", "PATCH"]:
            try:
                # 注意：這會消耗 request body，需要小心處理
                # body = await request.body()
                # info["request_body"] = body.decode("utf-8")
                pass
            except Exception as e:
                logger.warning(f"無法讀取請求主體: {e}")

        return info

    def _get_client_ip(self, request: Request) -> str:
        """獲取客戶端 IP"""
        # 檢查代理 header
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        # 使用直接連接的 IP
        if request.client:
            return request.client.host

        return "unknown"

    def _get_user_id(self, request: Request) -> Optional[str]:
        """獲取用戶 ID"""
        # 從 header 獲取
        user_id = request.headers.get("x-user-id")
        if user_id:
            return user_id

        # 從 state 獲取（如果有認證中間件設置）
        if hasattr(request.state, "user_id"):
            return request.state.user_id

        # 從 token 解析（需要實現 JWT 解析）
        # auth_header = request.headers.get("authorization")
        # if auth_header and auth_header.startswith("Bearer "):
        #     token = auth_header[7:]
        #     user_id = parse_jwt_token(token)
        #     return user_id

        return None


# ============================================================================
# 便捷設置函數
# ============================================================================


def setup_audit_middleware(
    app,
    audit_logger: AuditLogger,
    exclude_paths: Optional[list] = None,
):
    """
    設置審計中間件

    Args:
        app: FastAPI 應用
        audit_logger: 審計日誌記錄器
        exclude_paths: 排除的路徑列表

    Example:
        ```python
        from fastapi import FastAPI
        from src.medical_chatbot.audit import AuditLogger, setup_audit_middleware

        app = FastAPI()
        audit_logger = AuditLogger()
        setup_audit_middleware(app, audit_logger)
        ```
    """
    app.add_middleware(
        AuditMiddleware,
        audit_logger=audit_logger,
        exclude_paths=exclude_paths,
    )

    logger.info("審計中間件已註冊")


# ============================================================================
# 裝飾器
# ============================================================================


def audit_event(
    event_type: AuditEventType,
    message: Optional[str] = None,
    level: AuditLevel = AuditLevel.INFO,
):
    """
    審計事件裝飾器

    用於標記需要審計的函數。

    Args:
        event_type: 事件類型
        message: 事件訊息
        level: 審計等級

    Example:
        ```python
        from src.medical_chatbot.audit import audit_event, AuditEventType, AuditLevel

        @audit_event(
            event_type=AuditEventType.DATA_CREATE,
            message="創建新用戶",
            level=AuditLevel.INFO,
        )
        def create_user(username: str):
            # 創建用戶邏輯
            pass
        ```
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # 獲取審計記錄器（從依賴注入或全局）
            audit_logger = kwargs.get("audit_logger")

            # 執行函數
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                success = True
                error = None
            except Exception as e:
                success = False
                error = str(e)
                raise
            finally:
                # 記錄審計事件
                if audit_logger:
                    execution_time = time.time() - start_time

                    event_message = message or f"執行 {func.__name__}"

                    audit_logger.log(
                        event_type=event_type,
                        message=event_message,
                        level=level if success else AuditLevel.ERROR,
                        resource=func.__name__,
                        action="execute",
                        result="success" if success else "error",
                        metadata={
                            "execution_time": execution_time,
                            "error": error,
                            "args": str(args)[:200],  # 限制長度
                            "kwargs": str(kwargs)[:200],
                        },
                    )

            return result

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # 獲取審計記錄器
            audit_logger = kwargs.get("audit_logger")

            # 執行函數
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                success = True
                error = None
            except Exception as e:
                success = False
                error = str(e)
                raise
            finally:
                # 記錄審計事件
                if audit_logger:
                    execution_time = time.time() - start_time

                    event_message = message or f"執行 {func.__name__}"

                    audit_logger.log(
                        event_type=event_type,
                        message=event_message,
                        level=level if success else AuditLevel.ERROR,
                        resource=func.__name__,
                        action="execute",
                        result="success" if success else "error",
                        metadata={
                            "execution_time": execution_time,
                            "error": error,
                        },
                    )

            return result

        # 根據函數類型返回對應的包裝器
        import inspect

        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# ============================================================================
# 審計事件路由
# ============================================================================


def create_audit_routes(audit_logger: AuditLogger):
    """
    創建審計事件查詢路由

    Args:
        audit_logger: 審計日誌記錄器

    Returns:
        APIRouter

    Example:
        ```python
        from fastapi import FastAPI
        from src.medical_chatbot.audit import AuditLogger, create_audit_routes

        app = FastAPI()
        audit_logger = AuditLogger()
        router = create_audit_routes(audit_logger)
        app.include_router(router, prefix="/audit", tags=["audit"])
        ```
    """
    from fastapi import APIRouter, Query
    from typing import List

    router = APIRouter()

    @router.get("/summary")
    async def get_audit_summary():
        """獲取審計摘要"""
        return audit_logger.generate_summary()

    @router.get("/events")
    async def get_audit_events(
        user_id: Optional[str] = Query(None),
        event_type: Optional[str] = Query(None),
        level: Optional[str] = Query(None),
        limit: int = Query(100, ge=1, le=1000),
    ):
        """獲取審計事件"""
        events = audit_logger.event_buffer

        # 過濾
        if user_id:
            events = [e for e in events if e.user_id == user_id]

        if event_type:
            events = [e for e in events if e.event_type.value == event_type]

        if level:
            events = [e for e in events if e.level.value == level]

        # 限制數量
        events = events[:limit]

        return {"total": len(events), "events": [e.to_dict() for e in events]}

    @router.get("/events/security")
    async def get_security_events():
        """獲取安全事件"""
        events = audit_logger.get_security_events()
        return {"total": len(events), "events": [e.to_dict() for e in events]}

    @router.get("/events/failed")
    async def get_failed_operations():
        """獲取失敗的操作"""
        events = audit_logger.get_failed_operations()
        return {"total": len(events), "events": [e.to_dict() for e in events]}

    @router.post("/export")
    async def export_audit_events(
        file_path: str,
        format: str = "json",
    ):
        """導出審計事件"""
        try:
            audit_logger.export_events(file_path, format=format)
            return {"status": "success", "file_path": file_path}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    return router
