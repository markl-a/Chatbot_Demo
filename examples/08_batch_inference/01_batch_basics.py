"""
批次推理基礎範例

展示如何使用批次推理工具進行大規模推理。
"""
import sys
from pathlib import Path
import time

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.medical_chatbot.batch_inference import BatchProcessor, ParallelProcessor


# ============================================================================
# 模擬生成器
# ============================================================================


class MockGenerator:
    """模擬生成器（用於演示）"""

    def generate(self, prompt: str, **kwargs):
        # 模擬生成延遲
        time.sleep(0.1)

        # 簡單的回覆生成
        responses = {
            "什麼是高血壓？": "高血壓是一種血壓持續高於正常值的慢性疾病，需要長期控制和管理。",
            "糖尿病如何預防？": "預防糖尿病需要控制體重、健康飲食、定期運動和定期健康檢查。",
            "運動的好處？": "運動可以增強心肺功能、控制體重、改善心情和降低慢性病風險。",
        }

        # 檢查關鍵字
        for key in responses:
            if key in prompt:
                return responses[key]

        return f"關於「{prompt[:20]}...」的醫療建議。"


# ============================================================================
# 範例 1: 基本批次推理
# ============================================================================


def example_1_basic_batch():
    """基本批次推理"""
    print("\n" + "=" * 80)
    print("範例 1: 基本批次推理")
    print("=" * 80)

    # 創建生成器
    generator = MockGenerator()

    # 創建批次處理器
    processor = BatchProcessor(
        generator=generator,
        batch_size=4,
        save_dir="./batch_results",
        save_interval=10,
    )

    print(f"\n批次處理器: {processor}")

    # 準備輸入
    inputs = [
        "什麼是高血壓？",
        "糖尿病如何預防？",
        "運動的好處？",
        "如何控制血糖？",
        "心臟病的症狀？",
        "如何預防感冒？",
        "什麼是膽固醇？",
        "如何降低血壓？",
        "糖尿病的併發症？",
        "如何改善睡眠？",
    ]

    print(f"\n輸入樣本數: {len(inputs)}")
    print(f"批次大小: {processor.batch_size}")

    # 執行批次推理
    print(f"\n{'=' * 80}")
    print("開始批次推理...")
    print(f"{'=' * 80}")

    results = processor.process(
        inputs=inputs,
        show_progress=True,
        auto_save=False,
        max_length=256,
    )

    # 顯示結果
    print(f"\n{'=' * 80}")
    print("推理結果:")
    print(f"{'=' * 80}")

    for i, result in enumerate(results[:3], 1):
        print(f"\n樣本 {i}:")
        print(f"  輸入: {result['input']}")
        if result["status"] == "success":
            print(f"  輸出: {result['output']}")
            print(f"  生成時間: {result['generation_time']:.3f}s")
        else:
            print(f"  錯誤: {result['error']}")

    print(f"\n... (顯示前 3 個結果)")

    # 統計資訊
    stats = processor.get_stats()
    print(f"\n{'=' * 80}")
    print("統計資訊:")
    print(f"{'=' * 80}")
    print(f"  總樣本數: {stats['total_inputs']}")
    print(f"  成功處理: {stats['total_processed']}")
    print(f"  錯誤數: {stats['total_errors']}")
    print(f"  錯誤率: {stats['error_rate']:.2%}")
    print(f"  總耗時: {stats['total_time']:.2f}s")
    print(f"  平均每樣本: {stats['avg_time_per_sample']:.3f}s")
    print(f"  吞吐量: {stats['throughput']:.2f} 樣本/秒")

    # 保存結果
    filepath = processor.save_results("batch_example_1.json")
    print(f"\n結果已保存: {filepath}")


# ============================================================================
# 範例 2: 使用提示模板
# ============================================================================


def example_2_with_templates():
    """使用提示模板"""
    print("\n" + "=" * 80)
    print("範例 2: 使用提示模板")
    print("=" * 80)

    generator = MockGenerator()
    processor = BatchProcessor(generator=generator, batch_size=4)

    # 輸入問題
    questions = [
        "高血壓",
        "糖尿病",
        "心臟病",
        "感冒",
    ]

    # 提示模板
    prompts = [
        "請詳細說明什麼是{input}？",
        "請解釋如何預防{input}？",
        "請說明{input}的症狀有哪些？",
        "請說明如何治療{input}？",
    ]

    print(f"\n問題數: {len(questions)}")
    print(f"提示模板範例: {prompts[0]}")

    # 執行推理
    results = processor.process(
        inputs=questions,
        prompts=prompts,
        show_progress=True,
    )

    # 顯示結果
    print(f"\n推理結果:")
    for result in results[:2]:
        print(f"\n  問題: {result['input']}")
        print(f"  提示: {result['prompt']}")
        print(f"  回覆: {result['output'][:100]}...")


