"""
FastAPI 健康檢查整合範例

展示如何在 FastAPI 應用中整合健康檢查。
"""
import sys
from pathlib import Path

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from fastapi import FastAPI
from src.medical_chatbot.health import (
    HealthChecker,
    setup_health_routes,
    setup_kubernetes_health_routes,
)


# ============================================================================
# 範例 1: 基本健康檢查整合
# ============================================================================


def example_1_basic_integration():
    """基本健康檢查整合"""
    print("\n" + "=" * 80)
    print("範例 1: 基本健康檢查整合")
    print("=" * 80)

    # 創建應用
    app = FastAPI()

    # 創建健康檢查器
    health_checker = HealthChecker()

    # 設置健康檢查路由
    setup_health_routes(app, health_checker)

    print(f"\n健康檢查端點:")
    print(f"  GET /health - 基本健康檢查")
    print(f"  GET /health/ping - Ping 端點")
    print(f"  GET /health/ready - 就緒檢查")
    print(f"  GET /health/live - 存活檢查")
    print(f"  GET /health/detailed - 詳細健康檢查")
    print(f"  GET /health/summary - 健康摘要")

    print(f"\n啟動應用:")
    print(f"  uvicorn example_1_basic_integration:app --reload")

    return app


# ============================================================================
# 範例 2: Kubernetes 健康檢查
# ============================================================================


def example_2_kubernetes_integration():
    """Kubernetes 健康檢查整合"""
    print("\n" + "=" * 80)
    print("範例 2: Kubernetes 健康檢查整合")
    print("=" * 80)

    app = FastAPI()
    health_checker = HealthChecker()

    # 設置 Kubernetes 風格的健康檢查
    setup_kubernetes_health_routes(app, health_checker)

    print(f"\nKubernetes 健康檢查端點:")
    print(f"  GET /healthz - Liveness probe")
    print(f"  GET /readyz - Readiness probe")

    print(f"\nKubernetes 配置範例:")
    print("""
apiVersion: v1
kind: Pod
metadata:
  name: medical-chatbot
spec:
  containers:
  - name: api
    image: medical-chatbot:latest
    ports:
    - containerPort: 8000
    livenessProbe:
      httpGet:
        path: /healthz
        port: 8000
      initialDelaySeconds: 30
      periodSeconds: 10
      timeoutSeconds: 5
    readinessProbe:
      httpGet:
        path: /readyz
        port: 8000
      initialDelaySeconds: 5
      periodSeconds: 5
      timeoutSeconds: 3
    """)

    return app


# ============================================================================
# 範例 3: 完整的健康檢查整合
# ============================================================================


def example_3_complete_integration():
    """完整的健康檢查整合"""
    print("\n" + "=" * 80)
    print("範例 3: 完整的健康檢查整合")
    print("=" * 80)

    app = FastAPI(
        title="醫療聊天機器人 API",
        description="基於 TAIDE 的醫療問答系統",
    )

    # 模擬組件
    class MockDatabase:
        def get_db(self):
            class DB:
                def execute(self, query):
                    return True

                def __enter__(self):
                    return self

                def __exit__(self, *args):
                    pass

            return DB()

        @property
        def engine(self):
            class Engine:
                @property
                def url(self):
                    return "sqlite:///./medical_chatbot.db"

                @property
                def pool(self):
                    class Pool:
                        def size(self):
                            return 5

                        def checkedout(self):
                            return 2

                    return Pool()

            return Engine()

    class MockRedis:
        def ping(self):
            return True

        def info(self):
            return {
                "redis_version": "7.0.0",
                "used_memory_human": "2.5M",
                "connected_clients": 10,
                "uptime_in_days": 30,
            }

    # 創建健康檢查器（帶組件）
    health_checker = HealthChecker(
        database_manager=MockDatabase(),
        redis_cache=MockRedis(),
    )

    # 設置健康檢查路由
    setup_health_routes(app, health_checker)
    setup_kubernetes_health_routes(app, health_checker)

    # 業務端點
    @app.get("/")
    async def root():
        return {"message": "醫療聊天機器人 API"}

    @app.post("/api/v1/chat")
    async def chat(message: str):
        return {"response": f"回覆: {message}"}

    print(f"\n完整應用端點:")
    print(f"\n業務端點:")
    print(f"  GET  /")
    print(f"  POST /api/v1/chat")
    print(f"\n健康檢查端點:")
    print(f"  GET /health/*")
    print(f"  GET /healthz")
    print(f"  GET /readyz")

    print(f"\n啟動應用:")
    print(f"  uvicorn example_3_complete_integration:app --reload")

    return app


