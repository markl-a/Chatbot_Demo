#!/usr/bin/env python3
"""
案例 4.2: 監控與日誌記錄示例

這個範例展示如何實施完善的監控和日誌系統，包括：
- 結構化日誌記錄
- 性能指標收集
- 請求追蹤
- 錯誤監控

運行方式:
    python examples/04_integration_deployment/monitoring_logging.py
"""

import logging
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
from functools import wraps
from medical_chatbot.models.model_manager import ModelManager
from medical_chatbot.inference.generator import TextGenerator


class StructuredLogger:
    """結構化日誌記錄器"""

    def __init__(self, name: str, log_dir: str = "logs"):
        """初始化結構化日誌記錄器

        Args:
            name: 日誌記錄器名稱
            log_dir: 日誌目錄
        """
        self.name = name
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)

        # 創建日誌記錄器
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)

        # 創建檔案處理器
        log_file = self.log_dir / f"{name}_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)

        # 創建控制台處理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # 創建格式化器
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        # 添加處理器
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    def log_structured(
        self,
        level: str,
        message: str,
        extra_data: Optional[Dict[str, Any]] = None
    ):
        """記錄結構化日誌

        Args:
            level: 日誌級別
            message: 日誌訊息
            extra_data: 額外數據
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "message": message,
            "logger": self.name
        }

        if extra_data:
            log_entry["extra"] = extra_data

        log_message = json.dumps(log_entry, ensure_ascii=False)

        if level == "DEBUG":
            self.logger.debug(log_message)
        elif level == "INFO":
            self.logger.info(log_message)
        elif level == "WARNING":
            self.logger.warning(log_message)
        elif level == "ERROR":
            self.logger.error(log_message)
        elif level == "CRITICAL":
            self.logger.critical(log_message)

    def log_request(
        self,
        request_id: str,
        endpoint: str,
        method: str,
        params: Dict[str, Any]
    ):
        """記錄請求日誌

        Args:
            request_id: 請求 ID
            endpoint: 端點
            method: 方法
            params: 參數
        """
        self.log_structured(
            "INFO",
            "Incoming request",
            {
                "request_id": request_id,
                "endpoint": endpoint,
                "method": method,
                "params": params
            }
        )

    def log_response(
        self,
        request_id: str,
        status: str,
        duration: float,
        response_size: int
    ):
        """記錄回應日誌

        Args:
            request_id: 請求 ID
            status: 狀態
            duration: 執行時間
            response_size: 回應大小
        """
        self.log_structured(
            "INFO",
            "Response sent",
            {
                "request_id": request_id,
                "status": status,
                "duration_seconds": duration,
                "response_size_bytes": response_size
            }
        )

    def log_error(
        self,
        request_id: str,
        error_type: str,
        error_message: str,
        stack_trace: Optional[str] = None
    ):
        """記錄錯誤日誌

        Args:
            request_id: 請求 ID
            error_type: 錯誤類型
            error_message: 錯誤訊息
            stack_trace: 堆疊追蹤
        """
        extra_data = {
            "request_id": request_id,
            "error_type": error_type,
            "error_message": error_message
        }

        if stack_trace:
            extra_data["stack_trace"] = stack_trace

        self.log_structured("ERROR", "Error occurred", extra_data)


class PerformanceMonitor:
    """性能監控器"""

    def __init__(self):
        """初始化性能監控器"""
        self.metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_duration": 0.0,
            "request_durations": []
        }

    def record_request(self, duration: float, success: bool = True):
        """記錄請求指標

        Args:
            duration: 執行時間
            success: 是否成功
        """
        self.metrics["total_requests"] += 1

        if success:
            self.metrics["successful_requests"] += 1
        else:
            self.metrics["failed_requests"] += 1

        self.metrics["total_duration"] += duration
        self.metrics["request_durations"].append(duration)

    def get_statistics(self) -> Dict[str, Any]:
        """獲取統計數據

        Returns:
            統計數據字典
        """
        total = self.metrics["total_requests"]

        if total == 0:
            return {"error": "沒有請求數據"}

        durations = self.metrics["request_durations"]

        return {
            "total_requests": total,
            "successful_requests": self.metrics["successful_requests"],
            "failed_requests": self.metrics["failed_requests"],
            "success_rate": f"{self.metrics['successful_requests'] / total * 100:.2f}%",
            "average_duration": f"{self.metrics['total_duration'] / total:.3f}s",
            "min_duration": f"{min(durations):.3f}s",
            "max_duration": f"{max(durations):.3f}s",
            "total_duration": f"{self.metrics['total_duration']:.3f}s"
        }

    def reset(self):
        """重置指標"""
        self.metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_duration": 0.0,
            "request_durations": []
        }


def monitored_function(logger: StructuredLogger, monitor: PerformanceMonitor):
    """監控裝飾器

    Args:
        logger: 日誌記錄器
        monitor: 性能監控器
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            request_id = f"req_{int(time.time() * 1000)}"

            # 記錄請求開始
            logger.log_request(
                request_id,
                func.__name__,
                "CALL",
                {"args": str(args)[:100], "kwargs": str(kwargs)[:100]}
            )

            start_time = time.time()

            try:
                # 執行函數
                result = func(*args, **kwargs)

                # 計算執行時間
                duration = time.time() - start_time

                # 記錄成功
                logger.log_response(
                    request_id,
                    "SUCCESS",
                    duration,
                    len(str(result))
                )

                monitor.record_request(duration, success=True)

                return result

            except Exception as e:
                # 計算執行時間
                duration = time.time() - start_time

                # 記錄錯誤
                logger.log_error(
                    request_id,
                    type(e).__name__,
                    str(e)
                )

                monitor.record_request(duration, success=False)

                raise

        return wrapper
    return decorator


