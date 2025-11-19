# API 文檔自動生成

FastAPI OpenAPI 文檔自動生成和自訂工具。

## 功能特性

### 1. 自動生成 OpenAPI 規範
- ✅ 完整的 OpenAPI 3.0 支援
- ✅ 自動從 FastAPI 路由生成
- ✅ Pydantic 模型整合
- ✅ 範例和描述

### 2. Swagger UI
- ✅ 互動式 API 測試
- ✅ 自訂顯示選項
- ✅ 請求/回覆範例
- ✅ 認證測試

### 3. ReDoc
- ✅ 美觀的文檔展示
- ✅ 自訂主題
- ✅ 響應式設計
- ✅ 下載 OpenAPI 規範

### 4. 文檔導出
- ✅ OpenAPI JSON 導出
- ✅ Markdown 文檔生成
- ✅ 客戶端 SDK 生成

## 快速開始

### 基本使用

```python
from fastapi import FastAPI
from src.medical_chatbot.docs import OpenAPIGenerator, DocsConfig

# 創建 FastAPI 應用
app = FastAPI()

# 配置文檔
config = DocsConfig(
    title="我的 API",
    description="API 說明",
    version="1.0.0",
)

# 設置文檔
doc_generator = OpenAPIGenerator(app, config)
doc_generator.setup_docs()

# 定義路由
@app.get("/")
async def root():
    return {"message": "Hello World"}
```

啟動應用並訪問:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## 詳細配置

### 1. 文檔配置

```python
from src.medical_chatbot.docs import DocsConfig
from src.medical_chatbot.docs.docs_config import ContactInfo, LicenseInfo, ServerInfo

config = DocsConfig(
    # 基本資訊
    title="醫療聊天機器人 API",
    description="基於 TAIDE 的醫療問答系統",
    version="1.0.0",

    # 聯絡資訊
    contact=ContactInfo(
        name="AI 團隊",
        email="ai@example.com",
        url="https://example.com",
    ),

    # 授權資訊
    license_info=LicenseInfo(
        name="MIT",
        url="https://opensource.org/licenses/MIT",
    ),

    # 伺服器
    servers=[
        ServerInfo(url="http://localhost:8000", description="開發環境"),
        ServerInfo(url="https://api.example.com", description="生產環境"),
    ],

    # 標籤分組
    tags_metadata=[
        {
            "name": "chat",
            "description": "聊天對話端點",
        },
        {
            "name": "models",
            "description": "模型管理端點",
        },
    ],
)
```

### 2. Swagger UI 自訂

```python
from src.medical_chatbot.docs.docs_config import SwaggerUIConfig

swagger_config = SwaggerUIConfig(
    display_request_duration=True,  # 顯示請求時間
    display_operation_id=False,     # 隱藏操作 ID
    default_model_expand_depth=2,   # 模型展開深度
)

doc_generator.setup_docs(swagger_ui_config=swagger_config)
```

### 3. ReDoc 自訂

```python
from src.medical_chatbot.docs.docs_config import ReDocConfig

redoc_config = ReDocConfig(
    hide_download_button=False,  # 顯示下載按鈕
    expand_responses="200,201",  # 預設展開的回覆
    theme={
        "colors": {
            "primary": {
                "main": "#4CAF50",  # 主色調
            }
        }
    },
)

doc_generator.setup_docs(redoc_config=redoc_config)
```

### 4. 安全方案

```python
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
            "description": "JWT Token",
        },
    }
)
```

## Pydantic 模型整合

### 請求模型

```python
from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    """聊天請求"""

    message: str = Field(..., description="用戶消息", example="什麼是高血壓？")
    max_length: int = Field(256, description="最大生成長度", ge=1, le=2048)
    temperature: float = Field(0.7, description="生成溫度", ge=0.0, le=2.0)

    class Config:
        json_schema_extra = {
            "example": {
                "message": "什麼是高血壓？",
                "max_length": 256,
                "temperature": 0.7,
            }
        }
```

### 回覆模型

```python
class ChatResponse(BaseModel):
    """聊天回覆"""

    response: str = Field(..., description="機器人回覆")
    session_id: str = Field(..., description="會話 ID")
    model: str = Field(..., description="使用的模型")
    generation_time: float = Field(..., description="生成時間（秒）")

    class Config:
        json_schema_extra = {
            "example": {
                "response": "高血壓是一種血壓持續高於正常值的慢性疾病...",
                "session_id": "session-123",
                "model": "TAIDE-LX-8B",
                "generation_time": 0.523,
            }
        }
```

### 路由定義

```python
@app.post(
    "/api/v1/chat",
    response_model=ChatResponse,
    tags=["chat"],
    summary="聊天對話",
    description="發送消息到聊天機器人並獲取回覆",
    responses={
        200: {"description": "成功回覆", "model": ChatResponse},
        400: {"description": "請求參數錯誤"},
        429: {"description": "請求過於頻繁"},
    },
)
async def chat(request: ChatRequest):
    """
    ## 聊天對話

    發送消息到聊天機器人並獲取智能回覆。

    ### 參數說明

    - **message**: 用戶消息（必需）
    - **max_length**: 最大生成長度
    - **temperature**: 生成溫度（0-2）

    ### 範例

    \`\`\`python
    import requests

    response = requests.post(
        "http://localhost:8000/api/v1/chat",
        json={"message": "什麼是高血壓？"}
    )
    \`\`\`
    """
    pass
```

## 文檔導出

### 導出 OpenAPI JSON

```python
# 導出規範
doc_generator.export_openapi_spec("openapi.json")
```

輸出:
```json
{
  "openapi": "3.0.2",
  "info": {
    "title": "醫療聊天機器人 API",
    "version": "1.0.0",
    ...
  },
  "paths": {
    "/api/v1/chat": {
      "post": {
        ...
      }
    }
  }
}
```