# ============================================================================
# 範例 4: 自訂健康檢查
# ============================================================================


def example_4_custom_checks():
    """自訂健康檢查"""
    print("\n" + "=" * 80)
    print("範例 4: 自訂健康檢查")
    print("=" * 80)

    app = FastAPI()

    from src.medical_chatbot.health import ComponentStatus, HealthStatus

    # 創建健康檢查器
    health_checker = HealthChecker()

    # 添加自訂檢查
    def check_external_api() -> ComponentStatus:
        """檢查外部 API"""
        try:
            import requests
            import time

            start_time = time.time()
            response = requests.get("https://httpbin.org/status/200", timeout=5)
            response_time = time.time() - start_time

            if response.status_code == 200:
                return ComponentStatus(
                    name="external_api",
                    status=HealthStatus.HEALTHY,
                    message="外部 API 正常",
                    response_time=response_time,
                )
            else:
                return ComponentStatus(
                    name="external_api",
                    status=HealthStatus.UNHEALTHY,
                    message=f"外部 API 異常: {response.status_code}",
                )
        except Exception as e:
            return ComponentStatus(
                name="external_api",
                status=HealthStatus.UNHEALTHY,
                message=f"外部 API 檢查失敗: {str(e)}",
            )

    # 註冊自訂檢查
    health_checker.register_check("external_api", check_external_api)

    # 設置健康檢查路由
    setup_health_routes(app, health_checker)

    print(f"\n註冊的健康檢查:")
    for check_name in health_checker.checks.keys():
        print(f"  - {check_name}")

    return app


# ============================================================================
# 範例 5: 監控整合
# ============================================================================


def example_5_monitoring_integration():
    """監控整合"""
    print("\n" + "=" * 80)
    print("範例 5: 監控整合")
    print("=" * 80)

    app = FastAPI()
    health_checker = HealthChecker()
    setup_health_routes(app, health_checker)

    # 添加自訂監控端點
    @app.get("/metrics")
    async def metrics():
        """Prometheus 格式的指標"""
        report = health_checker.get_health_report()

        # 生成 Prometheus 格式的指標
        metrics_lines = []

        # 健康狀態指標
        status_value = {
            "healthy": 1,
            "degraded": 0.5,
            "unhealthy": 0,
        }

        overall_value = status_value.get(report["status"], 0)
        metrics_lines.append(f"# HELP health_status Overall health status")
        metrics_lines.append(f"# TYPE health_status gauge")
        metrics_lines.append(f'health_status{{service="medical_chatbot"}} {overall_value}')

        # 組件健康狀態
        metrics_lines.append(f"\n# HELP component_health Component health status")
        metrics_lines.append(f"# TYPE component_health gauge")

        for name, check in report["checks"].items():
            value = status_value.get(check["status"], 0)
            metrics_lines.append(
                f'component_health{{component="{name}"}} {value}'
            )

        # 回應時間
        metrics_lines.append(f"\n# HELP component_response_time Component response time in seconds")
        metrics_lines.append(f"# TYPE component_response_time gauge")

        for name, check in report["checks"].items():
            if check.get("response_time"):
                metrics_lines.append(
                    f'component_response_time{{component="{name}"}} {check["response_time"]}'
                )

        return "\n".join(metrics_lines)

    print(f"\n監控端點:")
    print(f"  GET /health/detailed - 健康檢查")
    print(f"  GET /metrics - Prometheus 指標")

    print(f"\nPrometheus 配置:")
    print("""
scrape_configs:
  - job_name: 'medical-chatbot'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
    scrape_interval: 15s
    """)

    return app


# ============================================================================
# 範例 6: 健康檢查儀表板
# ============================================================================


