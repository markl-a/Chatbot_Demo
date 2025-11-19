"""
自定義異常類別

定義專案中使用的所有自定義異常。
"""
from typing import Optional, Dict, Any


class MedicalChatbotException(Exception):
    """醫療聊天機器人基礎異常類別"""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式"""
        return {
            "error": self.__class__.__name__,
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details
        }

    def __str__(self) -> str:
        return f"[{self.error_code}] {self.message}"


# ============================================================================
# 模型相關異常
# ============================================================================


class ModelException(MedicalChatbotException):
    """模型相關異常基類"""
    pass


class ModelNotLoadedException(ModelException):
    """模型未載入異常"""

    def __init__(self, message: str = "模型尚未載入，請先載入模型"):
        super().__init__(message, error_code="MODEL_NOT_LOADED")


class ModelLoadException(ModelException):
    """模型載入失敗異常"""

    def __init__(self, model_name: str, reason: Optional[str] = None):
        message = f"無法載入模型: {model_name}"
        if reason:
            message += f" - {reason}"
        super().__init__(
            message,
            error_code="MODEL_LOAD_FAILED",
            details={"model_name": model_name, "reason": reason}
        )


class ModelInferenceException(ModelException):
    """模型推理失敗異常"""

    def __init__(self, message: str = "模型推理失敗", details: Optional[Dict] = None):
        super().__init__(message, error_code="MODEL_INFERENCE_FAILED", details=details)


class OutOfMemoryException(ModelException):
    """記憶體不足異常"""

    def __init__(self, message: str = "GPU/CPU 記憶體不足"):
        super().__init__(message, error_code="OUT_OF_MEMORY")


class AdapterException(ModelException):
    """適配器相關異常"""

    def __init__(self, message: str, adapter_path: Optional[str] = None):
        super().__init__(
            message,
            error_code="ADAPTER_ERROR",
            details={"adapter_path": adapter_path}
        )


# ============================================================================
# 配置相關異常
# ============================================================================


class ConfigException(MedicalChatbotException):
    """配置相關異常基類"""
    pass


class ConfigLoadException(ConfigException):
    """配置載入失敗異常"""

    def __init__(self, config_path: str, reason: Optional[str] = None):
        message = f"無法載入配置文件: {config_path}"
        if reason:
            message += f" - {reason}"
        super().__init__(
            message,
            error_code="CONFIG_LOAD_FAILED",
            details={"config_path": config_path, "reason": reason}
        )


class ConfigValidationException(ConfigException):
    """配置驗證失敗異常"""

    def __init__(self, message: str, field: Optional[str] = None):
        super().__init__(
            message,
            error_code="CONFIG_VALIDATION_FAILED",
            details={"field": field}
        )


class MissingConfigException(ConfigException):
    """缺少必要配置異常"""

    def __init__(self, field: str):
        super().__init__(
            f"缺少必要的配置項: {field}",
            error_code="MISSING_CONFIG",
            details={"field": field}
        )


# ============================================================================
# 資料相關異常
# ============================================================================


class DataException(MedicalChatbotException):
    """資料相關異常基類"""
    pass


class DatasetLoadException(DataException):
    """資料集載入失敗異常"""

    def __init__(self, dataset_name: str, reason: Optional[str] = None):
        message = f"無法載入資料集: {dataset_name}"
        if reason:
            message += f" - {reason}"
        super().__init__(
            message,
            error_code="DATASET_LOAD_FAILED",
            details={"dataset_name": dataset_name, "reason": reason}
        )


class DataPreprocessingException(DataException):
    """資料預處理異常"""

    def __init__(self, message: str = "資料預處理失敗"):
        super().__init__(message, error_code="DATA_PREPROCESSING_FAILED")


class InvalidDataException(DataException):
    """無效資料異常"""

    def __init__(self, message: str = "資料格式無效", data_info: Optional[Dict] = None):
        super().__init__(
            message,
            error_code="INVALID_DATA",
            details=data_info
        )


# ============================================================================
# API 相關異常
# ============================================================================


class APIException(MedicalChatbotException):
    """API 相關異常基類"""
    pass


class InvalidRequestException(APIException):
    """無效請求異常"""

    def __init__(self, message: str = "請求參數無效", field: Optional[str] = None):
        super().__init__(
            message,
            error_code="INVALID_REQUEST",
            details={"field": field}
        )


class RateLimitException(APIException):
    """速率限制異常"""

    def __init__(self, message: str = "請求過於頻繁，請稍後再試"):
        super().__init__(message, error_code="RATE_LIMIT_EXCEEDED")


class AuthenticationException(APIException):
    """認證失敗異常"""

    def __init__(self, message: str = "認證失敗"):
        super().__init__(message, error_code="AUTHENTICATION_FAILED")


class TimeoutException(APIException):
    """請求超時異常"""

    def __init__(self, message: str = "請求處理超時"):
        super().__init__(message, error_code="REQUEST_TIMEOUT")


# ============================================================================
# 安全相關異常
# ============================================================================


class SafetyException(MedicalChatbotException):
    """安全相關異常基類"""
    pass


class UnsafeContentException(SafetyException):
    """不安全內容異常"""

    def __init__(self, message: str = "檢測到不安全的內容"):
        super().__init__(message, error_code="UNSAFE_CONTENT")


class EmergencyDetectedException(SafetyException):
    """緊急情況檢測異常"""

    def __init__(self, message: str = "檢測到緊急醫療情況，請立即撥打 119"):
        super().__init__(message, error_code="EMERGENCY_DETECTED")


class InputValidationException(SafetyException):
    """輸入驗證失敗異常"""

    def __init__(self, message: str = "輸入驗證失敗", field: Optional[str] = None):
        super().__init__(
            message,
            error_code="INPUT_VALIDATION_FAILED",
            details={"field": field}
        )


# ============================================================================
# 訓練相關異常
# ============================================================================


class TrainingException(MedicalChatbotException):
    """訓練相關異常基類"""
    pass


class TrainingFailedException(TrainingException):
    """訓練失敗異常"""

    def __init__(self, message: str = "模型訓練失敗", epoch: Optional[int] = None):
        super().__init__(
            message,
            error_code="TRAINING_FAILED",
            details={"epoch": epoch}
        )


class CheckpointException(TrainingException):
    """檢查點相關異常"""

    def __init__(self, message: str, checkpoint_path: Optional[str] = None):
        super().__init__(
            message,
            error_code="CHECKPOINT_ERROR",
            details={"checkpoint_path": checkpoint_path}
        )


# ============================================================================
# RAG 相關異常
# ============================================================================


class RAGException(MedicalChatbotException):
    """RAG 相關異常基類"""
    pass


class VectorStoreException(RAGException):
    """向量存儲異常"""

    def __init__(self, message: str = "向量存儲操作失敗"):
        super().__init__(message, error_code="VECTOR_STORE_ERROR")


class RetrievalException(RAGException):
    """檢索失敗異常"""

    def __init__(self, message: str = "文檔檢索失敗", query: Optional[str] = None):
        super().__init__(
            message,
            error_code="RETRIEVAL_FAILED",
            details={"query": query}
        )


class EmbeddingException(RAGException):
    """嵌入生成失敗異常"""

    def __init__(self, message: str = "嵌入向量生成失敗"):
        super().__init__(message, error_code="EMBEDDING_FAILED")


# ============================================================================
# 資料庫相關異常
# ============================================================================


class DatabaseException(MedicalChatbotException):
    """資料庫相關異常基類"""
    pass


class ConnectionException(DatabaseException):
    """資料庫連接異常"""

    def __init__(self, message: str = "資料庫連接失敗"):
        super().__init__(message, error_code="DB_CONNECTION_FAILED")


class QueryException(DatabaseException):
    """查詢執行失敗異常"""

    def __init__(self, message: str = "資料庫查詢失敗", query: Optional[str] = None):
        super().__init__(
            message,
            error_code="DB_QUERY_FAILED",
            details={"query": query}
        )


# ============================================================================
# 快取相關異常
# ============================================================================


class CacheException(MedicalChatbotException):
    """快取相關異常基類"""
    pass


class CacheConnectionException(CacheException):
    """快取連接異常"""

    def __init__(self, message: str = "快取服務連接失敗"):
        super().__init__(message, error_code="CACHE_CONNECTION_FAILED")


class CacheOperationException(CacheException):
    """快取操作異常"""

    def __init__(self, message: str = "快取操作失敗", operation: Optional[str] = None):
        super().__init__(
            message,
            error_code="CACHE_OPERATION_FAILED",
            details={"operation": operation}
        )


# ============================================================================
# 工具函數
# ============================================================================


def get_exception_by_code(error_code: str) -> type:
    """根據錯誤碼獲取異常類別"""
    exception_map = {
        "MODEL_NOT_LOADED": ModelNotLoadedException,
        "MODEL_LOAD_FAILED": ModelLoadException,
        "MODEL_INFERENCE_FAILED": ModelInferenceException,
        "OUT_OF_MEMORY": OutOfMemoryException,
        "CONFIG_LOAD_FAILED": ConfigLoadException,
        "CONFIG_VALIDATION_FAILED": ConfigValidationException,
        "MISSING_CONFIG": MissingConfigException,
        "DATASET_LOAD_FAILED": DatasetLoadException,
        "INVALID_DATA": InvalidDataException,
        "INVALID_REQUEST": InvalidRequestException,
        "RATE_LIMIT_EXCEEDED": RateLimitException,
        "AUTHENTICATION_FAILED": AuthenticationException,
        "REQUEST_TIMEOUT": TimeoutException,
        "UNSAFE_CONTENT": UnsafeContentException,
        "EMERGENCY_DETECTED": EmergencyDetectedException,
        "INPUT_VALIDATION_FAILED": InputValidationException,
        "TRAINING_FAILED": TrainingFailedException,
        "VECTOR_STORE_ERROR": VectorStoreException,
        "RETRIEVAL_FAILED": RetrievalException,
        "DB_CONNECTION_FAILED": ConnectionException,
        "DB_QUERY_FAILED": QueryException,
        "CACHE_CONNECTION_FAILED": CacheConnectionException,
    }
    return exception_map.get(error_code, MedicalChatbotException)
