# 配置管理系統

完整的配置管理解決方案，支援多環境、環境變數和 FastAPI 整合。

## 功能特性

### 1. 環境管理
- ✅ 多環境支援（開發、測試、生產）
- ✅ 環境特定配置檔案
- ✅ 環境變數優先級系統
- ✅ .env 檔案支援

### 2. 配置驗證
- ✅ Pydantic 自動驗證
- ✅ 類型檢查和轉換
- ✅ 範圍限制
- ✅ 自訂驗證器

### 3. FastAPI 整合
- ✅ 依賴注入
- ✅ 配置端點
- ✅ 啟動/關閉事件
- ✅ 訪問控制

### 4. 模板生成
- ✅ 自動生成 .env 模板
- ✅ 包含所有配置選項
- ✅ 附帶說明文檔

## 快速開始

### 基本使用

```python
from src.medical_chatbot.config import Settings

# 創建配置
settings = Settings()

# 訪問配置
print(settings.DATABASE_URL)
print(settings.MODEL_NAME)
print(settings.ENVIRONMENT)
```

### FastAPI 整合

```python
from fastapi import FastAPI, Depends
from src.medical_chatbot.config import Settings, get_settings, setup_config_integration

app = FastAPI()

# 設置配置整合
setup_config_integration(app)

@app.get("/")
async def root(settings: Settings = Depends(get_settings)):
    return {
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }
```

## 配置選項

### 應用設定

```python
# 應用資訊
APP_NAME="醫療聊天機器人 API"
APP_VERSION="1.0.0"
ENVIRONMENT="development"  # development, staging, production

# 運行模式
DEBUG=true
TESTING=false

# API 設定
API_HOST="0.0.0.0"
API_PORT=8000
```

### 資料庫配置

```python
# PostgreSQL
DATABASE_URL="postgresql://user:password@localhost:5432/medical_chatbot"

# SQLite
DATABASE_URL="sqlite:///./medical_chatbot.db"

# 連接池
DATABASE_POOL_SIZE=5
DATABASE_MAX_OVERFLOW=10
DATABASE_ECHO=false
```

### Redis 配置

```python
REDIS_HOST="localhost"
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=""
REDIS_MAX_CONNECTIONS=50
```

### 模型配置

```python
MODEL_NAME="TAIDE-LX-8B"
DEVICE="cuda"  # cuda, cpu
MAX_LENGTH=256
TEMPERATURE=0.7
TOP_K=50
TOP_P=0.9
BATCH_SIZE=8
```

### 快取配置

```python
CACHE_STRATEGY="multi_tier"  # memory_only, redis_only, multi_tier
CACHE_TTL=300  # 秒
CACHE_MAX_SIZE=1000
```

### 速率限制配置

```python
RATE_LIMIT_STRATEGY="sliding_window"  # fixed_window, sliding_window, token_bucket
RATE_LIMIT_DEFAULT=100  # 請求數
RATE_LIMIT_WINDOW=60  # 秒
```

### 安全配置

```python
SECRET_KEY="your-secret-key-change-in-production"
API_KEYS_ENABLED=false
CORS_ORIGINS='["http://localhost:3000"]'
```

## 環境檔案

### 檔案結構

```
project/
├── .env                    # 預設環境變數（不提交）
├── .env.example           # 範例檔案（可提交）
├── .env.development       # 開發環境（不提交）
├── .env.staging          # 測試環境（不提交）
├── .env.production       # 生產環境（不提交）
└── config/
    ├── .env.development.local  # 本地覆蓋（不提交）
    └── .env.production.local   # 本地覆蓋（不提交）
```

### 優先級順序

1. 環境變數（最高優先級）
2. `.env.{ENVIRONMENT}.local`
3. `.env.{ENVIRONMENT}`
4. `.env`
5. 預設值（最低優先級）

### 生成模板

```python
from src.medical_chatbot.config import EnvLoader

loader = EnvLoader()

# 生成開發環境模板
loader.generate_env_template("development")

# 生成生產環境模板
loader.generate_env_template("production")
```

生成的檔案：
- `config/.env.development.template`
- `config/.env.production.template`

## FastAPI 整合

### 完整設置

```python
from fastapi import FastAPI
from src.medical_chatbot.config import setup_config_integration

app = FastAPI()

# 一鍵設置（包含配置端點）
setup_config_integration(app, include_routes=True)
```

