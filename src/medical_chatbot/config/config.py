"""
應用配置

使用 Pydantic Settings 管理應用配置，支援環境變數和 .env 檔案。
"""
from typing import Optional, List, Literal
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, validator


class Settings(BaseSettings):
    """應用配置"""

    # ========================================================================
    # 基本設定
    # ========================================================================

    APP_NAME: str = Field(default="醫療聊天機器人", description="應用名稱")
    APP_VERSION: str = Field(default="1.0.0", description="應用版本")
    ENVIRONMENT: Literal["development", "testing", "staging", "production"] = Field(
        default="development", description="運行環境"
    )
    DEBUG: bool = Field(default=False, description="調試模式")

    # API 設定
    API_HOST: str = Field(default="0.0.0.0", description="API 主機")
    API_PORT: int = Field(default=8000, description="API 端口")
    API_PREFIX: str = Field(default="/api/v1", description="API 路徑前綴")

    # CORS
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="允許的 CORS 來源"
    )
    CORS_ALLOW_CREDENTIALS: bool = Field(default=True, description="允許憑證")

    # ========================================================================
    # 資料庫配置
    # ========================================================================

    DATABASE_URL: str = Field(
        default="sqlite:///./medical_chatbot.db",
        description="資料庫連接 URL"
    )
    DATABASE_POOL_SIZE: int = Field(default=5, description="連接池大小")
    DATABASE_MAX_OVERFLOW: int = Field(default=10, description="最大溢出連接")
    DATABASE_ECHO: bool = Field(default=False, description="是否輸出 SQL")

    # ========================================================================
    # Redis 配置
    # ========================================================================

    REDIS_HOST: str = Field(default="localhost", description="Redis 主機")
    REDIS_PORT: int = Field(default=6379, description="Redis 端口")
    REDIS_DB: int = Field(default=0, description="Redis 資料庫")
    REDIS_PASSWORD: Optional[str] = Field(default=None, description="Redis 密碼")
    REDIS_MAX_CONNECTIONS: int = Field(default=50, description="最大連接數")

    # ========================================================================
    # 快取配置
    # ========================================================================

    CACHE_STRATEGY: Literal["memory_only", "redis_only", "multi_tier"] = Field(
        default="multi_tier", description="快取策略"
    )
    CACHE_MEMORY_SIZE: int = Field(default=1000, description="記憶體快取大小")
    CACHE_TTL: int = Field(default=3600, description="預設 TTL（秒）")

    # ========================================================================
    # 速率限制配置
    # ========================================================================

    RATE_LIMIT_ENABLED: bool = Field(default=True, description="是否啟用速率限制")
    RATE_LIMIT_STRATEGY: Literal["fixed_window", "sliding_window", "token_bucket"] = Field(
        default="sliding_window", description="速率限制策略"
    )
    RATE_LIMIT_DEFAULT: int = Field(default=60, description="預設限制（次/分鐘）")
    RATE_LIMIT_WINDOW: int = Field(default=60, description="時間窗口（秒）")

    # ========================================================================
    # 模型配置
    # ========================================================================

    MODEL_NAME: str = Field(default="TAIDE-LX-8B", description="預設模型名稱")
    MODEL_PATH: Optional[str] = Field(default=None, description="模型路徑")
    MODEL_DEVICE: str = Field(default="cuda", description="運行設備")
    MODEL_MAX_LENGTH: int = Field(default=512, description="最大生成長度")
    MODEL_TEMPERATURE: float = Field(default=0.7, description="生成溫度")
    MODEL_TOP_P: float = Field(default=0.9, description="Top-p 採樣")

    # ========================================================================
    # 批次推理配置
    # ========================================================================

    BATCH_SIZE: int = Field(default=8, description="批次大小")
    BATCH_MAX_WORKERS: int = Field(default=4, description="並行工作數")
    BATCH_SAVE_INTERVAL: int = Field(default=100, description="檢查點保存間隔")

    # ========================================================================
    # 日誌配置
    # ========================================================================

    LOG_LEVEL: str = Field(default="INFO", description="日誌級別")
    LOG_FORMAT: str = Field(
        default="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        description="日誌格式"
    )
    LOG_FILE: Optional[str] = Field(default="logs/app.log", description="日誌檔案路徑")
    LOG_ROTATION: str = Field(default="500 MB", description="日誌輪轉大小")
    LOG_RETENTION: str = Field(default="10 days", description="日誌保留時間")

    # ========================================================================
    # 安全配置
    # ========================================================================

    SECRET_KEY: str = Field(
        default="your-secret-key-change-in-production",
        description="密鑰（生產環境務必更改）"
    )
    API_KEY_HEADER: str = Field(default="X-API-Key", description="API Key 標頭名稱")
    JWT_ALGORITHM: str = Field(default="HS256", description="JWT 演算法")
    JWT_EXPIRE_MINUTES: int = Field(default=60, description="JWT 過期時間（分鐘）")

    # ========================================================================
    # 監控配置
    # ========================================================================

    METRICS_ENABLED: bool = Field(default=True, description="是否啟用指標")
    METRICS_PORT: int = Field(default=9090, description="Prometheus 指標端口")
    HEALTH_CHECK_INTERVAL: int = Field(default=30, description="健康檢查間隔（秒）")

    # ========================================================================
    # 其他配置
    # ========================================================================

    TIMEZONE: str = Field(default="Asia/Taipei", description="時區")
    MAX_REQUEST_SIZE: int = Field(default=10 * 1024 * 1024, description="最大請求大小（bytes）")
    UPLOAD_DIR: str = Field(default="uploads", description="上傳目錄")

    # ========================================================================
    # Pydantic 配置
    # ========================================================================

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ========================================================================
    # 驗證器
    # ========================================================================

    @validator("DATABASE_URL")
    def validate_database_url(cls, v: str) -> str:
        """驗證資料庫 URL"""
        if not v:
            raise ValueError("DATABASE_URL 不能為空")
        return v

    @validator("SECRET_KEY")
    def validate_secret_key(cls, v: str, values: dict) -> str:
        """驗證密鑰"""
        if values.get("ENVIRONMENT") == "production" and v == "your-secret-key-change-in-production":
            raise ValueError("生產環境必須設置 SECRET_KEY")
        return v

    @validator("MODEL_TEMPERATURE")
    def validate_temperature(cls, v: float) -> float:
        """驗證溫度參數"""
        if not 0.0 <= v <= 2.0:
            raise ValueError("MODEL_TEMPERATURE 必須在 0.0 到 2.0 之間")
        return v

    @validator("MODEL_TOP_P")
    def validate_top_p(cls, v: float) -> float:
        """驗證 top-p 參數"""
        if not 0.0 <= v <= 1.0:
            raise ValueError("MODEL_TOP_P 必須在 0.0 到 1.0 之間")
        return v

    # ========================================================================
    # 屬性方法
    # ========================================================================

    @property
    def is_production(self) -> bool:
        """是否為生產環境"""
        return self.ENVIRONMENT == "production"

    @property
    def is_development(self) -> bool:
        """是否為開發環境"""
        return self.ENVIRONMENT == "development"

    @property
    def database_url_async(self) -> str:
        """異步資料庫 URL"""
        if self.DATABASE_URL.startswith("postgresql://"):
            return self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
        return self.DATABASE_URL

    @property
    def redis_url(self) -> str:
        """Redis URL"""
        auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    def get_log_config(self) -> dict:
        """獲取日誌配置"""
        return {
            "level": self.LOG_LEVEL,
            "format": self.LOG_FORMAT,
            "file": self.LOG_FILE,
            "rotation": self.LOG_ROTATION,
            "retention": self.LOG_RETENTION,
        }

    def to_dict(self) -> dict:
        """轉換為字典"""
        return self.model_dump()

    def display_safe_config(self) -> dict:
        """顯示安全的配置（隱藏敏感資訊）"""
        config = self.to_dict()

        # 隱藏敏感欄位
        sensitive_fields = [
            "SECRET_KEY",
            "DATABASE_URL",
            "REDIS_PASSWORD",
        ]

        for field in sensitive_fields:
            if field in config and config[field]:
                config[field] = "***HIDDEN***"

        return config


# ============================================================================
# 全域配置實例
# ============================================================================

@lru_cache()
def get_settings() -> Settings:
    """
    獲取配置實例（單例模式）

    使用 lru_cache 確保配置只載入一次
    """
    return Settings()


# ============================================================================
# 輔助函數
# ============================================================================

def load_settings_from_file(file_path: str) -> Settings:
    """
    從指定檔案載入配置

    Args:
        file_path: 配置檔案路徑

    Returns:
        Settings 實例
    """
    return Settings(_env_file=file_path)


def update_settings(**kwargs) -> Settings:
    """
    更新配置（用於測試）

    Args:
        **kwargs: 要更新的配置項

    Returns:
        新的 Settings 實例
    """
    current = get_settings()
    updated_config = current.to_dict()
    updated_config.update(kwargs)
    return Settings(**updated_config)
