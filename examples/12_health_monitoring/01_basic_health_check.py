"""
基本健康檢查範例

展示如何使用健康檢查系統。
"""
import sys
from pathlib import Path

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.medical_chatbot.health import HealthChecker, HealthStatus, ComponentStatus


# ============================================================================
# 範例 1: 基本健康檢查
# ============================================================================


def example_1_basic_check():
    """基本健康檢查"""
    print("\n" + "=" * 80)
    print("範例 1: 基本健康檢查")
    print("=" * 80)

    # 創建健康檢查器（不配置外部組件）
    health_checker = HealthChecker()

    print(f"\n可用的健康檢查:")
    for check_name in health_checker.checks.keys():
        print(f"  - {check_name}")

    # 檢查磁碟空間
    print(f"\n檢查磁碟空間...")
    disk_status = health_checker.check_disk_space()

    print(f"  狀態: {disk_status.status.value}")
    print(f"  訊息: {disk_status.message}")
    print(f"  回應時間: {disk_status.response_time:.4f}s")
    print(f"  詳細資訊: {disk_status.details}")

    # 檢查記憶體
    print(f"\n檢查記憶體...")
    memory_status = health_checker.check_memory()

    print(f"  狀態: {memory_status.status.value}")
    print(f"  訊息: {memory_status.message}")
    print(f"  詳細資訊: {memory_status.details}")


# ============================================================================
# 範例 2: 檢查所有組件
# ============================================================================


def example_2_check_all():
    """檢查所有組件"""
    print("\n" + "=" * 80)
    print("範例 2: 檢查所有組件")
    print("=" * 80)

    health_checker = HealthChecker()

    # 檢查所有組件
    print(f"\n檢查所有組件...")
    results = health_checker.check_all()

    print(f"\n檢查結果:")
    for name, status in results.items():
        status_emoji = {
            HealthStatus.HEALTHY: "✓",
            HealthStatus.DEGRADED: "⚠",
            HealthStatus.UNHEALTHY: "✗",
        }
        emoji = status_emoji.get(status.status, "?")

        print(f"  {emoji} {name}:")
        print(f"      狀態: {status.status.value}")
        print(f"      訊息: {status.message}")
        if status.response_time:
            print(f"      回應時間: {status.response_time:.4f}s")


# ============================================================================
# 範例 3: 健康報告生成
# ============================================================================


def example_3_health_report():
    """健康報告生成"""
    print("\n" + "=" * 80)
    print("範例 3: 健康報告生成")
    print("=" * 80)

    health_checker = HealthChecker()

    # 生成健康報告
    print(f"\n生成健康報告...")
    report = health_checker.get_health_report()

    print(f"\n整體狀態: {report['status']}")
    print(f"時間戳記: {report['timestamp']}")
    print(f"總回應時間: {report['response_time']:.4f}s")

    print(f"\n摘要:")
    print(f"  總檢查數: {report['summary']['total_checks']}")
    print(f"  健康: {report['summary']['healthy']}")
    print(f"  降級: {report['summary']['degraded']}")
    print(f"  不健康: {report['summary']['unhealthy']}")

    print(f"\n各組件狀態:")
    for name, check in report['checks'].items():
        print(f"  {name}: {check['status']}")


# ============================================================================
# 範例 4: 自訂健康檢查
# ============================================================================


def example_4_custom_check():
    """自訂健康檢查"""
    print("\n" + "=" * 80)
    print("範例 4: 自訂健康檢查")
    print("=" * 80)

    health_checker = HealthChecker()

    # 定義自訂檢查
    def check_api_endpoint() -> ComponentStatus:
        """檢查外部 API 端點"""
        try:
            import requests
            import time

            start_time = time.time()

            # 測試 API（這裡用 httpbin.org）
            response = requests.get("https://httpbin.org/status/200", timeout=5)

            response_time = time.time() - start_time

            if response.status_code == 200:
                return ComponentStatus(
                    name="api_endpoint",
                    status=HealthStatus.HEALTHY,
                    message="API 端點正常",
                    response_time=response_time,
                )
            else:
                return ComponentStatus(
                    name="api_endpoint",
                    status=HealthStatus.DEGRADED,
                    message=f"API 回應異常: {response.status_code}",
                    response_time=response_time,
                )

        except Exception as e:
            return ComponentStatus(
                name="api_endpoint",
                status=HealthStatus.UNHEALTHY,
                message=f"API 檢查失敗: {str(e)}",
            )

    # 註冊自訂檢查
    print(f"\n註冊自訂檢查...")
    health_checker.register_check("api_endpoint", check_api_endpoint)

    print(f"\n可用的檢查:")
    for check_name in health_checker.checks.keys():
        print(f"  - {check_name}")

    # 執行自訂檢查
    print(f"\n執行自訂檢查...")
    api_status = health_checker.check_component("api_endpoint")

    print(f"  狀態: {api_status.status.value}")
    print(f"  訊息: {api_status.message}")
    if api_status.response_time:
        print(f"  回應時間: {api_status.response_time:.4f}s")


