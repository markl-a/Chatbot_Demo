"""
API 文檔配置

定義 API 文檔的配置選項。
"""
from typing import Dict, List, Optional, Any
from pydantic import BaseModel


class ContactInfo(BaseModel):
    """聯絡資訊"""

    name: str = "API Support"
    email: str = "support@example.com"
    url: Optional[str] = None


class LicenseInfo(BaseModel):
    """授權資訊"""

    name: str = "MIT"
    url: Optional[str] = "https://opensource.org/licenses/MIT"


class ServerInfo(BaseModel):
    """伺服器資訊"""

    url: str
    description: str = "Production"


class DocsConfig(BaseModel):
    """API 文檔配置"""

    # 基本資訊
    title: str = "醫療聊天機器人 API"
    description: str = "基於 TAIDE 的醫療問答系統 API"
    version: str = "1.0.0"

    # 聯絡和授權
    contact: ContactInfo = ContactInfo()
    license_info: LicenseInfo = LicenseInfo()

    # 伺服器
    servers: List[ServerInfo] = [
        ServerInfo(url="http://localhost:8000", description="開發環境"),
        ServerInfo(url="https://api.example.com", description="生產環境"),
    ]

    # OpenAPI 設定
    openapi_version: str = "3.0.2"
    openapi_url: str = "/openapi.json"
    docs_url: str = "/docs"
    redoc_url: str = "/redoc"

    # 標籤分組
    tags_metadata: List[Dict[str, Any]] = [
        {
            "name": "health",
            "description": "健康檢查端點",
        },
        {
            "name": "chat",
            "description": "聊天對話端點",
        },
        {
            "name": "generate",
            "description": "文本生成端點",
        },
        {
            "name": "models",
            "description": "模型管理端點",
        },
        {
            "name": "evaluation",
            "description": "模型評估端點",
        },
        {
            "name": "batch",
            "description": "批次推理端點",
        },
        {
            "name": "admin",
            "description": "管理端點（需要認證）",
        },
    ]

    # 安全方案
    security_schemes: Dict[str, Any] = {
        "APIKeyHeader": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "API 金鑰認證",
        },
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT Bearer Token",
        },
    }

    # 範例
    examples: Dict[str, Any] = {
        "chat_request": {
            "summary": "聊天請求範例",
            "value": {
                "message": "什麼是高血壓？",
                "max_length": 256,
                "temperature": 0.7,
            },
        },
        "chat_response": {
            "summary": "聊天回覆範例",
            "value": {
                "response": "高血壓是一種血壓持續高於正常值的慢性疾病...",
                "session_id": "session-123",
                "model": "TAIDE-LX-8B",
                "generation_time": 0.523,
            },
        },
    }

    class Config:
        """Pydantic 配置"""

        json_schema_extra = {
            "example": {
                "title": "醫療聊天機器人 API",
                "description": "基於 TAIDE 的醫療問答系統",
                "version": "1.0.0",
            }
        }


class SwaggerUIConfig(BaseModel):
    """Swagger UI 自訂配置"""

    # 顯示選項
    display_request_duration: bool = True
    display_operation_id: bool = False
    show_extensions: bool = True
    show_common_extensions: bool = True

    # 互動選項
    default_model_expand_depth: int = 2
    default_models_expand_depth: int = 1

    # 過濾選項
    filter: Optional[str] = None

    # 樣式
    custom_css: Optional[str] = None
    custom_js: Optional[str] = None


class ReDocConfig(BaseModel):
    """ReDoc 自訂配置"""

    # 顯示選項
    hide_download_button: bool = False
    expand_responses: str = "200,201"
    path_in_middle_panel: bool = False
    hide_hostname: bool = False

    # 主題
    theme: Dict[str, Any] = {
        "colors": {
            "primary": {
                "main": "#4CAF50",
            }
        },
        "typography": {
            "fontSize": "14px",
            "fontFamily": "Arial, sans-serif",
        },
    }
