"""
FastAPI 審計日誌整合範例
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from fastapi import FastAPI
from src.medical_chatbot.audit import AuditLogger, setup_audit_middleware, create_audit_routes


def create_app():
    """創建應用"""
    app = FastAPI(title="審計日誌範例")

    # 創建審計記錄器
    audit_logger = AuditLogger(log_file="logs/audit.log")

    # 設置審計中間件
    setup_audit_middleware(app, audit_logger)

    # 添加審計路由
    router = create_audit_routes(audit_logger)
    app.include_router(router, prefix="/audit", tags=["audit"])

    @app.get("/")
    async def root():
        return {"message": "Hello"}

    @app.post("/api/chat")
    async def chat(message: str):
        return {"response": f"回覆: {message}"}

    return app


if __name__ == "__main__":
    app = create_app()
    print("\n啟動應用:")
    print("  uvicorn 02_fastapi_audit:app --reload")
    print("\n審計端點:")
    print("  GET /audit/summary")
    print("  GET /audit/events")
