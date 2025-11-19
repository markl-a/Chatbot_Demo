"""
FastAPI API 文檔整合範例

展示如何整合和自訂 FastAPI API 文檔。
"""
import sys
from pathlib import Path

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from typing import Optional

from src.medical_chatbot.docs import OpenAPIGenerator, DocsConfig
from src.medical_chatbot.docs.docs_config import (
    ContactInfo,
    LicenseInfo,
    ServerInfo,
    SwaggerUIConfig,
    ReDocConfig,
)


# ============================================================================
# 範例 1: 基本設置
# ============================================================================


def example_1_basic_setup():
    """基本 API 文檔設置"""
    print("\n" + "=" * 80)
    print("範例 1: 基本 API 文檔設置")
    print("=" * 80)

    # 創建 FastAPI 應用
    app = FastAPI()

    # 創建文檔配置
    config = DocsConfig(
        title="醫療聊天機器人 API",
        description="基於 TAIDE 的醫療問答系統 API",
        version="1.0.0",
    )

    # 創建文檔生成器
    doc_generator = OpenAPIGenerator(app, config)

    # 設置文檔
    doc_generator.setup_docs()

    # 定義路由
    @app.get("/health", tags=["health"])
    async def health_check():
        """健康檢查端點"""
        return {"status": "healthy"}

    @app.post("/chat", tags=["chat"])
    async def chat(message: str):
        """聊天端點"""
        return {"response": f"收到消息: {message}"}

    print(f"\n文檔生成器: {doc_generator}")
    print(f"\nSwagger UI: http://localhost:8000{config.docs_url}")
    print(f"ReDoc: http://localhost:8000{config.redoc_url}")
    print(f"OpenAPI JSON: http://localhost:8000{config.openapi_url}")

    print("""
啟動應用:
    uvicorn example_1_basic_setup:app --reload

然後訪問:
    http://localhost:8000/docs - Swagger UI
    http://localhost:8000/redoc - ReDoc
    """)

    return app


# ============================================================================
# 範例 2: 完整配置
# ============================================================================


def example_2_full_configuration():
    """完整的 API 文檔配置"""
    print("\n" + "=" * 80)
    print("範例 2: 完整配置")
    print("=" * 80)

    app = FastAPI()

    # 詳細配置
    config = DocsConfig(
        title="醫療聊天機器人 API",
        description="""
## 功能特性

這是一個基於 TAIDE 語言模型的醫療問答系統 API。

### 主要功能

- 💬 智能對話：使用先進的語言模型提供準確的醫療建議
- 🔍 知識檢索：整合 RAG 系統，提供基於知識庫的回覆
- 📊 多模型支援：支援 TAIDE、Breeze、Taiwan-LLM 等多種模型
- 🔒 安全可靠：API 金鑰認證、速率限制保護
- 📈 性能優化：Redis 快取、批次推理支援

### 技術棧

- FastAPI
- Transformers
- FAISS
- Redis
- PostgreSQL
        """,
        version="1.0.0",
        contact=ContactInfo(
            name="醫療 AI 團隊",
            email="ai-support@medical-chat.com",
            url="https://medical-chat.com",
        ),
        license_info=LicenseInfo(
            name="MIT License",
            url="https://opensource.org/licenses/MIT",
        ),
        servers=[
            ServerInfo(url="http://localhost:8000", description="開發環境"),
            ServerInfo(url="https://dev-api.medical-chat.com", description="測試環境"),
            ServerInfo(url="https://api.medical-chat.com", description="生產環境"),
        ],
    )

    doc_generator = OpenAPIGenerator(app, config)

    # 自訂 Swagger UI
    swagger_config = SwaggerUIConfig(
        display_request_duration=True,
        display_operation_id=False,
        default_model_expand_depth=2,
    )

    # 自訂 ReDoc
    redoc_config = ReDocConfig(
        hide_download_button=False,
        expand_responses="200,201",
    )

    doc_generator.setup_docs(swagger_ui_config=swagger_config, redoc_config=redoc_config)

    print(f"\n配置完成:")
    print(f"  標題: {config.title}")
    print(f"  版本: {config.version}")
    print(f"  聯絡: {config.contact.email}")
    print(f"  伺服器數: {len(config.servers)}")

    return app


# ============================================================================
# 範例 3: 帶 Pydantic 模型的完整 API
# ============================================================================


