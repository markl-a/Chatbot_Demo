"""
結構化日誌

提供統一的結構化日誌記錄功能。
"""

import json
import sys
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from loguru import logger


class LogLevel(str, Enum):
    """日誌級別"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class EventType(str, Enum):
    """事件類型"""
    # HTTP 相關
    HTTP_REQUEST = "http_request"
    HTTP_RESPONSE = "http_response"
    HTTP_ERROR = "http_error"

    # 資料庫相關
    DB_QUERY = "db_query"
    DB_ERROR = "db_error"
    DB_CONNECTION = "db_connection"

    # 快取相關
    CACHE_HIT = "cache_hit"
    CACHE_MISS = "cache_miss"
    CACHE_SET = "cache_set"
    CACHE_DELETE = "cache_delete"
    CACHE_ERROR = "cache_error"

    # 認證相關
    AUTH_LOGIN = "auth_login"
    AUTH_LOGOUT = "auth_logout"
    AUTH_FAILED = "auth_failed"
    AUTH_TOKEN_REFRESH = "auth_token_refresh"

    # 推理相關
    INFERENCE_START = "inference_start"
    INFERENCE_END = "inference_end"
    INFERENCE_ERROR = "inference_error"

    # 系統相關
    SYSTEM_STARTUP = "system_startup"
    SYSTEM_SHUTDOWN = "system_shutdown"
    SYSTEM_ERROR = "system_error"
    SYSTEM_WARNING = "system_warning"

    # WebSocket 相關
    WS_CONNECT = "ws_connect"
    WS_DISCONNECT = "ws_disconnect"
    WS_MESSAGE = "ws_message"
    WS_ERROR = "ws_error"

    # 業務相關
    BUSINESS_EVENT = "business_event"
    AUDIT_EVENT = "audit_event"

    # 通用
    CUSTOM = "custom"


@dataclass
class LogContext:
    """日誌上下文"""
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    service_name: str = "medical-chatbot"
    environment: str = "development"
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LogEvent:
    """結構化日誌事件"""
    timestamp: str
    level: str
    event_type: str
    message: str
    service: str
    context: Dict[str, Any] = field(default_factory=dict)
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[Dict[str, Any]] = None
    duration_ms: Optional[float] = None
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        result = {
            "timestamp": self.timestamp,
            "level": self.level,
            "event_type": self.event_type,
            "message": self.message,
            "service": self.service,
        }

        if self.context:
            result["context"] = self.context

        if self.data:
            result["data"] = self.data

        if self.error:
            result["error"] = self.error

        if self.duration_ms is not None:
            result["duration_ms"] = self.duration_ms

        if self.tags:
            result["tags"] = self.tags

        return result

    def to_json(self) -> str:
        """轉換為 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, default=str)


