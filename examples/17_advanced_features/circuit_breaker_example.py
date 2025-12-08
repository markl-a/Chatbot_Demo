"""
斷路器模式示範

展示如何使用斷路器提高系統彈性。
"""

import asyncio
import random
import time

from medical_chatbot.resilience import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
    CircuitBreakerOpen,
    circuit_breaker,
    retry,
    retry_async,
    timeout,
    timeout_async,
)


# ============================================================================
# 斷路器基本用法
# ============================================================================


def circuit_breaker_basic_example():
    """斷路器基本用法示範"""
    print("=" * 60)
    print("斷路器基本用法示範")
    print("=" * 60)

    # 創建斷路器配置
    config = CircuitBreakerConfig(
        failure_threshold=3,      # 連續 3 次失敗後開啟
        success_threshold=2,      # 半開狀態 2 次成功後關閉
        timeout=5.0,              # 開啟狀態 5 秒後進入半開
        half_open_max_calls=2,    # 半開狀態最多 2 個並發請求
    )

    # 創建斷路器
    cb = CircuitBreaker("external-service", config)

    print(f"初始狀態: {cb.state.value}")

    # 模擬失敗
    for i in range(3):
        try:
            def failing_operation():
                raise ConnectionError("服務不可用")

            cb.call(failing_operation)
        except ConnectionError:
            print(f"第 {i + 1} 次失敗")

    print(f"當前狀態: {cb.state.value}")  # 應該是 OPEN

    # 嘗試在開啟狀態下調用
    try:
        cb.call(lambda: "success")
    except CircuitBreakerOpen as e:
        print(f"斷路器阻止了請求: {e}")

    # 獲取統計
    stats = cb.get_stats()
    print(f"\n統計信息:")
    print(f"  總調用: {stats['total_calls']}")
    print(f"  總成功: {stats['total_successes']}")
    print(f"  總失敗: {stats['total_failures']}")
    print(f"  總拒絕: {stats['total_rejections']}")


# ============================================================================
# 斷路器裝飾器
# ============================================================================


def decorator_example():
    """裝飾器用法示範"""
    print("\n" + "=" * 60)
    print("斷路器裝飾器示範")
    print("=" * 60)

    call_count = 0

    @circuit_breaker(
        name="api-call",
        failure_threshold=2,
        timeout=1.0,
    )
    def unstable_api_call():
        """模擬不穩定的 API 調用"""
        nonlocal call_count
        call_count += 1

        if random.random() < 0.7:  # 70% 失敗率
            raise ConnectionError("API 暫時不可用")
        return "success"

    # 多次調用
    for i in range(5):
        try:
            result = unstable_api_call()
            print(f"調用 {i + 1}: 成功")
        except ConnectionError as e:
            print(f"調用 {i + 1}: 失敗 - {e}")
        except CircuitBreakerOpen as e:
            print(f"調用 {i + 1}: 被斷路器阻止")

    print(f"\n實際執行次數: {call_count}")


# ============================================================================
# 帶降級的斷路器
# ============================================================================


def fallback_example():
    """降級功能示範"""
    print("\n" + "=" * 60)
    print("斷路器降級示範")
    print("=" * 60)

    def fallback_response(*args, **kwargs):
        """降級響應"""
        return {"status": "fallback", "message": "服務暫時不可用，使用快取數據"}

    @circuit_breaker(
        name="service-with-fallback",
        failure_threshold=2,
        fallback=fallback_response,
    )
    def call_service():
        raise ConnectionError("服務不可用")

    # 調用直到斷路器開啟
    for i in range(4):
        result = call_service()
        print(f"調用 {i + 1}: {result}")


# ============================================================================
# 重試機制
# ============================================================================


def retry_example():
    """重試機制示範"""
    print("\n" + "=" * 60)
    print("重試機制示範")
    print("=" * 60)

    attempt_count = 0

    @retry(
        max_retries=3,
        initial_delay=0.5,
        backoff_factor=2.0,
        jitter=True,
        retry_exceptions=[ConnectionError, TimeoutError],
    )
    def flaky_operation():
        """模擬不穩定的操作"""
        nonlocal attempt_count
        attempt_count += 1
        print(f"  嘗試第 {attempt_count} 次...")

        if attempt_count < 3:
            raise ConnectionError("暫時失敗")
        return "成功！"

    try:
        result = flaky_operation()
        print(f"結果: {result}")
    except ConnectionError as e:
        print(f"最終失敗: {e}")


