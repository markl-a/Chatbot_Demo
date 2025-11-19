# 審計日誌系統

完整的審計日誌解決方案，支援操作追蹤、安全審計和合規性記錄。

## 功能特性

- ✅ 多類型事件記錄（用戶、API、資料、安全、系統、模型）
- ✅ 多等級審計（INFO、WARNING、ERROR、CRITICAL、SECURITY）
- ✅ 多目標輸出（控制台、檔案、資料庫）
- ✅ FastAPI 自動審計中間件
- ✅ 事件查詢和分析
- ✅ 審計報告生成和導出

## 快速開始

### 基本使用

```python
from src.medical_chatbot.audit import AuditLogger

audit_logger = AuditLogger(log_file="logs/audit.log")

# 記錄用戶登入
audit_logger.log_user_login(user_id="user123", ip_address="192.168.1.1")

# 記錄 API 調用
audit_logger.log_api_call(
    endpoint="/api/chat",
    method="POST",
    status_code=200,
)
```

### FastAPI 整合

```python
from fastapi import FastAPI
from src.medical_chatbot.audit import AuditLogger, setup_audit_middleware

app = FastAPI()
audit_logger = AuditLogger()
setup_audit_middleware(app, audit_logger)
```

## 事件類型

- 用戶操作：USER_LOGIN, USER_LOGOUT, USER_REGISTER
- API 操作：API_CALL, API_ERROR, API_TIMEOUT
- 資料操作：DATA_CREATE, DATA_READ, DATA_UPDATE, DATA_DELETE
- 安全事件：AUTH_SUCCESS, AUTH_FAILURE, PERMISSION_DENIED
- 系統事件：SYSTEM_START, SYSTEM_STOP, SYSTEM_ERROR
- 模型操作：MODEL_LOAD, MODEL_GENERATE, MODEL_ERROR

## 審計等級

- INFO：一般資訊
- WARNING：警告
- ERROR：錯誤
- CRITICAL：嚴重
- SECURITY：安全事件

## 授權

MIT License