def example_3_complete_api():
    """完整的 API 範例（帶 Pydantic 模型）"""
    print("\n" + "=" * 80)
    print("範例 3: 完整的 API 範例")
    print("=" * 80)

    app = FastAPI()

    # Pydantic 模型
    class ChatRequest(BaseModel):
        message: str
        max_length: int = 256
        temperature: float = 0.7
        model: str = "TAIDE-LX-8B"

        class Config:
            json_schema_extra = {
                "example": {
                    "message": "什麼是高血壓？",
                    "max_length": 256,
                    "temperature": 0.7,
                    "model": "TAIDE-LX-8B",
                }
            }

    class ChatResponse(BaseModel):
        response: str
        session_id: str
        model: str
        generation_time: float

        class Config:
            json_schema_extra = {
                "example": {
                    "response": "高血壓是一種血壓持續高於正常值的慢性疾病...",
                    "session_id": "session-123",
                    "model": "TAIDE-LX-8B",
                    "generation_time": 0.523,
                }
            }

    class ErrorResponse(BaseModel):
        error: str
        message: str
        details: Optional[dict] = None

    # 配置文檔
    config = DocsConfig()
    doc_generator = OpenAPIGenerator(app, config)
    doc_generator.setup_docs()

    # 路由
    @app.post(
        "/api/v1/chat",
        response_model=ChatResponse,
        tags=["chat"],
        summary="聊天對話",
        description="發送消息到聊天機器人並獲取回覆",
        responses={
            200: {
                "description": "成功回覆",
                "model": ChatResponse,
            },
            400: {
                "description": "請求參數錯誤",
                "model": ErrorResponse,
            },
            401: {
                "description": "未授權",
                "model": ErrorResponse,
            },
            429: {
                "description": "請求過於頻繁",
                "model": ErrorResponse,
            },
        },
    )
    async def chat(
        request: ChatRequest,
        x_api_key: Optional[str] = Header(None, description="API 金鑰"),
    ):
        """
        ## 聊天對話

        發送消息到聊天機器人並獲取智能回覆。

        ### 參數說明

        - **message**: 用戶消息（必需）
        - **max_length**: 最大生成長度（預設: 256）
        - **temperature**: 生成溫度，控制隨機性（0-1，預設: 0.7）
        - **model**: 使用的模型名稱

        ### 範例

        ```python
        import requests

        response = requests.post(
            "http://localhost:8000/api/v1/chat",
            json={
                "message": "什麼是高血壓？",
                "max_length": 256,
                "temperature": 0.7,
            },
            headers={"X-API-Key": "your-api-key"}
        )

        print(response.json())
        ```
        """
        # 模擬回覆
        return ChatResponse(
            response=f"這是對「{request.message}」的回覆",
            session_id="session-123",
            model=request.model,
            generation_time=0.523,
        )

    @app.get("/api/v1/models", tags=["models"], summary="列出可用模型")
    async def list_models():
        """列出所有可用的模型"""
        return {
            "models": [
                "TAIDE-LX-8B",
                "Breeze-7B",
                "Taiwan-LLM-7B",
            ]
        }

    print("\n定義的端點:")
    print("  POST /api/v1/chat - 聊天對話")
    print("  GET  /api/v1/models - 列出模型")

    return app


# ============================================================================
# 範例 4: 導出文檔
# ============================================================================


def example_4_export_docs():
    """導出 API 文檔"""
    print("\n" + "=" * 80)
    print("範例 4: 導出文檔")
    print("=" * 80)

    app = example_3_complete_api()

    # 獲取文檔生成器
    config = DocsConfig()
    doc_generator = OpenAPIGenerator(app, config)
    doc_generator.setup_docs()

    print("\n導出文檔...")

    # 1. 導出 OpenAPI JSON
    doc_generator.export_openapi_spec("openapi.json")
    print("  ✓ openapi.json")

    # 2. 導出 Markdown
    doc_generator.export_markdown_docs("API_DOCS.md")
    print("  ✓ API_DOCS.md")

    print("\n檔案已導出到當前目錄")


# ============================================================================
# 範例 5: 安全方案配置
# ============================================================================


def example_5_security_schemes():
    """安全方案配置"""
    print("\n" + "=" * 80)
    print("範例 5: 安全方案配置")
    print("=" * 80)

    app = FastAPI()

    # 配置安全方案
    config = DocsConfig(
        security_schemes={
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
            "OAuth2": {
                "type": "oauth2",
                "flows": {
                    "password": {
                        "tokenUrl": "/token",
                        "scopes": {
                            "read": "讀取權限",
                            "write": "寫入權限",
                            "admin": "管理員權限",
                        },
                    }
                },
            },
        }
    )

    doc_generator = OpenAPIGenerator(app, config)
    doc_generator.setup_docs()

    # 帶安全性的路由
    @app.post(
        "/api/v1/admin/users",
        tags=["admin"],
        summary="創建用戶",
        dependencies=[],  # 實際應用中添加安全依賴
    )
    async def create_user(
        x_api_key: str = Header(..., description="管理員 API 金鑰")
    ):
        """創建新用戶（需要管理員權限）"""
        return {"message": "用戶已創建"}

    print("\n配置的安全方案:")
    for name, scheme in config.security_schemes.items():
        print(f"  - {name}: {scheme['type']}")

    return app


# ============================================================================
# 主程序
# ============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("FastAPI API 文檔範例")
    print("=" * 80)

    # 運行範例
    example_1_basic_setup()
    example_2_full_configuration()
    app = example_3_complete_api()
    example_4_export_docs()
    example_5_security_schemes()

    print("\n" + "=" * 80)
    print("範例完成！")
    print("=" * 80)
    print("""
主要功能:

1. 文檔配置
   - 自訂標題、描述、版本
   - 聯絡資訊和授權
   - 伺服器配置

2. Swagger UI
   - 互動式 API 測試
   - 自訂顯示選項
   - 請求/回覆範例

3. ReDoc
   - 美觀的文檔展示
   - 自訂主題
   - 響應式設計

4. 文檔導出
   - OpenAPI JSON 規範
   - Markdown 文檔
   - 客戶端 SDK 生成

5. 安全方案
   - API Key 認證
   - Bearer Token
   - OAuth2

使用建議:
    - 開發階段: 啟用完整的 Swagger UI
    - 生產環境: 可以禁用 /docs，僅保留 OpenAPI JSON
    - 文檔維護: 定期導出 Markdown 文檔
    - SDK 生成: 使用 OpenAPI 規範生成客戶端代碼

啟動範例應用:
    # 範例 1
    uvicorn 01_fastapi_integration:example_1_basic_setup --reload

    # 範例 3
    uvicorn 01_fastapi_integration:example_3_complete_api --reload

    # 然後訪問 http://localhost:8000/docs
    """)
