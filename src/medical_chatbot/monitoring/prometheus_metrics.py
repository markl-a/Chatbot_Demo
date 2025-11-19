"""
Prometheus 指標

定義和導出 Prometheus 指標。
"""
from typing import Optional, Callable
from functools import wraps
import time

from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    Info,
    generate_latest,
    REGISTRY,
    CONTENT_TYPE_LATEST,
)
from fastapi import Response
from loguru import logger


# ============================================================================
# Prometheus 指標類
# ============================================================================


class PrometheusMetrics:
    """Prometheus 指標管理器"""

    def __init__(self, app_name: str = "medical_chatbot"):
        """
        初始化 Prometheus 指標

        Args:
            app_name: 應用名稱
        """
        self.app_name = app_name

        # ====================================================================
        # HTTP 請求指標
        # ====================================================================

        # 請求計數
        self.http_requests_total = Counter(
            "http_requests_total",
            "Total HTTP requests",
            ["method", "endpoint", "status"],
        )

        # 請求延遲
        self.http_request_duration_seconds = Histogram(
            "http_request_duration_seconds",
            "HTTP request latency",
            ["method", "endpoint"],
            buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0),
        )

        # 請求大小
        self.http_request_size_bytes = Histogram(
            "http_request_size_bytes",
            "HTTP request size in bytes",
            ["method", "endpoint"],
        )

        # 回覆大小
        self.http_response_size_bytes = Histogram(
            "http_response_size_bytes",
            "HTTP response size in bytes",
            ["method", "endpoint"],
        )

        # ====================================================================
        # 模型推理指標
        # ====================================================================

        # 推理計數
        self.model_inferences_total = Counter(
            "model_inferences_total",
            "Total model inferences",
            ["model_name", "status"],
        )

        # 推理延遲
        self.model_inference_duration_seconds = Histogram(
            "model_inference_duration_seconds",
            "Model inference latency",
            ["model_name"],
            buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0),
        )

        # Token 生成速度
        self.model_tokens_per_second = Histogram(
            "model_tokens_per_second",
            "Model generation speed in tokens per second",
            ["model_name"],
        )

        # ====================================================================
        # 資料庫指標
        # ====================================================================

        # 資料庫連接池
        self.database_connections = Gauge(
            "database_connections",
            "Database connections",
            ["state"],  # active, idle
        )

        # 資料庫查詢計數
        self.database_queries_total = Counter(
            "database_queries_total",
            "Total database queries",
            ["operation", "table"],
        )

        # 資料庫查詢延遲
        self.database_query_duration_seconds = Histogram(
            "database_query_duration_seconds",
            "Database query latency",
            ["operation", "table"],
        )

        # ====================================================================
        # 快取指標
        # ====================================================================

        # 快取命中率
        self.cache_hits_total = Counter(
            "cache_hits_total",
            "Total cache hits",
            ["cache_type"],
        )

        self.cache_misses_total = Counter(
            "cache_misses_total",
            "Total cache misses",
            ["cache_type"],
        )

        # 快取大小
        self.cache_size_bytes = Gauge(
            "cache_size_bytes",
            "Cache size in bytes",
            ["cache_type"],
        )

        # ====================================================================
        # 系統指標
        # ====================================================================

        # 應用資訊
        self.app_info = Info(
            "app",
            "Application information",
        )

        # 健康狀態
        self.health_status = Gauge(
            "health_status",
            "Health status (1=healthy, 0.5=degraded, 0=unhealthy)",
            ["component"],
        )

        # 錯誤計數
        self.errors_total = Counter(
            "errors_total",
            "Total errors",
            ["error_type", "component"],
        )

        logger.info("Prometheus 指標初始化完成")

    # ========================================================================
    # HTTP 請求追蹤
    # ========================================================================

    def track_request(
        self,
        method: str,
        endpoint: str,
        status_code: int,
        duration: float,
        request_size: Optional[int] = None,
        response_size: Optional[int] = None,
    ):
        """
        追蹤 HTTP 請求

        Args:
            method: HTTP 方法
            endpoint: 端點路徑
            status_code: 狀態碼
            duration: 請求時長（秒）
            request_size: 請求大小（字節）
            response_size: 回覆大小（字節）
        """
        # 計數
        self.http_requests_total.labels(
            method=method, endpoint=endpoint, status=status_code
        ).inc()

        # 延遲
        self.http_request_duration_seconds.labels(
            method=method, endpoint=endpoint
        ).observe(duration)

        # 大小
        if request_size:
            self.http_request_size_bytes.labels(
                method=method, endpoint=endpoint
            ).observe(request_size)

        if response_size:
            self.http_response_size_bytes.labels(
                method=method, endpoint=endpoint
            ).observe(response_size)

    # ========================================================================
    # 模型推理追蹤
    # ========================================================================

    def track_inference(
        self,
        model_name: str,
        duration: float,
        tokens: Optional[int] = None,
        success: bool = True,
    ):
        """
        追蹤模型推理

        Args:
            model_name: 模型名稱
            duration: 推理時長（秒）
            tokens: 生成的 token 數
            success: 是否成功
        """
        # 計數
        status = "success" if success else "error"
        self.model_inferences_total.labels(model_name=model_name, status=status).inc()

        # 延遲
        self.model_inference_duration_seconds.labels(model_name=model_name).observe(
            duration
        )

        # Token 速度
        if tokens and duration > 0:
            tokens_per_sec = tokens / duration
            self.model_tokens_per_second.labels(model_name=model_name).observe(
                tokens_per_sec
            )

    # ========================================================================
    # 快取追蹤
    # ========================================================================

    def track_cache_hit(self, cache_type: str = "default"):
        """追蹤快取命中"""
        self.cache_hits_total.labels(cache_type=cache_type).inc()

    def track_cache_miss(self, cache_type: str = "default"):
        """追蹤快取未命中"""
        self.cache_misses_total.labels(cache_type=cache_type).inc()

    def set_cache_size(self, cache_type: str, size_bytes: int):
        """設置快取大小"""
        self.cache_size_bytes.labels(cache_type=cache_type).set(size_bytes)

    # ========================================================================
    # 健康狀態
    # ========================================================================

    def update_health_status(self, component: str, status: str):
        """
        更新健康狀態

        Args:
            component: 組件名稱
            status: 狀態（healthy/degraded/unhealthy）
        """
        status_map = {"healthy": 1.0, "degraded": 0.5, "unhealthy": 0.0}

        value = status_map.get(status.lower(), 0.0)
        self.health_status.labels(component=component).set(value)

    # ========================================================================
    # 錯誤追蹤
    # ========================================================================

    def track_error(self, error_type: str, component: str = "unknown"):
        """追蹤錯誤"""
        self.errors_total.labels(error_type=error_type, component=component).inc()


