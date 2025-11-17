#!/usr/bin/env python3
"""
案例 2.3: 性能優化示例

這個範例展示各種性能優化技術，包括：
- 批量推理優化
- 記憶體管理
- 快取機制
- 推理參數調優

運行方式:
    python examples/02_advanced_applications/performance_optimization.py
"""

import time
import psutil
import torch
from typing import List, Dict, Any, Optional
from functools import lru_cache
from medical_chatbot.models.model_manager import ModelManager
from medical_chatbot.inference.generator import TextGenerator


class PerformanceMonitor:
    """性能監控器"""

    def __init__(self):
        """初始化性能監控器"""
        self.metrics = []

    def start_measurement(self) -> Dict[str, Any]:
        """開始測量

        Returns:
            初始測量數據
        """
        return {
            "start_time": time.time(),
            "start_memory": psutil.Process().memory_info().rss / 1024 / 1024,  # MB
            "start_gpu_memory": (
                torch.cuda.memory_allocated() / 1024 / 1024
                if torch.cuda.is_available() else 0
            )
        }

    def end_measurement(self, start_data: Dict[str, Any], label: str = ""):
        """結束測量並記錄

        Args:
            start_data: 初始測量數據
            label: 測量標籤
        """
        end_time = time.time()
        end_memory = psutil.Process().memory_info().rss / 1024 / 1024
        end_gpu_memory = (
            torch.cuda.memory_allocated() / 1024 / 1024
            if torch.cuda.is_available() else 0
        )

        metric = {
            "label": label,
            "duration": end_time - start_data["start_time"],
            "memory_used": end_memory - start_data["start_memory"],
            "gpu_memory_used": end_gpu_memory - start_data["start_gpu_memory"]
        }

        self.metrics.append(metric)
        return metric

    def print_metric(self, metric: Dict[str, Any]):
        """打印測量結果

        Args:
            metric: 測量數據
        """
        print(f"\n{'─' * 60}")
        print(f"測試: {metric['label']}")
        print(f"{'─' * 60}")
        print(f"執行時間: {metric['duration']:.3f} 秒")
        print(f"記憶體使用: {metric['memory_used']:.2f} MB")
        if metric['gpu_memory_used'] > 0:
            print(f"GPU 記憶體使用: {metric['gpu_memory_used']:.2f} MB")

    def print_summary(self):
        """打印所有測量結果摘要"""
        if not self.metrics:
            print("沒有測量數據")
            return

        print("\n" + "=" * 60)
        print("性能測試摘要")
        print("=" * 60)

        for metric in self.metrics:
            print(f"\n{metric['label']}:")
            print(f"  時間: {metric['duration']:.3f}s")
            print(f"  記憶體: {metric['memory_used']:.2f}MB")
            if metric['gpu_memory_used'] > 0:
                print(f"  GPU記憶體: {metric['gpu_memory_used']:.2f}MB")


class OptimizedGenerator:
    """優化的生成器"""

    def __init__(self, model_manager: ModelManager):
        """初始化優化生成器

        Args:
            model_manager: 模型管理器
        """
        self.model_manager = model_manager
        self.generator = TextGenerator(
            model=model_manager.model,
            tokenizer=model_manager.tokenizer
        )

        # 快取
        self.response_cache = {}
        self.cache_hits = 0
        self.cache_misses = 0

    def generate_with_cache(
        self,
        question: str,
        use_cache: bool = True
    ) -> str:
        """使用快取的生成

        Args:
            question: 問題
            use_cache: 是否使用快取

        Returns:
            回應
        """
        # 檢查快取
        if use_cache and question in self.response_cache:
            self.cache_hits += 1
            return self.response_cache[question]

        self.cache_misses += 1

        # 生成回應
        messages = [
            {
                "role": "system",
                "content": "你是一位專業的醫療人員，請提供準確且有幫助的醫療建議。"
            },
            {
                "role": "user",
                "content": question
            }
        ]

        response = self.generator.generate(messages)

        # 存入快取
        if use_cache:
            self.response_cache[question] = response

        return response

    def batch_generate(
        self,
        questions: List[str],
        batch_size: int = 4
    ) -> List[str]:
        """批量生成（模擬批量處理）

        Args:
            questions: 問題列表
            batch_size: 批次大小

        Returns:
            回應列表
        """
        responses = []

        # 分批處理
        for i in range(0, len(questions), batch_size):
            batch = questions[i:i + batch_size]

            # 處理批次中的每個問題
            for question in batch:
                response = self.generate_with_cache(question)
                responses.append(response)

        return responses

    def get_cache_stats(self) -> Dict[str, Any]:
        """獲取快取統計

        Returns:
            快取統計字典
        """
        total = self.cache_hits + self.cache_misses
        hit_rate = self.cache_hits / total * 100 if total > 0 else 0

        return {
            "cache_size": len(self.response_cache),
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "hit_rate": f"{hit_rate:.2f}%"
        }

    def clear_cache(self):
        """清空快取"""
        self.response_cache.clear()
        self.cache_hits = 0
        self.cache_misses = 0