### 導出 Markdown

```python
# 導出 Markdown 文檔
doc_generator.export_markdown_docs("API_DOCS.md")
```

輸出:
```markdown
# 醫療聊天機器人 API

基於 TAIDE 的醫療問答系統

**版本**: 1.0.0

## API 端點

### `POST` /api/v1/chat

聊天對話

**參數**:
| 名稱 | 類型 | 必需 | 說明 |
|------|------|------|------|
| message | string | 是 | 用戶消息 |
...
```

### 生成客戶端 SDK

```python
# 生成 Python SDK
doc_generator.generate_client_sdk(
    language="python",
    output_dir="./python-sdk"
)

# 生成 JavaScript SDK
doc_generator.generate_client_sdk(
    language="javascript",
    output_dir="./js-sdk"
)
```

**注意**: 需要安裝 `openapi-generator-cli`:
```bash
npm install -g @openapitools/openapi-generator-cli
```

## 最佳實踐

### 1. 詳細的描述

```python
@app.post(
    "/api/v1/chat",
    summary="聊天對話",  # 簡短摘要
    description="""
    ## 詳細說明

    這個端點提供智能聊天功能...

    ### 使用場景
    - 醫療諮詢
    - 健康建議
    - 疾病資訊查詢
    """,  # 詳細描述（支援 Markdown）
)
async def chat(request: ChatRequest):
    pass
```

### 2. 完整的範例

```python
class ChatRequest(BaseModel):
    message: str

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "summary": "簡單問題",
                    "value": {"message": "什麼是高血壓？"},
                },
                {
                    "summary": "複雜問題",
                    "value": {
                        "message": "高血壓患者應該如何調整飲食？",
                        "max_length": 512,
                    },
                },
            ]
        }
```

### 3. 標籤組織

```python
config = DocsConfig(
    tags_metadata=[
        {
            "name": "health",
            "description": "健康檢查相關端點",
        },
        {
            "name": "chat",
            "description": "聊天對話端點",
            "externalDocs": {
                "description": "聊天 API 詳細文檔",
                "url": "https://docs.example.com/chat",
            },
        },
    ]
)
```

### 4. 錯誤回覆

```python
class ErrorResponse(BaseModel):
    error: str
    message: str
    details: Optional[dict] = None

@app.post(
    "/api/v1/chat",
    responses={
        400: {
            "description": "請求參數錯誤",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "example": {
                        "error": "ValidationError",
                        "message": "message 欄位不能為空",
                        "details": {"field": "message"},
                    }
                }
            },
        },
        429: {
            "description": "請求過於頻繁",
            "model": ErrorResponse,
        },
    },
)
async def chat(request: ChatRequest):
    pass
```

## 生產環境配置

### 禁用 Swagger UI

```python
config = DocsConfig(
    docs_url=None,  # 禁用 Swagger UI
    redoc_url="/docs",  # 僅保留 ReDoc
    openapi_url="/api/openapi.json",  # OpenAPI JSON 仍然可用
)
```

### 自訂域名

```python
config = DocsConfig(
    servers=[
        ServerInfo(
            url="https://api.medical-chat.com",
            description="生產環境",
        ),
        ServerInfo(
            url="https://dev-api.medical-chat.com",
            description="開發環境",
        ),
    ]
)
```

### 版本控制

```python
# API v1
app_v1 = FastAPI()
config_v1 = DocsConfig(
    title="API v1",
    version="1.0.0",
    openapi_url="/api/v1/openapi.json",
    docs_url="/api/v1/docs",
)

# API v2
app_v2 = FastAPI()
config_v2 = DocsConfig(
    title="API v2",
    version="2.0.0",
    openapi_url="/api/v2/openapi.json",
    docs_url="/api/v2/docs",
)
```

## 常見問題

### Q: 如何隱藏特定端點？

A: 使用 `include_in_schema=False`:

```python
@app.get("/internal/health", include_in_schema=False)
async def internal_health():
    pass
```

### Q: 如何自訂 Swagger UI 樣式？

A: 提供自訂 CSS:

```python
swagger_config = SwaggerUIConfig(
    custom_css="/static/custom-swagger.css"
)
```

### Q: 如何添加認證測試？

A: 配置安全方案並在 Swagger UI 中使用「Authorize」按鈕:

```python
config = DocsConfig(
    security_schemes={
        "APIKeyHeader": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
        }
    }
)

# 在路由中應用
@app.get("/protected", dependencies=[Depends(verify_api_key)])
async def protected_route():
    pass
```

### Q: 如何生成多語言文檔？

A: 導出 OpenAPI JSON 後使用翻譯工具，或創建多個配置:

```python
# 英文文檔
config_en = DocsConfig(
    title="Medical Chatbot API",
    description="Medical Q&A System based on TAIDE",
)

# 中文文檔
config_zh = DocsConfig(
    title="醫療聊天機器人 API",
    description="基於 TAIDE 的醫療問答系統",
)
```

## 範例截圖

### Swagger UI
![Swagger UI](https://fastapi.tiangolo.com/img/index/index-01-swagger-ui-simple.png)

### ReDoc
![ReDoc](https://fastapi.tiangolo.com/img/index/index-02-redoc-simple.png)

## 依賴套件

```bash
# 基礎依賴（FastAPI 已包含）
pip install fastapi pydantic

# SDK 生成（可選）
npm install -g @openapitools/openapi-generator-cli
```

## 參考資源

- [FastAPI 文檔](https://fastapi.tiangolo.com/)
- [OpenAPI 規範](https://swagger.io/specification/)
- [Swagger UI](https://swagger.io/tools/swagger-ui/)
- [ReDoc](https://redocly.com/redoc)

## 授權

MIT License