def example_6_health_dashboard():
    """健康檢查儀表板"""
    print("\n" + "=" * 80)
    print("範例 6: 健康檢查儀表板")
    print("=" * 80)

    app = FastAPI()
    health_checker = HealthChecker()
    setup_health_routes(app, health_checker)

    from fastapi.responses import HTMLResponse

    @app.get("/dashboard", response_class=HTMLResponse)
    async def dashboard():
        """健康檢查儀表板"""
        report = health_checker.get_health_report()

        # 生成 HTML
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>健康檢查儀表板</title>
            <meta charset="utf-8">
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    margin: 20px;
                    background-color: #f5f5f5;
                }}
                .container {{
                    max-width: 1200px;
                    margin: 0 auto;
                    background-color: white;
                    padding: 20px;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                h1 {{
                    color: #333;
                }}
                .status {{
                    padding: 10px 20px;
                    border-radius: 4px;
                    display: inline-block;
                    font-weight: bold;
                    margin: 10px 0;
                }}
                .healthy {{ background-color: #4CAF50; color: white; }}
                .degraded {{ background-color: #FF9800; color: white; }}
                .unhealthy {{ background-color: #f44336; color: white; }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 20px;
                }}
                th, td {{
                    padding: 12px;
                    text-align: left;
                    border-bottom: 1px solid #ddd;
                }}
                th {{
                    background-color: #f2f2f2;
                    font-weight: bold;
                }}
                .component-healthy {{ color: #4CAF50; }}
                .component-degraded {{ color: #FF9800; }}
                .component-unhealthy {{ color: #f44336; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🏥 醫療聊天機器人 - 健康檢查儀表板</h1>

                <div class="status {report['status']}">
                    整體狀態: {report['status'].upper()}
                </div>

                <p>時間: {report['timestamp']}</p>
                <p>總檢查時間: {report['response_time']:.4f}s</p>

                <h2>摘要</h2>
                <ul>
                    <li>總檢查數: {report['summary']['total_checks']}</li>
                    <li>健康: {report['summary']['healthy']}</li>
                    <li>降級: {report['summary']['degraded']}</li>
                    <li>不健康: {report['summary']['unhealthy']}</li>
                </ul>

                <h2>組件詳情</h2>
                <table>
                    <thead>
                        <tr>
                            <th>組件</th>
                            <th>狀態</th>
                            <th>訊息</th>
                            <th>回應時間</th>
                        </tr>
                    </thead>
                    <tbody>
        """

        for name, check in report["checks"].items():
            status_class = f"component-{check['status']}"
            response_time = (
                f"{check['response_time']:.4f}s" if check.get("response_time") else "N/A"
            )

            html += f"""
                        <tr>
                            <td><strong>{name}</strong></td>
                            <td class="{status_class}">{check['status'].upper()}</td>
                            <td>{check['message']}</td>
                            <td>{response_time}</td>
                        </tr>
            """

        html += """
                    </tbody>
                </table>

                <p style="margin-top: 20px; color: #666;">
                    <small>自動重新整理: <span id="countdown">30</span>秒</small>
                </p>
            </div>

            <script>
                // 自動重新整理
                let countdown = 30;
                setInterval(() => {
                    countdown--;
                    document.getElementById('countdown').textContent = countdown;
                    if (countdown <= 0) {
                        location.reload();
                    }
                }, 1000);
            </script>
        </body>
        </html>
        """

        return html

    print(f"\n儀表板端點:")
    print(f"  GET /dashboard - HTML 儀表板")
    print(f"\n訪問: http://localhost:8000/dashboard")

    return app


# ============================================================================
# 主程序
# ============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("FastAPI 健康檢查整合範例")
    print("=" * 80)

    # 運行範例
    app1 = example_1_basic_integration()
    app2 = example_2_kubernetes_integration()
    app = example_3_complete_integration()
    app4 = example_4_custom_checks()
    app5 = example_5_monitoring_integration()
    app6 = example_6_health_dashboard()

    print("\n" + "=" * 80)
    print("範例完成！")
    print("=" * 80)
    print("""
主要功能:

1. 健康檢查端點
   - GET /health - 基本檢查
   - GET /health/ready - 就緒檢查
   - GET /health/live - 存活檢查
   - GET /health/detailed - 詳細檢查

2. Kubernetes 整合
   - GET /healthz - Liveness probe
   - GET /readyz - Readiness probe
   - 標準 K8s 健康檢查

3. 組件檢查
   - 資料庫
   - Redis
   - 模型
   - 磁碟
   - 記憶體

4. 監控整合
   - Prometheus 指標
   - 自訂監控端點
   - 健康狀態導出

5. 儀表板
   - HTML 可視化
   - 自動重新整理
   - 狀態展示

啟動範例:
    # 基本整合
    uvicorn 02_fastapi_integration:example_1_basic_integration --reload

    # 完整整合
    uvicorn 02_fastapi_integration:example_3_complete_integration --reload

    # 儀表板
    uvicorn 02_fastapi_integration:example_6_health_dashboard --reload

測試端點:
    # 基本健康檢查
    curl http://localhost:8000/health

    # 詳細健康檢查
    curl http://localhost:8000/health/detailed

    # 檢查特定組件
    curl http://localhost:8000/health/component/database

    # Kubernetes liveness
    curl http://localhost:8000/healthz

    # 儀表板
    open http://localhost:8000/dashboard
    """)