# ============================================================================
# 範例 3: 並行推理
# ============================================================================


def example_3_parallel():
    """並行推理"""
    print("\n" + "=" * 80)
    print("範例 3: 並行推理")
    print("=" * 80)

    generator = MockGenerator()

    # 創建並行處理器（多線程）
    processor = ParallelProcessor(
        generator=generator,
        max_workers=4,
        mode="thread",
    )

    print(f"\n並行處理器: {processor}")

    # 準備輸入
    inputs = [f"問題 {i}" for i in range(20)]

    print(f"\n輸入樣本數: {len(inputs)}")
    print(f"工作線程數: {processor.max_workers}")

    # 執行並行推理
    print(f"\n{'=' * 80}")
    print("開始並行推理...")
    print(f"{'=' * 80}")

    results = processor.process(inputs=inputs, show_progress=True)

    # 統計資訊
    stats = processor.get_stats()
    print(f"\n統計資訊:")
    print(f"  處理模式: {stats['mode']}")
    print(f"  工作數: {stats['max_workers']}")
    print(f"  總樣本數: {stats['total_inputs']}")
    print(f"  成功處理: {stats['total_processed']}")
    print(f"  總耗時: {stats['total_time']:.2f}s")
    print(f"  吞吐量: {stats['throughput']:.2f} 樣本/秒")

    # 性能分析
    analysis = processor.analyze_performance()
    print(f"\n性能分析:")
    print(f"  平均生成時間: {analysis['mean_time']:.3f}s")
    print(f"  中位數: {analysis['median_time']:.3f}s")
    print(f"  標準差: {analysis['std_time']:.3f}s")
    print(f"  最小值: {analysis['min_time']:.3f}s")
    print(f"  最大值: {analysis['max_time']:.3f}s")
    print(f"  95% 分位: {analysis['percentile_95']:.3f}s")
    if analysis["speedup"]:
        print(f"  加速比: {analysis['speedup']:.2f}x")


# ============================================================================
# 範例 4: 錯誤處理和重試
# ============================================================================


def example_4_error_handling():
    """錯誤處理和重試"""
    print("\n" + "=" * 80)
    print("範例 4: 錯誤處理和重試")
    print("=" * 80)

    # 創建會出錯的生成器
    class FaultyGenerator:
        def __init__(self, error_rate=0.3):
            self.error_rate = error_rate
            self.call_count = 0

        def generate(self, prompt: str, **kwargs):
            self.call_count += 1

            # 模擬錯誤
            import random

            if random.random() < self.error_rate:
                raise Exception("模擬的生成錯誤")

            time.sleep(0.05)
            return f"回覆: {prompt}"

    generator = FaultyGenerator(error_rate=0.3)
    processor = BatchProcessor(generator=generator, batch_size=4)

    # 準備輸入
    inputs = [f"測試問題 {i}" for i in range(20)]

    print(f"\n輸入樣本數: {len(inputs)}")
    print(f"預期錯誤率: 30%")

    # 執行推理
    print(f"\n第一次推理:")
    results = processor.process(inputs=inputs, show_progress=True, auto_save=False)

    stats = processor.get_stats()
    print(f"\n統計資訊:")
    print(f"  成功: {stats['total_processed']}")
    print(f"  錯誤: {stats['total_errors']}")
    print(f"  錯誤率: {stats['error_rate']:.2%}")

    # 重試失敗的樣本
    if stats["total_errors"] > 0:
        print(f"\n{'=' * 80}")
        print(f"重試失敗的樣本...")
        print(f"{'=' * 80}")

        retry_results = processor.retry_failed(max_retries=3, show_progress=True)

        print(f"\n重試結果:")
        print(f"  重試成功: {len(retry_results)}")
        print(f"  仍然失敗: {processor.get_stats()['total_errors']}")


# ============================================================================
# 範例 5: 結果導出
# ============================================================================