class StructuredLogger:
    """
    結構化日誌記錄器

    功能：
    - 統一的事件格式
    - 上下文傳播
    - 計時器
    - 多種事件類型支援
    """

    def __init__(
        self,
        service_name: str = "medical-chatbot",
        environment: str = "development",
        json_output: bool = True,
    ):
        """
        初始化結構化日誌記錄器

        Args:
            service_name: 服務名稱
            environment: 環境
            json_output: 是否輸出 JSON 格式
        """
        self.service_name = service_name
        self.environment = environment
        self.json_output = json_output

        # 當前上下文
        self._context = LogContext(
            service_name=service_name,
            environment=environment,
        )

    # ========================================================================
    # 上下文管理
    # ========================================================================

    def set_context(self, **kwargs):
        """設置上下文"""
        for key, value in kwargs.items():
            if hasattr(self._context, key):
                setattr(self._context, key, value)
            else:
                self._context.extra[key] = value

    def get_context(self) -> Dict[str, Any]:
        """獲取當前上下文"""
        ctx = {
            "request_id": self._context.request_id,
            "user_id": self._context.user_id,
            "session_id": self._context.session_id,
            "trace_id": self._context.trace_id,
            "span_id": self._context.span_id,
            "service": self._context.service_name,
            "environment": self._context.environment,
        }

        # 移除 None 值
        ctx = {k: v for k, v in ctx.items() if v is not None}

        # 添加額外上下文
        ctx.update(self._context.extra)

        return ctx

    @contextmanager
    def context(self, **kwargs):
        """上下文管理器"""
        old_context = LogContext(
            request_id=self._context.request_id,
            user_id=self._context.user_id,
            session_id=self._context.session_id,
            trace_id=self._context.trace_id,
            span_id=self._context.span_id,
            service_name=self._context.service_name,
            environment=self._context.environment,
            extra=self._context.extra.copy(),
        )

        try:
            self.set_context(**kwargs)
            yield
        finally:
            self._context = old_context

    # ========================================================================
    # 核心日誌方法
    # ========================================================================

    def log(
        self,
        level: Union[LogLevel, str],
        event_type: Union[EventType, str],
        message: str,
        data: Optional[Dict[str, Any]] = None,
        error: Optional[Exception] = None,
        duration_ms: Optional[float] = None,
        tags: Optional[List[str]] = None,
        **kwargs,
    ):
        """
        記錄結構化日誌

        Args:
            level: 日誌級別
            event_type: 事件類型
            message: 日誌消息
            data: 附加數據
            error: 異常（如果有）
            duration_ms: 持續時間（毫秒）
            tags: 標籤
            **kwargs: 額外的數據字段
        """
        # 構建事件
        event = LogEvent(
            timestamp=datetime.utcnow().isoformat() + "Z",
            level=level.value if isinstance(level, LogLevel) else level,
            event_type=event_type.value if isinstance(event_type, EventType) else event_type,
            message=message,
            service=self.service_name,
            context=self.get_context(),
            data={**(data or {}), **kwargs},
            duration_ms=duration_ms,
            tags=tags or [],
        )

        # 處理錯誤
        if error:
            event.error = {
                "type": type(error).__name__,
                "message": str(error),
                "traceback": self._format_traceback(error),
            }

        # 輸出日誌
        log_func = getattr(logger, level.lower() if isinstance(level, str) else level.value.lower())

        if self.json_output:
            log_func(event.to_json())
        else:
            log_func(f"[{event.event_type}] {message}")

    def _format_traceback(self, error: Exception) -> Optional[str]:
        """格式化異常追蹤"""
        import traceback
        return "".join(traceback.format_exception(type(error), error, error.__traceback__))

    # ========================================================================
    # 便捷方法
    # ========================================================================

    def debug(self, message: str, event_type: str = "custom", **kwargs):
        """DEBUG 級別日誌"""
        self.log(LogLevel.DEBUG, event_type, message, **kwargs)

    def info(self, message: str, event_type: str = "custom", **kwargs):
        """INFO 級別日誌"""
        self.log(LogLevel.INFO, event_type, message, **kwargs)

    def warning(self, message: str, event_type: str = "custom", **kwargs):
        """WARNING 級別日誌"""
        self.log(LogLevel.WARNING, event_type, message, **kwargs)

    def error(self, message: str, event_type: str = "custom", error: Exception = None, **kwargs):
        """ERROR 級別日誌"""
        self.log(LogLevel.ERROR, event_type, message, error=error, **kwargs)

    def critical(self, message: str, event_type: str = "custom", error: Exception = None, **kwargs):
        """CRITICAL 級別日誌"""
        self.log(LogLevel.CRITICAL, event_type, message, error=error, **kwargs)

    # ========================================================================
    # 專用事件方法
    # ========================================================================

    def log_http_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
        user_id: Optional[str] = None,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        **kwargs,
    ):
        """記錄 HTTP 請求"""
        self.log(
            LogLevel.INFO,
            EventType.HTTP_REQUEST,
            f"{method} {path} {status_code}",
            data={
                "method": method,
                "path": path,
                "status_code": status_code,
                "client_ip": client_ip,
                "user_agent": user_agent,
                **kwargs,
            },
            duration_ms=duration_ms,
            user_id=user_id,
        )

    def log_db_query(
        self,
        operation: str,
        table: Optional[str] = None,
        duration_ms: Optional[float] = None,
        rows_affected: Optional[int] = None,
        **kwargs,
    ):
        """記錄資料庫查詢"""
        self.log(
            LogLevel.DEBUG,
            EventType.DB_QUERY,
            f"DB {operation}" + (f" on {table}" if table else ""),
            data={
                "operation": operation,
                "table": table,
                "rows_affected": rows_affected,
                **kwargs,
            },
            duration_ms=duration_ms,
        )

    def log_db_error(
        self,
        operation: str,
        error: Exception,
        table: Optional[str] = None,
        **kwargs,
    ):
        """記錄資料庫錯誤"""
        self.log(
            LogLevel.ERROR,
            EventType.DB_ERROR,
            f"DB {operation} 失敗" + (f" on {table}" if table else ""),
            data={
                "operation": operation,
                "table": table,
                **kwargs,
            },
            error=error,
        )

    def log_cache_operation(
        self,
        operation: str,
        key: str,
        hit: Optional[bool] = None,
        duration_ms: Optional[float] = None,
        **kwargs,
    ):
        """記錄快取操作"""
        if operation == "get":
            event_type = EventType.CACHE_HIT if hit else EventType.CACHE_MISS
        elif operation == "set":
            event_type = EventType.CACHE_SET
        elif operation == "delete":
            event_type = EventType.CACHE_DELETE
        else:
            event_type = EventType.CUSTOM

        self.log(
            LogLevel.DEBUG,
            event_type,
            f"Cache {operation}: {key}",
            data={
                "operation": operation,
                "key": key,
                "hit": hit,
                **kwargs,
            },
            duration_ms=duration_ms,
        )

    def log_auth_event(
        self,
        event_type: EventType,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        success: bool = True,
        reason: Optional[str] = None,
        **kwargs,
    ):
        """記錄認證事件"""
        self.log(
            LogLevel.INFO if success else LogLevel.WARNING,
            event_type,
            f"Auth event: {event_type.value}",
            data={
                "user_id": user_id,
                "username": username,
                "success": success,
                "reason": reason,
                **kwargs,
            },
        )

    def log_inference(
        self,
        status: str,  # start, end, error
        model_name: Optional[str] = None,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        duration_ms: Optional[float] = None,
        error: Optional[Exception] = None,
        **kwargs,
    ):
        """記錄推理事件"""
        if status == "start":
            event_type = EventType.INFERENCE_START
            level = LogLevel.INFO
        elif status == "end":
            event_type = EventType.INFERENCE_END
            level = LogLevel.INFO
        else:
            event_type = EventType.INFERENCE_ERROR
            level = LogLevel.ERROR

        self.log(
            level,
            event_type,
            f"Inference {status}",
            data={
                "model_name": model_name,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                **kwargs,
            },
            duration_ms=duration_ms,
            error=error,
        )

    # ========================================================================
    # 計時器
    # ========================================================================

    @contextmanager
    def timer(
        self,
        operation: str,
        event_type: Union[EventType, str] = EventType.CUSTOM,
        level: LogLevel = LogLevel.INFO,
        **extra_data,
    ):
        """
        計時器上下文管理器

        使用方式：
        with structured_logger.timer("database_query", event_type=EventType.DB_QUERY):
            result = db.execute(query)
        """
        start_time = time.time()

        try:
            yield
            duration_ms = (time.time() - start_time) * 1000

            self.log(
                level,
                event_type,
                f"{operation} 完成",
                data=extra_data,
                duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000

            self.log(
                LogLevel.ERROR,
                event_type,
                f"{operation} 失敗",
                data=extra_data,
                duration_ms=duration_ms,
                error=e,
            )
            raise


# ============================================================================
# 全局實例
# ============================================================================

structured_logger = StructuredLogger()


def get_structured_logger() -> StructuredLogger:
    """獲取全局結構化日誌記錄器"""
    return structured_logger


def configure_structured_logging(
    service_name: str = "medical-chatbot",
    environment: str = "development",
    json_output: bool = True,
):
    """配置結構化日誌"""
    global structured_logger
    structured_logger = StructuredLogger(
        service_name=service_name,
        environment=environment,
        json_output=json_output,
    )
    return structured_logger