def demo_baseline_performance():
    """示範基準性能測試"""
    print("\n" + "=" * 60)
    print("示範 1: 基準性能測試")
    print("=" * 60)

    monitor = PerformanceMonitor()

    # 初始化模型
    print("\n正在載入模型...")
    model_manager = ModelManager()
    model_manager.load_model()

    generator = TextGenerator(
        model=model_manager.model,
        tokenizer=model_manager.tokenizer
    )

    # 測試問題
    questions = [
        "如何預防感冒？",
        "頭痛該怎麼辦？",
        "失眠如何改善？"
    ]

    # 逐個測試
    for i, question in enumerate(questions, 1):
        print(f"\n測試 {i}/{len(questions)}: {question}")

        start = monitor.start_measurement()

        messages = [
            {
                "role": "system",
                "content": "你是一位專業的醫療人員，請提供準確且有幫助的醫療建議。"
            },
            {
                "role": "user",
                "content": question
            }
        ]

        response = generator.generate(messages)

        metric = monitor.end_measurement(start, f"問題 {i}")
        monitor.print_metric(metric)

        print(f"\n回應: {response[:100]}...")

    # 打印摘要
    monitor.print_summary()


def demo_cache_optimization():
    """示範快取優化"""
    print("\n" + "=" * 60)
    print("示範 2: 快取優化")
    print("=" * 60)

    monitor = PerformanceMonitor()

    # 初始化
    model_manager = ModelManager()
    model_manager.load_model()
    opt_generator = OptimizedGenerator(model_manager)

    # 測試問題（包含重複）
    questions = [
        "如何預防感冒？",
        "頭痛該怎麼辦？",
        "如何預防感冒？",  # 重複
        "失眠如何改善？",
        "頭痛該怎麼辦？",  # 重複
        "如何預防感冒？"   # 重複
    ]

    print(f"\n測試 {len(questions)} 個問題（包含重複）\n")

    # 不使用快取
    print("【不使用快取】")
    start = monitor.start_measurement()

    for question in questions:
        opt_generator.generate_with_cache(question, use_cache=False)

    metric_no_cache = monitor.end_measurement(start, "不使用快取")
    monitor.print_metric(metric_no_cache)

    # 清空快取
    opt_generator.clear_cache()

    # 使用快取
    print("\n【使用快取】")
    start = monitor.start_measurement()

    for question in questions:
        opt_generator.generate_with_cache(question, use_cache=True)

    metric_with_cache = monitor.end_measurement(start, "使用快取")
    monitor.print_metric(metric_with_cache)

    # 快取統計
    stats = opt_generator.get_cache_stats()
    print("\n快取統計:")
    for key, value in stats.items():
        print(f"  {key}: {value}")

    # 性能改善
    improvement = (
        (metric_no_cache['duration'] - metric_with_cache['duration'])
        / metric_no_cache['duration'] * 100
    )
    print(f"\n性能改善: {improvement:.2f}%")


def demo_batch_processing():
    """示範批量處理優化"""
    print("\n" + "=" * 60)
    print("示範 3: 批量處理優化")
    print("=" * 60)

    monitor = PerformanceMonitor()

    # 初始化
    model_manager = ModelManager()
    model_manager.load_model()
    opt_generator = OptimizedGenerator(model_manager)

    # 測試問題
    questions = [
        "如何保持身體健康？",
        "運動對健康有什麼好處？",
        "健康飲食的原則是什麼？",
        "如何提高免疫力？",
        "壓力管理的方法有哪些？",
        "充足睡眠的重要性是什麼？"
    ]

    print(f"\n處理 {len(questions)} 個問題\n")

    # 逐個處理
    print("【逐個處理】")
    start = monitor.start_measurement()

    for question in questions:
        opt_generator.generate_with_cache(question, use_cache=False)

    metric_sequential = monitor.end_measurement(start, "逐個處理")
    monitor.print_metric(metric_sequential)

    # 批量處理
    opt_generator.clear_cache()

    print("\n【批量處理 (batch_size=3)】")
    start = monitor.start_measurement()

    opt_generator.batch_generate(questions, batch_size=3)

    metric_batch = monitor.end_measurement(start, "批量處理")
    monitor.print_metric(metric_batch)