# ============================================================================
# 全局實例
# ============================================================================

_metrics: Optional[PrometheusMetrics] = None


def get_metrics() -> PrometheusMetrics:
    """獲取全局指標實例"""
    global _metrics
    if _metrics is None:
        _metrics = PrometheusMetrics()
    return _metrics


# ============================================================================
# FastAPI 整合
# ============================================================================


def setup_prometheus_metrics(app):
    """
    設置 Prometheus 指標端點

    Args:
        app: FastAPI 應用

    Example:
        ```python
        from fastapi import FastAPI
        from src.medical_chatbot.monitoring import setup_prometheus_metrics

        app = FastAPI()
        setup_prometheus_metrics(app)
        ```
    """
    metrics = get_metrics()

    # 設置應用資訊
    import sys
    from pathlib import Path

    metrics.app_info.info(
        {
            "app_name": "medical_chatbot",
            "version": "1.0.0",
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        }
    )

    # 添加指標端點
    @app.get("/metrics")
    async def metrics_endpoint():
        """Prometheus 指標端點"""
        return Response(
            content=generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST
        )

    # 添加中間件
    from fastapi import Request
    import time

    @app.middleware("http")
    async def prometheus_middleware(request: Request, call_next):
        """Prometheus 中間件"""
        # 跳過 /metrics 端點本身
        if request.url.path == "/metrics":
            return await call_next(request)

        # 記錄開始時間
        start_time = time.time()

        # 處理請求
        response = await call_next(request)

        # 計算時長
        duration = time.time() - start_time

        # 追蹤請求
        metrics.track_request(
            method=request.method,
            endpoint=request.url.path,
            status_code=response.status_code,
            duration=duration,
        )

        return response

    logger.info("Prometheus 指標已設置: /metrics")


# ============================================================================
# 裝飾器
# ============================================================================


def track_request(func: Callable) -> Callable:
    """
    追蹤請求裝飾器

    Example:
        ```python
        from src.medical_chatbot.monitoring import track_request

        @app.get("/api/data")
        @track_request
        async def get_data():
            return {"data": "value"}
        ```
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()

        try:
            result = await func(*args, **kwargs)
            success = True
            return result

        except Exception as e:
            success = False
            raise

        finally:
            duration = time.time() - start_time

            # 追蹤（這裡需要從 request 獲取資訊）
            # 實際使用時應該從 FastAPI 的依賴注入獲取

    return wrapper


def track_model_inference(model_name: str):
    """
    追蹤模型推理裝飾器

    Args:
        model_name: 模型名稱

    Example:
        ```python
        from src.medical_chatbot.monitoring import track_model_inference

        @track_model_inference("TAIDE-LX-8B")
        def generate(prompt):
            return model.generate(prompt)
        ```
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            metrics = get_metrics()
            start_time = time.time()

            try:
                result = await func(*args, **kwargs)
                success = True
                return result

            except Exception as e:
                success = False
                raise

            finally:
                duration = time.time() - start_time
                metrics.track_inference(
                    model_name=model_name, duration=duration, success=success
                )

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            metrics = get_metrics()
            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                success = True
                return result

            except Exception as e:
                success = False
                raise

            finally:
                duration = time.time() - start_time
                metrics.track_inference(
                    model_name=model_name, duration=duration, success=success
                )

        import inspect

        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator
