"""
彈性模組

提供斷路器、重試、超時等彈性模式。
"""

from medical_chatbot.resilience.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
    CircuitBreakerOpen,
    circuit_breaker,
    get_circuit_breaker,
)
from medical_chatbot.resilience.retry import (
    RetryConfig,
    retry,
    retry_async,
    exponential_backoff,
)
from medical_chatbot.resilience.timeout import (
    TimeoutConfig,
    timeout,
    timeout_async,
    TimeoutError as ResilienceTimeoutError,
)

__all__ = [
    # Circuit Breaker
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitState",
    "CircuitBreakerOpen",
    "circuit_breaker",
    "get_circuit_breaker",
    # Retry
    "RetryConfig",
    "retry",
    "retry_async",
    "exponential_backoff",
    # Timeout
    "TimeoutConfig",
    "timeout",
    "timeout_async",
    "ResilienceTimeoutError",
]
