"""
追蹤上下文

管理追蹤上下文的傳播。
"""

from typing import Any, Dict, Optional

from loguru import logger

try:
    from opentelemetry import trace
    from opentelemetry.propagate import extract, inject
    from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

    OPENTELEMETRY_AVAILABLE = True
except ImportError:
    OPENTELEMETRY_AVAILABLE = False


def get_current_trace_id() -> Optional[str]:
    """
    獲取當前追蹤 ID

    Returns:
        追蹤 ID 字符串，或 None
    """
    if not OPENTELEMETRY_AVAILABLE:
        return None

    span = trace.get_current_span()
    if span:
        context = span.get_span_context()
        if context.is_valid:
            return format(context.trace_id, '032x')
    return None


def get_current_span_id() -> Optional[str]:
    """
    獲取當前 Span ID

    Returns:
        Span ID 字符串，或 None
    """
    if not OPENTELEMETRY_AVAILABLE:
        return None

    span = trace.get_current_span()
    if span:
        context = span.get_span_context()
        if context.is_valid:
            return format(context.span_id, '016x')
    return None


def inject_context(carrier: Dict[str, Any]) -> Dict[str, Any]:
    """
    將當前追蹤上下文注入到載體（如 HTTP 標頭）

    Args:
        carrier: 載體字典

    Returns:
        包含追蹤上下文的載體
    """
    if not OPENTELEMETRY_AVAILABLE:
        return carrier

    inject(carrier)
    return carrier


def extract_context(carrier: Dict[str, Any]):
    """
    從載體中提取追蹤上下文

    Args:
        carrier: 載體字典

    Returns:
        OpenTelemetry 上下文
    """
    if not OPENTELEMETRY_AVAILABLE:
        return None

    return extract(carrier)


def get_trace_context_headers() -> Dict[str, str]:
    """
    獲取追蹤上下文 HTTP 標頭

    Returns:
        包含 traceparent 和 tracestate 的字典
    """
    headers = {}
    inject_context(headers)
    return headers


class TraceContext:
    """
    追蹤上下文管理器

    用於在不同服務間傳遞追蹤上下文。
    """

    def __init__(self):
        self.propagator = TraceContextTextMapPropagator() if OPENTELEMETRY_AVAILABLE else None

    def inject_to_headers(self, headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """
        注入追蹤上下文到 HTTP 標頭

        Args:
            headers: 現有標頭（可選）

        Returns:
            包含追蹤上下文的標頭
        """
        headers = headers or {}
        if self.propagator:
            self.propagator.inject(headers)
        return headers

    def extract_from_headers(self, headers: Dict[str, str]):
        """
        從 HTTP 標頭提取追蹤上下文

        Args:
            headers: HTTP 標頭

        Returns:
            OpenTelemetry 上下文
        """
        if self.propagator:
            return self.propagator.extract(headers)
        return None

    @staticmethod
    def get_current_context() -> Dict[str, Optional[str]]:
        """
        獲取當前追蹤上下文信息

        Returns:
            包含 trace_id 和 span_id 的字典
        """
        return {
            "trace_id": get_current_trace_id(),
            "span_id": get_current_span_id(),
        }


# 全局上下文管理器
_trace_context = TraceContext()


def get_trace_context() -> TraceContext:
    """獲取全局追蹤上下文管理器"""
    return _trace_context