# ============================================================================
# 範例 5: 異步健康檢查
# ============================================================================


async def example_5_async_check():
    """異步健康檢查"""
    print("\n" + "=" * 80)
    print("範例 5: 異步健康檢查")
    print("=" * 80)

    health_checker = HealthChecker()

    # 異步檢查所有組件
    print(f"\n異步檢查所有組件...")
    import time

    start_time = time.time()
    results = await health_checker.check_all_async()
    elapsed_time = time.time() - start_time

    print(f"\n完成時間: {elapsed_time:.4f}s")

    print(f"\n檢查結果:")
    for name, status in results.items():
        print(f"  {name}: {status.status.value}")

    # 生成異步健康報告
    print(f"\n生成異步健康報告...")
    start_time = time.time()
    report = await health_checker.get_health_report_async()
    elapsed_time = time.time() - start_time

    print(f"\n完成時間: {elapsed_time:.4f}s")
    print(f"整體狀態: {report['status']}")


# ============================================================================
# 範例 6: 帶外部組件的健康檢查
# ============================================================================


def example_6_with_components():
    """帶外部組件的健康檢查"""
    print("\n" + "=" * 80)
    print("範例 6: 帶外部組件的健康檢查")
    print("=" * 80)

    # 模擬外部組件
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
                    return "sqlite:///./test.db"

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
                "used_memory_human": "1.5M",
                "connected_clients": 5,
                "uptime_in_days": 10,
            }

    class MockModel:
        model_name = "TAIDE-LX-8B"
        device = "cpu"

        def generate(self, prompt, max_length=10):
            return "測試回覆"

    # 創建健康檢查器
    health_checker = HealthChecker(
        database_manager=MockDatabase(),
        redis_cache=MockRedis(),
        model_generator=MockModel(),
    )

    print(f"\n檢查所有組件...")
    results = health_checker.check_all()

    print(f"\n檢查結果:")
    for name, status in results.items():
        print(f"\n  {name}:")
        print(f"    狀態: {status.status.value}")
        print(f"    訊息: {status.message}")
        if status.response_time:
            print(f"    回應時間: {status.response_time:.4f}s")
        if status.details:
            print(f"    詳細資訊:")
            for key, value in status.details.items():
                print(f"      {key}: {value}")


# ============================================================================
# 主程序
# ============================================================================

if __name__ == "__main__":
    import asyncio

    print("\n" + "=" * 80)
    print("健康檢查範例")
    print("=" * 80)

    # 運行範例
    example_1_basic_check()
    example_2_check_all()
    example_3_health_report()
    example_4_custom_check()

    # 運行異步範例
    asyncio.run(example_5_async_check())

    example_6_with_components()

    print("\n" + "=" * 80)
    print("範例完成！")
    print("=" * 80)
    print("""
主要功能:

1. 組件健康檢查
   - 資料庫連接
   - Redis 連接
   - 模型狀態
   - 磁碟空間
   - 記憶體使用

2. 健康狀態
   - HEALTHY: 組件正常
   - DEGRADED: 組件降級
   - UNHEALTHY: 組件不健康

3. 檢查模式
   - 同步檢查
   - 異步並行檢查
   - 單個組件檢查
   - 全部組件檢查

4. 健康報告
   - 詳細狀態
   - 回應時間
   - 摘要統計
   - 時間戳記

5. 自訂檢查
   - register_check() 註冊
   - unregister_check() 取消註冊
   - 自訂檢查邏輯

使用建議:
    - 定期執行健康檢查
    - 監控關鍵組件
    - 設置告警閾值
    - 整合監控系統
    """)