這會自動設置：
- 配置單例
- 啟動/關閉事件
- 配置端點（`/config/*`）

### 配置端點

自動註冊的端點：

- **GET `/config/info`** - 應用資訊
- **GET `/config/database`** - 資料庫配置
- **GET `/config/redis`** - Redis 配置
- **GET `/config/model`** - 模型配置
- **GET `/config/cache`** - 快取配置
- **GET `/config/rate-limit`** - 速率限制配置
- **POST `/config/reload`** - 重新加載配置（僅調試模式）

### 依賴注入

#### 獲取完整配置

```python
from fastapi import Depends
from src.medical_chatbot.config import Settings, get_settings

@app.get("/info")
async def info(settings: Settings = Depends(get_settings)):
    return {
        "app_name": settings.APP_NAME,
        "environment": settings.ENVIRONMENT,
    }
```

#### 獲取特定配置

```python
from src.medical_chatbot.config import (
    get_database_url,
    get_redis_config,
    get_model_config,
    get_rate_limit_config,
)

@app.get("/database/url")
async def get_db_url(url: str = Depends(get_database_url)):
    return {"database_url": url}

@app.get("/redis/config")
async def get_redis(config: dict = Depends(get_redis_config)):
    return config
```

### 訪問控制

限制特定環境的端點：

```python
from src.medical_chatbot.config import (
    require_debug_mode,
    require_production_mode,
)

# 僅調試模式
@app.get("/debug/info", dependencies=[Depends(require_debug_mode)])
async def debug_info(settings: Settings = Depends(get_settings)):
    return settings.dict()

# 僅生產模式
@app.post("/admin/operation", dependencies=[Depends(require_production_mode)])
async def admin_operation():
    return {"status": "ok"}
```

## 配置驅動的功能

### 使用配置的預設值

```python
from pydantic import BaseModel

class ChatRequest(BaseModel):
    message: str
    max_length: int = None
    temperature: float = None

@app.post("/chat")
async def chat(
    request: ChatRequest,
    settings: Settings = Depends(get_settings),
):
    # 使用配置的預設值
    max_length = request.max_length or settings.MAX_LENGTH
    temperature = request.temperature or settings.TEMPERATURE

    return {
        "response": "處理中...",
        "config": {
            "max_length": max_length,
            "temperature": temperature,
            "model": settings.MODEL_NAME,
        }
    }
```

### 根據環境啟用功能

```python
@app.on_event("startup")
async def startup_event():
    settings = get_settings()

    if settings.ENVIRONMENT == "production":
        # 生產環境特定初始化
        pass
    elif settings.DEBUG:
        # 調試模式特定初始化
        pass
```

## 配置驗證

### 自動驗證

Pydantic 會自動驗證：

```python
# 類型驗證
API_PORT=8000  # ✓ int
API_PORT="abc"  # ✗ ValidationError

# 範圍驗證
DATABASE_POOL_SIZE=5  # ✓ 在範圍內
DATABASE_POOL_SIZE=0  # ✗ 必須 >= 1
```

### 自訂驗證器

```python
from pydantic import validator

class Settings(BaseSettings):
    SECRET_KEY: str
    ENVIRONMENT: str

    @validator("SECRET_KEY")
    def validate_secret_key(cls, v: str, values: dict) -> str:
        if values.get("ENVIRONMENT") == "production":
            if v == "your-secret-key-change-in-production":
                raise ValueError("生產環境必須設置 SECRET_KEY")
        return v
```

## 環境變數載入

### EnvLoader 類

```python
from src.medical_chatbot.config import EnvLoader

loader = EnvLoader()

# 加載特定環境
env_vars = loader.load_env("development")

# 獲取環境檔案路徑
env_file = loader.get_env_file_path("production")

# 生成模板
template = loader.generate_env_template("staging")
```

### 手動加載

```python
import os
from pathlib import Path
from dotenv import load_dotenv

# 加載 .env 檔案
load_dotenv()

# 加載特定檔案
load_dotenv(".env.production")

# 覆蓋現有環境變數
load_dotenv(override=True)
```

## 生產環境最佳實踐

### 1. 安全配置

```python
# .env.production
SECRET_KEY="強隨機金鑰"
DATABASE_URL="postgresql://user:password@db.example.com/dbname"
REDIS_PASSWORD="強密碼"
DEBUG=false
TESTING=false
```