def demo_basic_logging():
    """示範基本日誌記錄"""
    print("\n" + "=" * 60)
    print("示範 1: 基本日誌記錄")
    print("=" * 60)

    # 創建日誌記錄器
    logger = StructuredLogger("medical_chatbot")

    # 記錄不同級別的日誌
    logger.log_structured("INFO", "應用程式啟動")
    logger.log_structured("DEBUG", "載入配置", {"config_file": "config.yaml"})
    logger.log_structured("WARNING", "模型載入較慢", {"duration": 30.5})
    logger.log_structured("ERROR", "模型載入失敗", {
        "error": "CUDA out of memory"
    })

    print("\n✓ 日誌已記錄到 logs/ 目錄")


def demo_request_logging():
    """示範請求日誌"""
    print("\n" + "=" * 60)
    print("示範 2: 請求日誌記錄")
    print("=" * 60)

    logger = StructuredLogger("api")

    # 模擬 API 請求
    requests = [
        {
            "request_id": "req_001",
            "endpoint": "/chat",
            "method": "POST",
            "params": {"message": "如何預防感冒？"}
        },
        {
            "request_id": "req_002",
            "endpoint": "/conversation",
            "method": "POST",
            "params": {"messages": [{"role": "user", "content": "頭痛"}]}
        }
    ]

    for req in requests:
        # 記錄請求
        logger.log_request(
            req["request_id"],
            req["endpoint"],
            req["method"],
            req["params"]
        )

        # 模擬處理
        time.sleep(0.1)

        # 記錄回應
        logger.log_response(
            req["request_id"],
            "200 OK",
            0.15,
            512
        )

    print("\n✓ 請求日誌已記錄")


def demo_performance_monitoring():
    """示範性能監控"""
    print("\n" + "=" * 60)
    print("示範 3: 性能監控")
    print("=" * 60)

    logger = StructuredLogger("performance")
    monitor = PerformanceMonitor()

    # 創建被監控的函數
    @monitored_function(logger, monitor)
    def process_question(question: str) -> str:
        """處理問題"""
        time.sleep(0.2)  # 模擬處理時間
        return f"回答: {question}"

    # 執行多次請求
    questions = [
        "如何保持健康？",
        "預防疾病的方法？",
        "運動的好處？"
    ]

    print("\n處理請求...")
    for question in questions:
        try:
            result = process_question(question)
            print(f"✓ 處理完成: {question[:20]}...")
        except Exception as e:
            print(f"✗ 處理失敗: {str(e)}")

    # 顯示統計數據
    stats = monitor.get_statistics()
    print("\n性能統計:")
    for key, value in stats.items():
        print(f"  {key}: {value}")


