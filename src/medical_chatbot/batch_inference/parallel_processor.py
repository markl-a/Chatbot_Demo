"""
並行推理處理器

提供多線程和多進程的批次推理功能。
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import json
import time
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from tqdm import tqdm

from loguru import logger

from ..utils.exceptions import BatchInferenceException


class ParallelProcessor:
    """並行推理處理器"""

    def __init__(
        self,
        generator: Any,
        max_workers: int = 4,
        mode: str = "thread",
        save_dir: Optional[str] = None,
    ):
        """
        初始化並行處理器

        Args:
            generator: 生成器實例
            max_workers: 最大工作線程/進程數
            mode: 並行模式（thread/process）
            save_dir: 結果保存目錄
        """
        self.generator = generator
        self.max_workers = max_workers
        self.mode = mode
        self.save_dir = Path(save_dir) if save_dir else Path("./parallel_results")
        self.save_dir.mkdir(parents=True, exist_ok=True)

        # 結果存儲
        self.results = []
        self.errors = []

        # 統計資訊
        self.total_processed = 0
        self.total_errors = 0
        self.start_time = None
        self.end_time = None

        logger.info(
            f"並行處理器初始化: max_workers={max_workers}, mode={mode}"
        )

    # ========================================================================
    # 並行推理
    # ========================================================================

    def process(
        self,
        inputs: List[str],
        show_progress: bool = True,
        **generate_kwargs,
    ) -> List[Dict[str, Any]]:
        """
        並行推理

        Args:
            inputs: 輸入文本列表
            show_progress: 是否顯示進度條
            **generate_kwargs: 生成參數

        Returns:
            結果列表
        """
        self.start_time = time.time()
        self.results = []
        self.errors = []
        self.total_processed = 0
        self.total_errors = 0

        logger.info(
            f"開始並行推理: {len(inputs)} 個樣本, "
            f"{self.max_workers} 個 workers ({self.mode})"
        )

        # 選擇執行器
        executor_class = (
            ThreadPoolExecutor if self.mode == "thread" else ProcessPoolExecutor
        )

        # 並行處理
        with executor_class(max_workers=self.max_workers) as executor:
            # 提交任務
            future_to_input = {
                executor.submit(
                    self._process_single, input_text, **generate_kwargs
                ): input_text
                for input_text in inputs
            }

            # 收集結果
            if show_progress:
                iterator = tqdm(
                    as_completed(future_to_input),
                    total=len(inputs),
                    desc="並行推理",
                )
            else:
                iterator = as_completed(future_to_input)

            for future in iterator:
                try:
                    result = future.result()
                    self.results.append(result)

                    if result["status"] == "success":
                        self.total_processed += 1
                    else:
                        self.total_errors += 1
                        self.errors.append(result)

                except Exception as e:
                    logger.error(f"任務執行失敗: {e}")
                    input_text = future_to_input[future]
                    error = {
                        "input": input_text,
                        "error": str(e),
                        "timestamp": datetime.now().isoformat(),
                        "status": "error",
                    }
                    self.results.append(error)
                    self.errors.append(error)
                    self.total_errors += 1

        self.end_time = time.time()

        logger.info(
            f"並行推理完成: {self.total_processed} 個成功, "
            f"{self.total_errors} 個錯誤, "
            f"總耗時 {self.end_time - self.start_time:.2f}s"
        )

        # 按原始順序排序（如果需要）
        self._sort_results_by_input_order(inputs)

        return self.results

    def _process_single(self, input_text: str, **generate_kwargs) -> Dict[str, Any]:
        """處理單個輸入"""
        try:
            start_time = time.time()
            output = self.generator.generate(input_text, **generate_kwargs)
            generation_time = time.time() - start_time

            return {
                "input": input_text,
                "output": output,
                "generation_time": generation_time,
                "timestamp": datetime.now().isoformat(),
                "status": "success",
            }

        except Exception as e:
            logger.error(f"生成失敗 (input={input_text[:50]}...): {e}")

            return {
                "input": input_text,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "status": "error",
            }

    def _sort_results_by_input_order(self, original_inputs: List[str]):
        """按原始輸入順序排序結果"""
        input_to_index = {inp: idx for idx, inp in enumerate(original_inputs)}

        self.results.sort(key=lambda r: input_to_index.get(r["input"], float("inf")))

    # ========================================================================
    # 統計資訊
    # ========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """獲取統計資訊"""
        total_time = (
            (self.end_time or time.time()) - self.start_time
            if self.start_time
            else 0
        )

        successful_results = [
            r for r in self.results if r.get("status") == "success"
        ]

        stats = {
            "total_inputs": len(self.results),
            "total_processed": self.total_processed,
            "total_errors": self.total_errors,
            "error_rate": (
                self.total_errors / len(self.results) if self.results else 0.0
            ),
            "total_time": total_time,
            "avg_time_per_sample": (
                total_time / len(successful_results) if successful_results else 0.0
            ),
            "throughput": (
                len(successful_results) / total_time if total_time > 0 else 0.0
            ),
            "max_workers": self.max_workers,
            "mode": self.mode,
        }

        return stats

    # ========================================================================
    # 結果保存
    # ========================================================================

    def save_results(self, filename: Optional[str] = None) -> str:
        """保存結果"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"parallel_results_{timestamp}.json"

        filepath = self.save_dir / filename

        output = {
            "stats": self.get_stats(),
            "results": self.results,
            "errors": self.errors,
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        logger.info(f"結果已保存: {filepath}")

        return str(filepath)

    # ========================================================================
    # 結果過濾
    # ========================================================================

    def get_successful_results(self) -> List[Dict[str, Any]]:
        """獲取成功的結果"""
        return [r for r in self.results if r.get("status") == "success"]

    def get_failed_results(self) -> List[Dict[str, Any]]:
        """獲取失敗的結果"""
        return [r for r in self.results if r.get("status") == "error"]

    # ========================================================================
    # 性能分析
    # ========================================================================

    def analyze_performance(self) -> Dict[str, Any]:
        """
        分析性能

        Returns:
            性能分析報告
        """
        successful_results = self.get_successful_results()

        if not successful_results:
            return {"message": "沒有成功的結果可供分析"}

        generation_times = [r["generation_time"] for r in successful_results]

        import numpy as np

        analysis = {
            "count": len(generation_times),
            "total_time": sum(generation_times),
            "mean_time": np.mean(generation_times),
            "median_time": np.median(generation_times),
            "std_time": np.std(generation_times),
            "min_time": min(generation_times),
            "max_time": max(generation_times),
            "percentile_25": np.percentile(generation_times, 25),
            "percentile_75": np.percentile(generation_times, 75),
            "percentile_95": np.percentile(generation_times, 95),
            "speedup": (
                len(successful_results) * np.mean(generation_times)
            ) / (self.end_time - self.start_time)
            if self.end_time and self.start_time
            else None,
        }

        return analysis

    def __repr__(self) -> str:
        """字串表示"""
        stats = self.get_stats()
        return (
            f"ParallelProcessor(mode={self.mode}, "
            f"workers={self.max_workers}, "
            f"processed={stats['total_processed']}, "
            f"throughput={stats['throughput']:.2f}/s)"
        )
