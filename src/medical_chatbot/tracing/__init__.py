"""
分佈式追蹤模組

提供 OpenTelemetry 追蹤功能。
"""

from medical_chatbot.tracing.tracer import (
    Tracer,
    TracerConfig,
    setup_tracing,
    get_tracer,
    create_span,
    trace_function,
)
from medical_chatbot.tracing.fastapi_middleware import (
    TracingMiddleware,
    setup_fastapi_tracing,
)
from medical_chatbot.tracing.context import (
    get_current_trace_id,
    get_current_span_id,
    inject_context,
    extract_context,
)

__all__ = [
    # Tracer
    "Tracer",
    "TracerConfig",
    "setup_tracing",
    "get_tracer",
    "create_span",
    "trace_function",
    # Middleware
    "TracingMiddleware",
    "setup_fastapi_tracing",
    # Context
    "get_current_trace_id",
    "get_current_span_id",
    "inject_context",
    "extract_context",
]