def example_5_export():
    """結果導出"""
    print("\n" + "=" * 80)
    print("範例 5: 結果導出")
    print("=" * 80)

    generator = MockGenerator()
    processor = BatchProcessor(generator=generator, batch_size=4)

    # 執行推理
    inputs = ["問題 1", "問題 2", "問題 3", "問題 4", "問題 5"]
    results = processor.process(inputs=inputs, show_progress=False)

    print(f"\n處理了 {len(results)} 個樣本")

    # 導出為不同格式
    print(f"\n導出結果:")

    # TXT 格式
    processor.export_outputs("outputs.txt", format="txt")
    print(f"  ✓ outputs.txt (純文本)")

    # JSON 格式
    processor.export_outputs("outputs.json", format="json")
    print(f"  ✓ outputs.json (JSON)")

    # CSV 格式
    processor.export_outputs("outputs.csv", format="csv")
    print(f"  ✓ outputs.csv (CSV)")

    # 完整結果
    processor.save_results("full_results.json")
    print(f"  ✓ full_results.json (完整結果)")


# ============================================================================
# 範例 6: 性能比較（批次 vs 並行）
# ============================================================================


def example_6_performance_comparison():
    """性能比較"""
    print("\n" + "=" * 80)
    print("範例 6: 性能比較（批次 vs 並行）")
    print("=" * 80)

    generator = MockGenerator()
    inputs = [f"問題 {i}" for i in range(40)]

    print(f"\n輸入樣本數: {len(inputs)}")

    # 批次推理
    print(f"\n{'=' * 80}")
    print("批次推理（batch_size=8）:")
    print(f"{'=' * 80}")

    batch_processor = BatchProcessor(generator=generator, batch_size=8)
    batch_processor.process(inputs=inputs, show_progress=True, auto_save=False)
    batch_stats = batch_processor.get_stats()

    print(f"\n批次推理結果:")
    print(f"  總耗時: {batch_stats['total_time']:.2f}s")
    print(f"  吞吐量: {batch_stats['throughput']:.2f} 樣本/秒")

    # 並行推理
    print(f"\n{'=' * 80}")
    print("並行推理（4 線程）:")
    print(f"{'=' * 80}")

    parallel_processor = ParallelProcessor(
        generator=generator, max_workers=4, mode="thread"
    )
    parallel_processor.process(inputs=inputs, show_progress=True)
    parallel_stats = parallel_processor.get_stats()

    print(f"\n並行推理結果:")
    print(f"  總耗時: {parallel_stats['total_time']:.2f}s")
    print(f"  吞吐量: {parallel_stats['throughput']:.2f} 樣本/秒")

    # 比較
    print(f"\n{'=' * 80}")
    print("性能比較:")
    print(f"{'=' * 80}")

    speedup = batch_stats["total_time"] / parallel_stats["total_time"]
    print(f"  並行加速比: {speedup:.2f}x")
    print(
        f"  吞吐量提升: {(parallel_stats['throughput'] / batch_stats['throughput'] - 1) * 100:.1f}%"
    )


# ============================================================================
# 主程序
# ============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("批次推理範例")
    print("=" * 80)

    # 運行所有範例
    example_1_basic_batch()
    example_2_with_templates()
    example_3_parallel()
    example_4_error_handling()
    example_5_export()
    example_6_performance_comparison()

    print("\n" + "=" * 80)
    print("範例完成！")
    print("=" * 80)
    print("""
主要功能:

1. 批次推理
   - 自動分批處理
   - 進度追蹤（tqdm）
   - 自動保存檢查點
   - 錯誤處理和重試

2. 並行推理
   - 多線程/多進程支援
   - 自動任務分配
   - 結果順序保持
   - 性能分析

3. 結果管理
   - 多種格式導出（TXT/JSON/CSV）
   - 統計資訊追蹤
   - 成功/失敗過濾
   - 檢查點保存

4. 錯誤處理
   - 自動捕獲錯誤
   - 錯誤統計
   - 失敗樣本重試
   - 詳細錯誤記錄

使用建議:
    - 小批次推理: 使用 BatchProcessor
    - 大規模推理: 使用 ParallelProcessor
    - I/O 密集: 使用多線程（thread）
    - CPU 密集: 使用多進程（process）
    - 長時間任務: 啟用 auto_save
    """)
