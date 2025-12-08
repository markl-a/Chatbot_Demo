"""
追蹤測試

測試 OpenTelemetry 追蹤功能。
"""

import pytest
from unittest.mock import MagicMock, patch

from medical_chatbot.tracing.tracer import (
    Tracer,
    TracerConfig,
    trace_function,
)
from medical_chatbot.tracing.context import (
    get_current_trace_id,
    get_current_span_id,
    inject_context,
    TraceContext,
)


# ============================================================================
# TracerConfig 測試
# ============================================================================


class TestTracerConfig:
    """追蹤器配置測試"""

    def test_default_config(self):
        """測試默認配置"""
        config = TracerConfig()

        assert config.service_name == "medical-chatbot"
        assert config.service_version == "0.2.0"
        assert config.environment == "development"
        assert config.exporter_type == "console"
        assert config.enabled is True

    def test_custom_config(self):
        """測試自定義配置"""
        config = TracerConfig(
            service_name="custom-service",
            service_version="1.0.0",
            environment="production",
            exporter_type="otlp",
            otlp_endpoint="http://collector:4317",
            sample_rate=0.5,
        )

        assert config.service_name == "custom-service"
        assert config.service_version == "1.0.0"
        assert config.environment == "production"
        assert config.exporter_type == "otlp"
        assert config.sample_rate == 0.5


# ============================================================================
# Tracer 測試（不依賴 OpenTelemetry）
# ============================================================================


class TestTracerWithoutOTel:
    """追蹤器測試（OpenTelemetry 禁用）"""

    def test_disabled_tracer(self):
        """測試禁用的追蹤器"""
        config = TracerConfig(enabled=False)
        tracer = Tracer(config)

        assert tracer.is_enabled is False

    def test_disabled_span_context(self):
        """測試禁用追蹤器的 span 上下文"""
        config = TracerConfig(enabled=False)
        tracer = Tracer(config)

        with tracer.start_span("test-span") as span:
            assert span is None

    def test_disabled_get_trace_id(self):
        """測試禁用追蹤器獲取追蹤 ID"""
        config = TracerConfig(enabled=False)
        tracer = Tracer(config)

        assert tracer.get_trace_id() is None
        assert tracer.get_span_id() is None


# ============================================================================
# TraceContext 測試
# ============================================================================


class TestTraceContext:
    """追蹤上下文測試"""

    def test_inject_to_headers(self):
        """測試注入到標頭"""
        context = TraceContext()
        headers = context.inject_to_headers()

        # 即使沒有活動的追蹤，也應該返回字典
        assert isinstance(headers, dict)

    def test_inject_to_existing_headers(self):
        """測試注入到現有標頭"""
        context = TraceContext()
        existing_headers = {"Authorization": "Bearer token"}
        headers = context.inject_to_headers(existing_headers)

        assert "Authorization" in headers

    def test_get_current_context(self):
        """測試獲取當前上下文"""
        context = TraceContext.get_current_context()

        assert "trace_id" in context
        assert "span_id" in context


# ============================================================================
# trace_function 裝飾器測試
# ============================================================================


class TestTraceFunction:
    """函數追蹤裝飾器測試"""

    def test_sync_function_decorator(self):
        """測試同步函數裝飾器"""

        @trace_function(name="test-sync")
        def sync_function(x, y):
            return x + y

        result = sync_function(1, 2)
        assert result == 3

    @pytest.mark.asyncio
    async def test_async_function_decorator(self):
        """測試異步函數裝飾器"""

        @trace_function(name="test-async")
        async def async_function(x, y):
            return x + y

        result = await async_function(1, 2)
        assert result == 3

    def test_decorator_without_name(self):
        """測試不帶名稱的裝飾器"""

        @trace_function()
        def my_function():
            return "result"

        result = my_function()
        assert result == "result"

    def test_decorator_with_attributes(self):
        """測試帶屬性的裝飾器"""

        @trace_function(
            name="test-with-attrs",
            attributes={"custom_attr": "value"},
        )
        def function_with_attrs():
            return "result"

        result = function_with_attrs()
        assert result == "result"


# ============================================================================
# Context 函數測試
# ============================================================================


class TestContextFunctions:
    """上下文函數測試"""

    def test_get_current_trace_id_no_span(self):
        """測試無活動 span 時獲取追蹤 ID"""
        trace_id = get_current_trace_id()
        # 可能是 None（如果沒有 OpenTelemetry）或有值
        assert trace_id is None or isinstance(trace_id, str)

    def test_get_current_span_id_no_span(self):
        """測試無活動 span 時獲取 span ID"""
        span_id = get_current_span_id()
        assert span_id is None or isinstance(span_id, str)

    def test_inject_context_to_carrier(self):
        """測試注入上下文到載體"""
        carrier = {}
        result = inject_context(carrier)

        assert isinstance(result, dict)
