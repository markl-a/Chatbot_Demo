"""
錯誤處理工具

提供統一的錯誤處理機制和中間件。
"""
from typing import Callable, Optional, Any, Dict
from functools import wraps
import traceback
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from .exceptions import (
    MedicalChatbotException,
    ModelException,
    APIException,
    SafetyException,
    DataException,
    ConfigException,
    RateLimitException,
    TimeoutException,
    AuthenticationException,
)
from .logger import get_logger

logger = get_logger(__name__)


# ============================================================================
# 錯誤處理裝飾器
# ============================================================================


def handle_errors(
    default_message: str = "操作失敗",
    reraise: bool = False,
    log_traceback: bool = True
):
    """
    錯誤處理裝飾器

    Args:
        default_message: 默認錯誤消息
        reraise: 是否重新拋出異常
        log_traceback: 是否記錄完整堆疊追蹤
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except MedicalChatbotException as e:
                # 自定義異常，直接記錄並處理
                logger.error(f"{func.__name__} 發生錯誤: {e}")
                if log_traceback:
                    logger.debug(traceback.format_exc())
                if reraise:
                    raise
                return None
            except Exception as e:
                # 未預期的異常
                logger.error(f"{func.__name__} 發生未預期的錯誤: {e}")
                if log_traceback:
                    logger.exception(f"完整錯誤追蹤:")
                if reraise:
                    raise
                return None

        return wrapper
    return decorator


def async_handle_errors(
    default_message: str = "操作失敗",
    reraise: bool = False,
    log_traceback: bool = True
):
    """
    非同步錯誤處理裝飾器

    Args:
        default_message: 默認錯誤消息
        reraise: 是否重新拋出異常
        log_traceback: 是否記錄完整堆疊追蹤
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except MedicalChatbotException as e:
                logger.error(f"{func.__name__} 發生錯誤: {e}")
                if log_traceback:
                    logger.debug(traceback.format_exc())
                if reraise:
                    raise
                return None
            except Exception as e:
                logger.error(f"{func.__name__} 發生未預期的錯誤: {e}")
                if log_traceback:
                    logger.exception(f"完整錯誤追蹤:")
                if reraise:
                    raise
                return None

        return wrapper
    return decorator