### 2. 敏感資訊管理

**永遠不要**提交包含敏感資訊的檔案到版本控制：

```gitignore
# .gitignore
.env
.env.local
.env.*.local
.env.development
.env.staging
.env.production
```

**可以**提交範例檔案：

```bash
# .env.example
SECRET_KEY=your-secret-key-change-in-production
DATABASE_URL=postgresql://user:password@localhost/medical_chatbot
REDIS_PASSWORD=
```

### 3. 容器化部署

```dockerfile
# Dockerfile
FROM python:3.9

# 複製應用
COPY . /app
WORKDIR /app

# 安裝依賴
RUN pip install -r requirements.txt

# 環境變數通過 docker run 或 docker-compose 傳入
# 不要在映像中硬編碼敏感資訊

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=production
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_HOST=redis
      - SECRET_KEY=${SECRET_KEY}
    env_file:
      - .env.production
```

### 4. 配置驗證

啟動時驗證關鍵配置：

```python
@app.on_event("startup")
async def validate_config():
    settings = get_settings()

    # 生產環境檢查
    if settings.ENVIRONMENT == "production":
        assert settings.SECRET_KEY != "your-secret-key-change-in-production"
        assert not settings.DEBUG
        assert not settings.TESTING
        assert "postgresql://" in settings.DATABASE_URL

        logger.info("生產環境配置驗證通過")
```

## 常見問題

### Q: 如何切換環境？

A: 設置 `ENVIRONMENT` 環境變數：

```bash
# 方法 1: 環境變數
export ENVIRONMENT=production
python main.py

# 方法 2: .env 檔案
echo "ENVIRONMENT=production" > .env
python main.py

# 方法 3: 命令行
ENVIRONMENT=production python main.py
```

### Q: 配置優先級是什麼？

A:
1. 環境變數（最高）
2. `.env.{ENVIRONMENT}.local`
3. `.env.{ENVIRONMENT}`
4. `.env`
5. 預設值（最低）

### Q: 如何重新加載配置？

A: 在調試模式下調用 `/config/reload` 端點：

```bash
curl -X POST http://localhost:8000/config/reload
```

或在代碼中：

```python
from src.medical_chatbot.config import get_settings

# 清除快取
get_settings.cache_clear()

# 重新加載
settings = get_settings()
```

### Q: 如何添加新配置？

A:

1. 在 `Settings` 類中添加欄位：

```python
class Settings(BaseSettings):
    # 新配置
    NEW_FEATURE_ENABLED: bool = Field(default=False)
```

2. 在 .env 檔案中設置：

```bash
NEW_FEATURE_ENABLED=true
```

3. 使用配置：

```python
settings = get_settings()
if settings.NEW_FEATURE_ENABLED:
    # 啟用功能
    pass
```

### Q: 如何處理列表和字典配置？

A: 使用 JSON 字符串：

```python
# .env
CORS_ORIGINS='["http://localhost:3000", "http://localhost:8080"]'
ALLOWED_HOSTS='{"web": "example.com", "api": "api.example.com"}'
```

```python
import json
from pydantic import validator

class Settings(BaseSettings):
    CORS_ORIGINS: List[str] = []

    @validator("CORS_ORIGINS", pre=True)
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v
```

## 範例截圖

### 配置資訊端點

```bash
$ curl http://localhost:8000/config/info
{
  "environment": "development",
  "debug": true,
  "testing": false,
  "app_name": "醫療聊天機器人 API",
  "app_version": "1.0.0",
  "model_name": "TAIDE-LX-8B",
  "device": "cuda"
}
```

### 模型配置端點

```bash
$ curl http://localhost:8000/config/model
{
  "name": "TAIDE-LX-8B",
  "device": "cuda",
  "max_length": 256,
  "temperature": 0.7,
  "top_k": 50,
  "top_p": 0.9,
  "batch_size": 8
}
```

## 參考資源

- [Pydantic Settings](https://pydantic-docs.helpmanual.io/usage/settings/)
- [python-dotenv](https://github.com/theskumar/python-dotenv)
- [FastAPI Dependency Injection](https://fastapi.tiangolo.com/tutorial/dependencies/)
- [12 Factor App - Config](https://12factor.net/config)

## 授權

MIT License