def demo_error_logging():
    """示範錯誤日誌"""
    print("\n" + "=" * 60)
    print("示範 4: 錯誤日誌記錄")
    print("=" * 60)

    logger = StructuredLogger("errors")

    # 模擬各種錯誤
    errors = [
        {
            "request_id": "req_100",
            "error_type": "ValueError",
            "message": "無效的參數"
        },
        {
            "request_id": "req_101",
            "error_type": "RuntimeError",
            "message": "模型推理失敗"
        },
        {
            "request_id": "req_102",
            "error_type": "TimeoutError",
            "message": "請求超時"
        }
    ]

    for error in errors:
        logger.log_error(
            error["request_id"],
            error["error_type"],
            error["message"]
        )

        print(f"✓ 記錄錯誤: {error['error_type']}")

    print("\n✓ 錯誤日誌已記錄")


def demo_comprehensive_monitoring():
    """示範綜合監控"""
    print("\n" + "=" * 60)
    print("示範 5: 綜合監控系統")
    print("=" * 60)

    # 初始化監控組件
    logger = StructuredLogger("comprehensive")
    monitor = PerformanceMonitor()

    print("\n正在載入模型...")
    logger.log_structured("INFO", "開始載入模型")

    try:
        model_manager = ModelManager()
        model_manager.load_model()

        logger.log_structured("INFO", "模型載入成功")
        print("✓ 模型載入完成")

    except Exception as e:
        logger.log_error(
            "model_load",
            type(e).__name__,
            str(e)
        )
        print(f"✗ 模型載入失敗: {str(e)}")
        return

    # 創建監控的生成器
    generator = TextGenerator(
        model=model_manager.model,
        tokenizer=model_manager.tokenizer
    )

    @monitored_function(logger, monitor)
    def chat(question: str) -> str:
        messages = [
            {
                "role": "system",
                "content": "你是一位專業的醫療人員。"
            },
            {
                "role": "user",
                "content": question
            }
        ]
        return generator.generate(messages)

    # 執行測試
    test_questions = [
        "如何預防感冒？",
        "頭痛該怎麼辦？"
    ]

    print("\n執行測試...")
    for question in test_questions:
        try:
            response = chat(question)
            print(f"✓ Q: {question}")
            print(f"  A: {response[:80]}...")
        except Exception as e:
            print(f"✗ 錯誤: {str(e)}")

    # 顯示統計
    stats = monitor.get_statistics()
    print("\n" + "=" * 60)
    print("綜合統計:")
    print("=" * 60)
    for key, value in stats.items():
        print(f"{key}: {value}")


def main():
    """主函數"""
    print("""
╔══════════════════════════════════════════════════════════╗
║        醫療聊天機器人 - 監控與日誌示例                  ║
╚══════════════════════════════════════════════════════════╝
    """)

    print("\n選擇要運行的示範:")
    print("1. 基本日誌記錄")
    print("2. 請求日誌記錄")
    print("3. 性能監控")
    print("4. 錯誤日誌記錄")
    print("5. 綜合監控系統")
    print("6. 運行所有示範")

    try:
        choice = input("\n請輸入選項 (1-6): ").strip()

        if choice == "1":
            demo_basic_logging()
        elif choice == "2":
            demo_request_logging()
        elif choice == "3":
            demo_performance_monitoring()
        elif choice == "4":
            demo_error_logging()
        elif choice == "5":
            demo_comprehensive_monitoring()
        elif choice == "6":
            demo_basic_logging()
            demo_request_logging()
            demo_performance_monitoring()
            demo_error_logging()
            # 跳過綜合監控（需要載入模型）
        else:
            print("無效的選項")

        print("\n" + "=" * 60)
        print("示範完成！")
        print("=" * 60)

    except Exception as e:
        print(f"\n發生錯誤: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
