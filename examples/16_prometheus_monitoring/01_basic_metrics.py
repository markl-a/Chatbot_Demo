"""
基本 Prometheus 監控範例
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from fastapi import FastAPI
from src.medical_chatbot.monitoring import setup_prometheus_metrics, get_metrics
import time


def create_app():
    """創建應用"""
    app = FastAPI(title="Prometheus 監控範例")

    # 設置 Prometheus 指標
    setup_prometheus_metrics(app)

    # 業務端點
    @app.get("/")
    async def root():
        return {"message": "Hello World"}

    @app.get("/api/data")
    async def get_data():
        # 模擬處理
        time.sleep(0.1)
        return {"data": [1, 2, 3]}

    @app.post("/api/inference")
    async def inference(prompt: str):
        metrics = get_metrics()

        # 追蹤推理
        start_time = time.time()
        time.sleep(0.5)  # 模擬推理
        duration = time.time() - start_time

        metrics.track_inference(
            model_name="TAIDE-LX-8B", duration=duration, tokens=50, success=True
        )

        return {"response": f"回覆: {prompt}"}

    return app


if __name__ == "__main__":
    print("=" * 80)
    print("Prometheus 監控範例")
    print("=" * 80)
    print("\n啟動應用:")
    print("  uvicorn 01_basic_metrics:app --reload")
    print("\n訪問:")
    print("  http://localhost:8000/metrics - Prometheus 指標")
    print("  http://localhost:8000/api/data - 測試端點")
    print("\nPrometheus 配置:")
    print("""
scrape_configs:
  - job_name: 'medical-chatbot'
    static_configs:
      - targets: ['localhost:8000']
    scrape_interval: 15s
    """)

    app = create_app()
