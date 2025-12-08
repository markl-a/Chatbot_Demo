"""
FastAPI 追蹤中間件

為 FastAPI 應用添加自動追蹤功能。
"""

import time
from typing import Callable, Optional

from fastapi import FastAPI, Request, Response
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware

from medical_chatbot.tracing.tracer import Tracer, TracerConfig, get_tracer, setup_tracing
from medical_chatbot.tracing.context import extract_context, get_current_trace_id

try:
    from opentelemetry import trace
    from opentelemetry.trace import SpanKind

    OPENTELEMETRY_AVAILABLE = True
except ImportError:
    OPENTELEMETRY_AVAILABLE = False
    SpanKind = None


class TracingMiddleware(BaseHTTPMiddleware):
    """
    追蹤中間件

    自動為每個 HTTP 請求創建追蹤 Span。
    """

    def __init__(
        self,
        app,
        tracer: Optional[Tracer] = None,
        exclude_paths: list = None,
        record_request_body: bool = False,
        record_response_body: bool = False,
    ):
        """
        初始化追蹤中間件

        Args:
            app: FastAPI 應用
            tracer: 追蹤器（可選）
            exclude_paths: 排除追蹤的路徑
            record_request_body: 是否記錄請求體
            record_response_body: 是否記錄響應體
        """
        super().__init__(app)
        self.tracer = tracer or get_tracer()
        self.exclude_paths = exclude_paths or [
            "/health",
            "/metrics",
            "/docs",
            "/redoc",
            "/openapi.json",
        ]
        self.record_request_body = record_request_body
        self.record_response_body = record_response_body

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """處理請求"""
        # 檢查是否排除路徑
        path = request.url.path
        if any(path.startswith(excluded) for excluded in self.exclude_paths):
            return await call_next(request)

        if not self.tracer.is_enabled:
            return await call_next(request)

        # 提取傳入的追蹤上下文
        headers = dict(request.headers)
        parent_context = extract_context(headers)

        # 創建 Span
        span_name = f"{request.method} {path}"
        attributes = {
            "http.method": request.method,
            "http.url": str(request.url),
            "http.scheme": request.url.scheme,
            "http.host": request.url.hostname,
            "http.target": path,
            "http.user_agent": request.headers.get("user-agent", ""),
            "http.client_ip": request.client.host if request.client else "",
        }

        # 添加查詢參數
        if request.query_params:
            attributes["http.query_string"] = str(request.query_params)

        span_kind = SpanKind.SERVER if OPENTELEMETRY_AVAILABLE else None

        start_time = time.time()

        with self.tracer.start_span(
            span_name,
            attributes=attributes,
            kind=span_kind,
        ) as span:
            # 記錄請求體（如果啟用）
            if self.record_request_body:
                try:
                    body = await request.body()
                    if body:
                        self.tracer.add_event(
                            "request.body",
                            {"body": body.decode("utf-8")[:1000]},  # 限制大小
                        )
                except Exception:
                    pass

            try:
                response = await call_next(request)

                # 記錄響應信息
                duration = time.time() - start_time
                self.tracer.set_attribute("http.status_code", response.status_code)
                self.tracer.set_attribute("http.duration_ms", duration * 1000)

                # 設置狀態
                if response.status_code >= 400:
                    self.tracer.set_status("error", f"HTTP {response.status_code}")
                else:
                    self.tracer.set_status("ok")

                # 添加追蹤 ID 到響應標頭
                trace_id = get_current_trace_id()
                if trace_id:
                    response.headers["X-Trace-ID"] = trace_id

                return response

            except Exception as e:
                # 記錄異常
                self.tracer.record_exception(e)
                self.tracer.set_status("error", str(e))
                raise


def setup_fastapi_tracing(
    app: FastAPI,
    service_name: str = "medical-chatbot",
    service_version: str = "0.2.0",
    exporter_type: str = "console",
    otlp_endpoint: str = "http://localhost:4317",
    exclude_paths: list = None,
    enabled: bool = True,
) -> Tracer:
    """
    設置 FastAPI 追蹤

    Args:
        app: FastAPI 應用
        service_name: 服務名稱
        service_version: 服務版本
        exporter_type: 導出器類型
        otlp_endpoint: OTLP 端點
        exclude_paths: 排除追蹤的路徑
        enabled: 是否啟用

    Returns:
        Tracer 實例
    """
    # 創建配置
    config = TracerConfig(
        service_name=service_name,
        service_version=service_version,
        exporter_type=exporter_type,
        otlp_endpoint=otlp_endpoint,
        enabled=enabled,
    )

    # 設置追蹤器
    tracer = setup_tracing(config)

    # 添加中間件
    if enabled:
        app.add_middleware(
            TracingMiddleware,
            tracer=tracer,
            exclude_paths=exclude_paths,
        )

    # 添加追蹤端點
    @app.get("/tracing/info")
    async def tracing_info():
        """獲取追蹤信息"""
        return {
            "enabled": tracer.is_enabled,
            "service_name": config.service_name,
            "service_version": config.service_version,
            "exporter_type": config.exporter_type,
            "current_trace_id": get_current_trace_id(),
        }

    # 設置關閉事件
    @app.on_event("shutdown")
    async def shutdown_tracing():
        tracer.shutdown()

    logger.info(f"FastAPI 追蹤已設置 (啟用: {enabled}, 導出器: {exporter_type})")

    return tracer


# ============================================================================
# 追蹤裝飾器（用於路由函數）
# ============================================================================


def trace_route(
    name: Optional[str] = None,
    attributes: dict = None,
):
    """
    路由追蹤裝飾器

    Args:
        name: Span 名稱
        attributes: 屬性

    Returns:
        裝飾器
    """
    from functools import wraps

    def decorator(func: Callable) -> Callable:
        span_name = name or func.__name__

        @wraps(func)
        async def wrapper(*args, **kwargs):
            tracer = get_tracer()
            with tracer.start_span(span_name, attributes=attributes):
                return await func(*args, **kwargs)

        return wrapper

    return decorator
