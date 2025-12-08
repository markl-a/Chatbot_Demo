"""
追蹤器

OpenTelemetry 追蹤核心功能。
"""

import os
from contextlib import contextmanager
from dataclasses import dataclass, field
from functools import wraps
from typing import Any, Callable, Dict, Optional

from loguru import logger

try:
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.exporter.jaeger.thrift import JaegerExporter
    from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
    from opentelemetry.sdk.trace import TracerProvider, Span
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    from opentelemetry.trace import Status, StatusCode
    from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

    OPENTELEMETRY_AVAILABLE = True
except ImportError:
    OPENTELEMETRY_AVAILABLE = False
    logger.warning("OpenTelemetry 未安裝，追蹤功能將被禁用")


@dataclass
class TracerConfig:
    """追蹤器配置"""
    service_name: str = "medical-chatbot"
    service_version: str = "0.2.0"
    environment: str = "development"

    # 導出器設置
    exporter_type: str = "console"  # console, otlp, jaeger
    otlp_endpoint: str = "http://localhost:4317"
    jaeger_agent_host: str = "localhost"
    jaeger_agent_port: int = 6831

    # 採樣設置
    sample_rate: float = 1.0  # 1.0 = 100%

    # 其他設置
    enabled: bool = True
    debug: bool = False

    # 額外資源屬性
    extra_attributes: Dict[str, str] = field(default_factory=dict)


class Tracer:
    """
    OpenTelemetry 追蹤器

    支援：
    - 多種導出器（Console, OTLP, Jaeger）
    - Span 創建和管理
    - 上下文傳播
    - 自動追蹤裝飾器
    """

    def __init__(self, config: Optional[TracerConfig] = None):
        """
        初始化追蹤器

        Args:
            config: 追蹤器配置
        """
        self.config = config or TracerConfig()
        self._tracer = None
        self._provider = None
        self._initialized = False

        if not OPENTELEMETRY_AVAILABLE:
            logger.warning("OpenTelemetry 不可用，追蹤功能已禁用")
            return

        if self.config.enabled:
            self._initialize()

    def _initialize(self):
        """初始化追蹤器"""
        if not OPENTELEMETRY_AVAILABLE:
            return

        try:
            # 創建資源
            resource_attributes = {
                SERVICE_NAME: self.config.service_name,
                SERVICE_VERSION: self.config.service_version,
                "deployment.environment": self.config.environment,
            }
            resource_attributes.update(self.config.extra_attributes)

            resource = Resource.create(resource_attributes)

            # 創建追蹤器提供者
            self._provider = TracerProvider(resource=resource)

            # 創建導出器
            exporter = self._create_exporter()
            if exporter:
                processor = BatchSpanProcessor(exporter)
                self._provider.add_span_processor(processor)

            # 設置全局追蹤器提供者
            trace.set_tracer_provider(self._provider)

            # 獲取追蹤器
            self._tracer = trace.get_tracer(
                self.config.service_name,
                self.config.service_version,
            )

            self._initialized = True
            logger.info(
                f"OpenTelemetry 追蹤器初始化完成 "
                f"(服務: {self.config.service_name}, 導出器: {self.config.exporter_type})"
            )

        except Exception as e:
            logger.error(f"追蹤器初始化失敗: {e}")
            self._initialized = False

    def _create_exporter(self):
        """創建導出器"""
        exporter_type = self.config.exporter_type.lower()

        if exporter_type == "console":
            return ConsoleSpanExporter()

        elif exporter_type == "otlp":
            return OTLPSpanExporter(
                endpoint=self.config.otlp_endpoint,
                insecure=True,
            )

        elif exporter_type == "jaeger":
            return JaegerExporter(
                agent_host_name=self.config.jaeger_agent_host,
                agent_port=self.config.jaeger_agent_port,
            )

        else:
            logger.warning(f"未知的導出器類型: {exporter_type}，使用 Console")
            return ConsoleSpanExporter()

    @property
    def is_enabled(self) -> bool:
        """追蹤是否啟用"""
        return self._initialized and self.config.enabled

    @contextmanager
    def start_span(
        self,
        name: str,
        attributes: Optional[Dict[str, Any]] = None,
        kind: Optional[Any] = None,
    ):
        """
        開始一個新的 Span

        Args:
            name: Span 名稱
            attributes: 屬性
            kind: Span 類型

        Yields:
            Span 實例
        """
        if not self.is_enabled:
            yield None
            return

        span_kind = kind
        if span_kind is None and OPENTELEMETRY_AVAILABLE:
            span_kind = trace.SpanKind.INTERNAL

        with self._tracer.start_as_current_span(
            name,
            kind=span_kind,
            attributes=attributes,
        ) as span:
            try:
                yield span
            except Exception as e:
                if span and OPENTELEMETRY_AVAILABLE:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                raise

    def start_span_no_context(
        self,
        name: str,
        attributes: Optional[Dict[str, Any]] = None,
    ):
        """
        開始一個新的 Span（不設為當前上下文）

        Args:
            name: Span 名稱
            attributes: 屬性

        Returns:
            Span 實例
        """
        if not self.is_enabled:
            return None

        return self._tracer.start_span(name, attributes=attributes)

    def add_event(
        self,
        name: str,
        attributes: Optional[Dict[str, Any]] = None,
    ):
        """
        添加事件到當前 Span

        Args:
            name: 事件名稱
            attributes: 事件屬性
        """
        if not self.is_enabled:
            return

        span = trace.get_current_span()
        if span:
            span.add_event(name, attributes=attributes)

    def set_attribute(self, key: str, value: Any):
        """
        設置當前 Span 的屬性

        Args:
            key: 屬性鍵
            value: 屬性值
        """
        if not self.is_enabled:
            return

        span = trace.get_current_span()
        if span:
            span.set_attribute(key, value)

    def set_status(self, status_code: str, description: str = ""):
        """
        設置當前 Span 的狀態

        Args:
            status_code: 狀態代碼 (ok, error)
            description: 描述
        """
        if not self.is_enabled or not OPENTELEMETRY_AVAILABLE:
            return

        span = trace.get_current_span()
        if span:
            code = StatusCode.OK if status_code.lower() == "ok" else StatusCode.ERROR
            span.set_status(Status(code, description))

    def record_exception(self, exception: Exception):
        """
        記錄異常到當前 Span

        Args:
            exception: 異常實例
        """
        if not self.is_enabled:
            return

        span = trace.get_current_span()
        if span:
            span.record_exception(exception)

    def get_current_span(self):
        """獲取當前 Span"""
        if not self.is_enabled:
            return None
        return trace.get_current_span()

    def get_trace_id(self) -> Optional[str]:
        """獲取當前追蹤 ID"""
        if not self.is_enabled:
            return None

        span = trace.get_current_span()
        if span:
            context = span.get_span_context()
            if context.is_valid:
                return format(context.trace_id, '032x')
        return None

    def get_span_id(self) -> Optional[str]:
        """獲取當前 Span ID"""
        if not self.is_enabled:
            return None

        span = trace.get_current_span()
        if span:
            context = span.get_span_context()
            if context.is_valid:
                return format(context.span_id, '016x')
        return None

    def shutdown(self):
        """關閉追蹤器"""
        if self._provider:
            self._provider.shutdown()
            logger.info("追蹤器已關閉")