def demo_parameter_tuning():
    """示範參數調優"""
    print("\n" + "=" * 60)
    print("示範 4: 推理參數調優")
    print("=" * 60)

    monitor = PerformanceMonitor()

    # 初始化
    model_manager = ModelManager()
    model_manager.load_model()

    question = "如何保持健康的生活方式？"

    # 測試不同參數配置
    configs = [
        {
            "name": "高質量 (慢)",
            "params": {
                "max_new_tokens": 150,
                "temperature": 0.3,
                "do_sample": True
            }
        },
        {
            "name": "平衡",
            "params": {
                "max_new_tokens": 90,
                "temperature": 0.15,
                "do_sample": True
            }
        },
        {
            "name": "快速",
            "params": {
                "max_new_tokens": 50,
                "temperature": 0.1,
                "do_sample": False
            }
        }
    ]

    print(f"\n測試問題: {question}\n")

    for config in configs:
        print(f"\n{'─' * 60}")
        print(f"配置: {config['name']}")
        print(f"{'─' * 60}")

        generator = TextGenerator(
            model=model_manager.model,
            tokenizer=model_manager.tokenizer,
            **config['params']
        )

        start = monitor.start_measurement()

        messages = [
            {
                "role": "system",
                "content": "你是一位專業的醫療人員，請提供準確且有幫助的醫療建議。"
            },
            {
                "role": "user",
                "content": question
            }
        ]

        response = generator.generate(messages)

        metric = monitor.end_measurement(start, config['name'])

        print(f"執行時間: {metric['duration']:.3f}秒")
        print(f"回應長度: {len(response)} 字元")
        print(f"回應: {response[:80]}...")

    # 打印摘要
    monitor.print_summary()


def demo_memory_management():
    """示範記憶體管理"""
    print("\n" + "=" * 60)
    print("示範 5: 記憶體管理")
    print("=" * 60)

    # 顯示系統資訊
    print("\n系統資訊:")
    print(f"CPU 數量: {psutil.cpu_count()}")
    print(f"總記憶體: {psutil.virtual_memory().total / 1024 / 1024 / 1024:.2f} GB")
    print(f"可用記憶體: {psutil.virtual_memory().available / 1024 / 1024 / 1024:.2f} GB")

    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}")
        print(f"GPU 總記憶體: {torch.cuda.get_device_properties(0).total_memory / 1024 / 1024 / 1024:.2f} GB")

    # 載入模型前的記憶體
    print("\n載入模型前:")
    print(f"進程記憶體: {psutil.Process().memory_info().rss / 1024 / 1024:.2f} MB")

    if torch.cuda.is_available():
        print(f"GPU 已分配: {torch.cuda.memory_allocated() / 1024 / 1024:.2f} MB")
        print(f"GPU 已保留: {torch.cuda.memory_reserved() / 1024 / 1024:.2f} MB")

    # 載入模型
    print("\n正在載入模型...")
    model_manager = ModelManager()
    model_manager.load_model()

    # 載入模型後的記憶體
    print("\n載入模型後:")
    print(f"進程記憶體: {psutil.Process().memory_info().rss / 1024 / 1024:.2f} MB")

    if torch.cuda.is_available():
        print(f"GPU 已分配: {torch.cuda.memory_allocated() / 1024 / 1024:.2f} MB")
        print(f"GPU 已保留: {torch.cuda.memory_reserved() / 1024 / 1024:.2f} MB")

    # 執行推理
    generator = TextGenerator(
        model=model_manager.model,
        tokenizer=model_manager.tokenizer
    )

    messages = [
        {
            "role": "system",
            "content": "你是一位專業的醫療人員。"
        },
        {
            "role": "user",
            "content": "如何保持健康？"
        }
    ]

    print("\n執行推理...")
    generator.generate(messages)

    # 推理後的記憶體
    print("\n推理後:")
    print(f"進程記憶體: {psutil.Process().memory_info().rss / 1024 / 1024:.2f} MB")

    if torch.cuda.is_available():
        print(f"GPU 已分配: {torch.cuda.memory_allocated() / 1024 / 1024:.2f} MB")
        print(f"GPU 已保留: {torch.cuda.memory_reserved() / 1024 / 1024:.2f} MB")

        # 清理 GPU 快取
        print("\n清理 GPU 快取...")
        torch.cuda.empty_cache()

        print("清理後:")
        print(f"GPU 已分配: {torch.cuda.memory_allocated() / 1024 / 1024:.2f} MB")
        print(f"GPU 已保留: {torch.cuda.memory_reserved() / 1024 / 1024:.2f} MB")


def main():
    """主函數"""
    print("""
╔══════════════════════════════════════════════════════════╗
║        醫療聊天機器人 - 性能優化示例                    ║
╚══════════════════════════════════════════════════════════╝
    """)

    print("\n選擇要運行的示範:")
    print("1. 基準性能測試")
    print("2. 快取優化")
    print("3. 批量處理優化")
    print("4. 推理參數調優")
    print("5. 記憶體管理")
    print("6. 運行所有示範")

    try:
        choice = input("\n請輸入選項 (1-6): ").strip()

        if choice == "1":
            demo_baseline_performance()
        elif choice == "2":
            demo_cache_optimization()
        elif choice == "3":
            demo_batch_processing()
        elif choice == "4":
            demo_parameter_tuning()
        elif choice == "5":
            demo_memory_management()
        elif choice == "6":
            demo_baseline_performance()
            demo_cache_optimization()
            demo_batch_processing()
            demo_parameter_tuning()
            demo_memory_management()
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