def retry_on_error(
    max_retries: int = 3,
    exceptions: tuple = (Exception,),
    delay: float = 1.0,
    backoff: float = 2.0
):
    """
    錯誤重試裝飾器

    Args:
        max_retries: 最大重試次數
        exceptions: 需要重試的異常類型
        delay: 初始延遲時間（秒）
        backoff: 延遲時間的倍數
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            import time

            current_delay = delay
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(
                            f"{func.__name__} 失敗 (嘗試 {attempt + 1}/{max_retries}), "
                            f"{current_delay}秒後重試: {e}"
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(f"{func.__name__} 在 {max_retries} 次重試後仍然失敗")

            if last_exception:
                raise last_exception

        return wrapper
    return decorator


# ============================================================================
# FastAPI 錯誤處理器
# ============================================================================


async def medical_chatbot_exception_handler(
    request: Request,
    exc: MedicalChatbotException
) -> JSONResponse:
    """處理自定義異常"""
    logger.error(f"請求錯誤: {exc.error_code} - {exc.message}")

    # 根據異常類型確定 HTTP 狀態碼
    status_code = get_http_status_code(exc)

    return JSONResponse(
        status_code=status_code,
        content=exc.to_dict()
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError
) -> JSONResponse:
    """處理請求驗證錯誤"""
    logger.warning(f"請求驗證失敗: {exc.errors()}")

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "ValidationError",
            "error_code": "VALIDATION_ERROR",
            "message": "請求參數驗證失敗",
            "details": exc.errors()
        }
    )


async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException
) -> JSONResponse:
    """處理 HTTP 異常"""
    logger.warning(f"HTTP 錯誤: {exc.status_code} - {exc.detail}")

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTPException",
            "error_code": f"HTTP_{exc.status_code}",
            "message": exc.detail
        }
    )


async def general_exception_handler(
    request: Request,
    exc: Exception
) -> JSONResponse:
    """處理未捕獲的異常"""
    logger.exception(f"未捕獲的異常: {exc}")

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "InternalServerError",
            "error_code": "INTERNAL_ERROR",
            "message": "伺服器內部錯誤，請稍後再試",
            "details": {
                "type": type(exc).__name__,
                "message": str(exc)
            }
        }
    )


# ============================================================================
# 輔助函數
# ============================================================================


def get_http_status_code(exc: MedicalChatbotException) -> int:
    """根據異常類型返回相應的 HTTP 狀態碼"""
    status_map = {
        APIException: status.HTTP_400_BAD_REQUEST,
        RateLimitException: status.HTTP_429_TOO_MANY_REQUESTS,
        AuthenticationException: status.HTTP_401_UNAUTHORIZED,
        TimeoutException: status.HTTP_504_GATEWAY_TIMEOUT,
        ModelException: status.HTTP_503_SERVICE_UNAVAILABLE,
        ConfigException: status.HTTP_500_INTERNAL_SERVER_ERROR,
        DataException: status.HTTP_422_UNPROCESSABLE_ENTITY,
        SafetyException: status.HTTP_400_BAD_REQUEST,
    }

    # 檢查異常類型
    for exc_type, status_code in status_map.items():
        if isinstance(exc, exc_type):
            return status_code

    # 默認返回 500
    return status.HTTP_500_INTERNAL_SERVER_ERROR


def format_error_response(
    error: Exception,
    include_traceback: bool = False
) -> Dict[str, Any]:
    """
    格式化錯誤響應

    Args:
        error: 異常對象
        include_traceback: 是否包含堆疊追蹤

    Returns:
        格式化的錯誤字典
    """
    if isinstance(error, MedicalChatbotException):
        response = error.to_dict()
    else:
        response = {
            "error": type(error).__name__,
            "error_code": "UNKNOWN_ERROR",
            "message": str(error),
            "details": {}
        }

    if include_traceback:
        response["traceback"] = traceback.format_exc()

    return response


def log_error(
    error: Exception,
    context: Optional[Dict[str, Any]] = None,
    level: str = "error"
):
    """
    記錄錯誤

    Args:
        error: 異常對象
        context: 額外的上下文信息
        level: 日誌級別
    """
    error_info = format_error_response(error, include_traceback=True)

    if context:
        error_info["context"] = context

    log_func = getattr(logger, level, logger.error)
    log_func(f"錯誤發生: {error_info}")


class ErrorContext:
    """錯誤上下文管理器"""

    def __init__(
        self,
        operation: str,
        reraise: bool = True,
        log_level: str = "error"
    ):
        self.operation = operation
        self.reraise = reraise
        self.log_level = log_level

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val is not None:
            log_error(
                exc_val,
                context={"operation": self.operation},
                level=self.log_level
            )

            if not self.reraise:
                return True  # 抑制異常

        return False


# ============================================================================
# 錯誤恢復策略
# ============================================================================


class ErrorRecoveryStrategy:
    """錯誤恢復策略基類"""

    def can_recover(self, error: Exception) -> bool:
        """判斷是否可以恢復"""
        raise NotImplementedError

    def recover(self, error: Exception) -> Any:
        """執行恢復操作"""
        raise NotImplementedError


class ModelLoadErrorRecovery(ErrorRecoveryStrategy):
    """模型載入錯誤恢復策略"""

    def __init__(self, fallback_models: list):
        self.fallback_models = fallback_models

    def can_recover(self, error: Exception) -> bool:
        from .exceptions import ModelLoadException
        return isinstance(error, ModelLoadException)

    def recover(self, error: Exception) -> Any:
        logger.info(f"嘗試使用備選模型恢復...")
        # 實現載入備選模型的邏輯
        for model_name in self.fallback_models:
            try:
                logger.info(f"嘗試載入備選模型: {model_name}")
                # 這裡應該調用實際的模型載入邏輯
                return {"model_name": model_name, "status": "loaded"}
            except Exception as e:
                logger.warning(f"備選模型 {model_name} 載入失敗: {e}")
                continue

        raise error


def register_error_handlers(app):
    """
    註冊所有錯誤處理器到 FastAPI 應用

    Args:
        app: FastAPI 應用實例
    """
    app.add_exception_handler(MedicalChatbotException, medical_chatbot_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)

    logger.info("已註冊所有錯誤處理器")