# ============================================================================
# 全局實例和便捷函數
# ============================================================================

_tracer: Optional[Tracer] = None


def setup_tracing(config: Optional[TracerConfig] = None) -> Tracer:
    """
    設置全局追蹤器

    Args:
        config: 追蹤器配置

    Returns:
        Tracer 實例
    """
    global _tracer
    _tracer = Tracer(config)
    return _tracer


def get_tracer() -> Tracer:
    """獲取全局追蹤器"""
    global _tracer
    if _tracer is None:
        _tracer = Tracer()
    return _tracer


@contextmanager
def create_span(
    name: str,
    attributes: Optional[Dict[str, Any]] = None,
):
    """
    創建 Span（便捷函數）

    Args:
        name: Span 名稱
        attributes: 屬性

    Yields:
        Span 實例
    """
    tracer = get_tracer()
    with tracer.start_span(name, attributes=attributes) as span:
        yield span


def trace_function(
    name: Optional[str] = None,
    attributes: Optional[Dict[str, Any]] = None,
):
    """
    函數追蹤裝飾器

    Args:
        name: Span 名稱（默認使用函數名）
        attributes: 屬性

    Returns:
        裝飾器
    """

    def decorator(func: Callable) -> Callable:
        span_name = name or func.__name__

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            tracer = get_tracer()
            with tracer.start_span(span_name, attributes=attributes):
                return func(*args, **kwargs)

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            tracer = get_tracer()
            with tracer.start_span(span_name, attributes=attributes):
                return await func(*args, **kwargs)

        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator
