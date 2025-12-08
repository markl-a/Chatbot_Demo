"""
斷路器測試

測試斷路器模式功能。
"""

import asyncio
import pytest
import time
from unittest.mock import MagicMock, patch

from medical_chatbot.resilience.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
    CircuitBreakerOpen,
)


# ============================================================================
# CircuitBreakerConfig 測試
# ============================================================================


class TestCircuitBreakerConfig:
    """斷路器配置測試"""

    def test_default_config(self):
        """測試默認配置"""
        config = CircuitBreakerConfig()

        assert config.failure_threshold == 5
        assert config.success_threshold == 3
        assert config.timeout == 30.0
        assert config.half_open_max_calls == 3

    def test_custom_config(self):
        """測試自定義配置"""
        config = CircuitBreakerConfig(
            failure_threshold=10,
            success_threshold=5,
            timeout=60.0,
            half_open_max_calls=5,
        )

        assert config.failure_threshold == 10
        assert config.success_threshold == 5
        assert config.timeout == 60.0
        assert config.half_open_max_calls == 5


# ============================================================================
# CircuitBreaker 測試
# ============================================================================


class TestCircuitBreaker:
    """斷路器測試"""

    @pytest.fixture
    def circuit_breaker(self):
        """創建斷路器"""
        config = CircuitBreakerConfig(
            failure_threshold=3,
            success_threshold=2,
            timeout=1.0,  # 短超時以便測試
        )
        return CircuitBreaker("test-service", config)

    def test_initial_state(self, circuit_breaker):
        """測試初始狀態"""
        assert circuit_breaker.state == CircuitState.CLOSED
        assert circuit_breaker.is_closed is True
        assert circuit_breaker.failure_count == 0

    def test_success_in_closed_state(self, circuit_breaker):
        """測試關閉狀態下的成功"""
        circuit_breaker.record_success()

        assert circuit_breaker.state == CircuitState.CLOSED
        assert circuit_breaker.success_count == 1

    def test_failure_in_closed_state(self, circuit_breaker):
        """測試關閉狀態下的失敗"""
        circuit_breaker.record_failure()

        assert circuit_breaker.state == CircuitState.CLOSED
        assert circuit_breaker.failure_count == 1

    def test_open_after_threshold(self, circuit_breaker):
        """測試達到閾值後開啟"""
        # 記錄失敗直到達到閾值
        for _ in range(3):
            circuit_breaker.record_failure()

        assert circuit_breaker.state == CircuitState.OPEN
        assert circuit_breaker.is_open is True

    def test_half_open_after_timeout(self, circuit_breaker):
        """測試超時後進入半開狀態"""
        # 開啟斷路器
        for _ in range(3):
            circuit_breaker.record_failure()

        assert circuit_breaker.state == CircuitState.OPEN

        # 等待超時
        time.sleep(1.1)

        # 檢查是否可以嘗試
        assert circuit_breaker.can_execute() is True
        assert circuit_breaker.state == CircuitState.HALF_OPEN

    def test_close_from_half_open(self, circuit_breaker):
        """測試從半開狀態關閉"""
        # 開啟斷路器
        for _ in range(3):
            circuit_breaker.record_failure()

        # 等待超時
        time.sleep(1.1)
        circuit_breaker.can_execute()  # 進入半開狀態

        # 記錄成功
        circuit_breaker.record_success()
        circuit_breaker.record_success()

        assert circuit_breaker.state == CircuitState.CLOSED

    def test_reopen_from_half_open(self, circuit_breaker):
        """測試從半開狀態重新開啟"""
        # 開啟斷路器
        for _ in range(3):
            circuit_breaker.record_failure()

        # 等待超時
        time.sleep(1.1)
        circuit_breaker.can_execute()  # 進入半開狀態

        # 記錄失敗
        circuit_breaker.record_failure()

        assert circuit_breaker.state == CircuitState.OPEN

    def test_cannot_execute_when_open(self, circuit_breaker):
        """測試開啟狀態下不能執行"""
        # 開啟斷路器
        for _ in range(3):
            circuit_breaker.record_failure()

        assert circuit_breaker.can_execute() is False

    def test_stats(self, circuit_breaker):
        """測試統計信息"""
        circuit_breaker.record_success()
        circuit_breaker.record_failure()

        stats = circuit_breaker.get_stats()

        assert stats["state"] == "closed"
        assert stats["failure_count"] == 1
        assert stats["success_count"] == 1
        assert stats["name"] == "test-service"

    def test_reset(self, circuit_breaker):
        """測試重置"""
        # 記錄一些狀態
        circuit_breaker.record_failure()
        circuit_breaker.record_failure()

        circuit_breaker.reset()

        assert circuit_breaker.state == CircuitState.CLOSED
        assert circuit_breaker.failure_count == 0
        assert circuit_breaker.success_count == 0

    def test_context_manager_success(self, circuit_breaker):
        """測試上下文管理器（成功）"""

        def operation():
            return "success"

        result = circuit_breaker.call(operation)

        assert result == "success"
        assert circuit_breaker.success_count == 1

    def test_context_manager_failure(self, circuit_breaker):
        """測試上下文管理器（失敗）"""

        def operation():
            raise ValueError("test error")

        with pytest.raises(ValueError):
            circuit_breaker.call(operation)

        assert circuit_breaker.failure_count == 1

    def test_call_when_open(self, circuit_breaker):
        """測試開啟狀態下調用"""
        # 開啟斷路器
        for _ in range(3):
            circuit_breaker.record_failure()

        def operation():
            return "success"

        with pytest.raises(CircuitBreakerOpen):
            circuit_breaker.call(operation)

    @pytest.mark.asyncio
    async def test_async_call_success(self, circuit_breaker):
        """測試異步調用（成功）"""

        async def async_operation():
            return "async success"

        result = await circuit_breaker.call_async(async_operation)

        assert result == "async success"
        assert circuit_breaker.success_count == 1

    @pytest.mark.asyncio
    async def test_async_call_failure(self, circuit_breaker):
        """測試異步調用（失敗）"""

        async def async_operation():
            raise ValueError("async error")

        with pytest.raises(ValueError):
            await circuit_breaker.call_async(async_operation)

        assert circuit_breaker.failure_count == 1

    def test_excluded_exceptions(self):
        """測試排除的異常"""
        config = CircuitBreakerConfig(
            failure_threshold=3,
            excluded_exceptions=[ValueError],
        )
        cb = CircuitBreaker("test", config)

        def operation():
            raise ValueError("excluded")

        with pytest.raises(ValueError):
            cb.call(operation)

        # ValueError 被排除，不應該計入失敗
        assert cb.failure_count == 0

    def test_on_state_change_callback(self, circuit_breaker):
        """測試狀態變更回調"""
        states_received = []

        def on_state_change(old_state, new_state):
            states_received.append((old_state, new_state))

        circuit_breaker.on_state_change = on_state_change

        # 觸發狀態變更
        for _ in range(3):
            circuit_breaker.record_failure()

        assert len(states_received) == 1
        assert states_received[0] == (CircuitState.CLOSED, CircuitState.OPEN)


# ============================================================================
# 裝飾器測試
# ============================================================================


class TestCircuitBreakerDecorator:
    """斷路器裝飾器測試"""

    def test_decorator_success(self):
        """測試裝飾器（成功）"""
        from medical_chatbot.resilience.circuit_breaker import circuit_breaker

        @circuit_breaker(name="test-decorator", failure_threshold=3)
        def my_function():
            return "success"

        result = my_function()
        assert result == "success"

    def test_decorator_failure(self):
        """測試裝飾器（失敗）"""
        from medical_chatbot.resilience.circuit_breaker import circuit_breaker

        call_count = 0

        @circuit_breaker(name="test-decorator-fail", failure_threshold=2, timeout=0.1)
        def failing_function():
            nonlocal call_count
            call_count += 1
            raise ValueError("always fails")

        # 前兩次調用會失敗並開啟斷路器
        for _ in range(2):
            with pytest.raises(ValueError):
                failing_function()

        # 第三次調用應該被斷路器阻止
        with pytest.raises(CircuitBreakerOpen):
            failing_function()

        # 只有前兩次實際執行了函數
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_async_decorator(self):
        """測試異步裝飾器"""
        from medical_chatbot.resilience.circuit_breaker import circuit_breaker

        @circuit_breaker(name="test-async-decorator")
        async def async_function():
            return "async result"

        result = await async_function()
        assert result == "async result"