# ============================================================================
# 超時處理
# ============================================================================


def timeout_example():
    """超時處理示範"""
    print("\n" + "=" * 60)
    print("超時處理示範")
    print("=" * 60)

    @timeout(seconds=1.0, operation_name="慢操作")
    def slow_operation():
        """模擬慢操作"""
        time.sleep(2.0)  # 會超時
        return "完成"

    try:
        result = slow_operation()
        print(f"結果: {result}")
    except Exception as e:
        print(f"超時: {e}")


# ============================================================================
# 異步斷路器
# ============================================================================


async def async_example():
    """異步斷路器示範"""
    print("\n" + "=" * 60)
    print("異步斷路器示範")
    print("=" * 60)

    @circuit_breaker(name="async-service", failure_threshold=2)
    async def async_service_call():
        """模擬異步服務調用"""
        await asyncio.sleep(0.1)
        if random.random() < 0.5:
            raise ConnectionError("異步服務失敗")
        return "async success"

    @retry_async(max_retries=2, initial_delay=0.2)
    async def retry_async_call():
        """帶重試的異步調用"""
        if random.random() < 0.7:
            raise ConnectionError("需要重試")
        return "重試成功"

    # 測試異步斷路器
    for i in range(4):
        try:
            result = await async_service_call()
            print(f"異步調用 {i + 1}: {result}")
        except (ConnectionError, CircuitBreakerOpen) as e:
            print(f"異步調用 {i + 1}: {type(e).__name__}")

    # 測試異步重試
    print("\n異步重試測試:")
    try:
        result = await retry_async_call()
        print(f"結果: {result}")
    except ConnectionError as e:
        print(f"最終失敗: {e}")


# ============================================================================
# 狀態變更回調
# ============================================================================


def callback_example():
    """狀態變更回調示範"""
    print("\n" + "=" * 60)
    print("狀態變更回調示範")
    print("=" * 60)

    config = CircuitBreakerConfig(failure_threshold=2, timeout=1.0)
    cb = CircuitBreaker("callback-demo", config)

    # 設置狀態變更回調
    def on_state_change(old_state, new_state):
        print(f"  狀態變更: {old_state.value} -> {new_state.value}")

    cb.on_state_change = on_state_change

    # 設置失敗回調
    def on_failure(exception):
        print(f"  失敗: {exception}")

    cb.on_failure = on_failure

    # 設置成功回調
    def on_success():
        print("  成功!")

    cb.on_success = on_success

    # 觸發狀態變更
    print("觸發失敗...")
    for _ in range(2):
        try:
            cb.call(lambda: (_ for _ in ()).throw(ValueError("錯誤")))
        except ValueError:
            pass

    print("\n等待超時...")
    time.sleep(1.1)

    print("嘗試恢復...")
    try:
        if cb.can_execute():
            cb.record_success()
            cb.record_success()
    except Exception:
        pass


# ============================================================================
# 組合使用
# ============================================================================


def combined_example():
    """組合使用示範"""
    print("\n" + "=" * 60)
    print("組合使用示範（斷路器 + 重試 + 超時）")
    print("=" * 60)

    @circuit_breaker(name="combined", failure_threshold=3)
    @retry(max_retries=2, initial_delay=0.1)
    @timeout(seconds=2.0, operation_name="組合操作")
    def combined_operation():
        """組合了所有彈性模式的操作"""
        # 模擬各種情況
        chance = random.random()
        if chance < 0.3:
            raise ConnectionError("連接失敗")
        elif chance < 0.5:
            time.sleep(3.0)  # 超時
        return "組合操作成功！"

    for i in range(5):
        try:
            result = combined_operation()
            print(f"調用 {i + 1}: {result}")
        except Exception as e:
            print(f"調用 {i + 1}: {type(e).__name__} - {e}")


# ============================================================================
# 主程序
# ============================================================================


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Medical Chatbot 彈性模式示範")
    print("=" * 60 + "\n")

    circuit_breaker_basic_example()
    decorator_example()
    fallback_example()
    retry_example()
    timeout_example()
    asyncio.run(async_example())
    callback_example()
    combined_example()

    print("\n" + "=" * 60)
    print("示範完成！")
    print("=" * 60)
