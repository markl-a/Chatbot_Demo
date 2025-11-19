"""
批次推理處理器

提供批次推理、進度追蹤和結果管理功能。
"""
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
from pathlib import Path
import json
import time
from tqdm import tqdm

from loguru import logger

from ..utils.exceptions import BatchInferenceException


class BatchProcessor:
    """批次推理處理器"""

    def __init__(
        self,
        generator: Any,
        batch_size: int = 8,
        save_dir: Optional[str] = None,
        save_interval: int = 100,
    ):
        """
        初始化批次處理器

        Args:
            generator: 生成器實例
            batch_size: 批次大小
            save_dir: 結果保存目錄
            save_interval: 自動保存間隔（樣本數）
        """
        self.generator = generator
        self.batch_size = batch_size
        self.save_dir = Path(save_dir) if save_dir else Path("./batch_results")
        self.save_interval = save_interval
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
            f"批次處理器初始化: batch_size={batch_size}, "
            f"save_dir={self.save_dir}"
        )

    # ========================================================================
    # 批次推理
    # ========================================================================

    def process(
        self,
        inputs: List[str],
        prompts: Optional[List[str]] = None,
        show_progress: bool = True,
        auto_save: bool = True,
        **generate_kwargs,
    ) -> List[Dict[str, Any]]:
        """
        批次推理

        Args:
            inputs: 輸入文本列表
            prompts: 提示模板列表（與 inputs 一一對應）
            show_progress: 是否顯示進度條
            auto_save: 是否自動保存
            **generate_kwargs: 生成參數

        Returns:
            結果列表
        """
        if prompts and len(prompts) != len(inputs):
            raise BatchInferenceException(
                f"prompts 和 inputs 長度不匹配: {len(prompts)} vs {len(inputs)}"
            )

        self.start_time = time.time()
        self.results = []
        self.errors = []
        self.total_processed = 0
        self.total_errors = 0

        logger.info(f"開始批次推理: {len(inputs)} 個樣本")

        # 創建進度條
        iterator = tqdm(
            range(0, len(inputs), self.batch_size),
            desc="批次推理",
            disable=not show_progress,
        )

        for i in iterator:
            batch_inputs = inputs[i : i + self.batch_size]
            batch_prompts = prompts[i : i + self.batch_size] if prompts else None

            # 處理批次
            batch_results = self._process_batch(
                batch_inputs, batch_prompts, **generate_kwargs
            )

            self.results.extend(batch_results)
            self.total_processed += len(batch_results)

            # 自動保存
            if auto_save and self.total_processed % self.save_interval == 0:
                self._checkpoint_save()

            # 更新進度條
            if show_progress:
                iterator.set_postfix(
                    {
                        "processed": self.total_processed,
                        "errors": self.total_errors,
                        "avg_time": f"{self._get_avg_time():.2f}s",
                    }
                )

        self.end_time = time.time()

        # 最終保存
        if auto_save:
            self.save_results()

        logger.info(
            f"批次推理完成: {self.total_processed} 個樣本, "
            f"{self.total_errors} 個錯誤, "
            f"總耗時 {self.end_time - self.start_time:.2f}s"
        )

        return self.results

    def _process_batch(
        self,
        batch_inputs: List[str],
        batch_prompts: Optional[List[str]] = None,
        **generate_kwargs,
    ) -> List[Dict[str, Any]]:
        """處理單個批次"""
        batch_results = []

        for idx, input_text in enumerate(batch_inputs):
            try:
                # 構建完整提示
                if batch_prompts:
                    prompt = batch_prompts[idx].format(input=input_text)
                else:
                    prompt = input_text

                # 生成
                start_time = time.time()
                output = self.generator.generate(prompt, **generate_kwargs)
                generation_time = time.time() - start_time

                # 記錄結果
                result = {
                    "input": input_text,
                    "prompt": prompt,
                    "output": output,
                    "generation_time": generation_time,
                    "timestamp": datetime.now().isoformat(),
                    "status": "success",
                }

                batch_results.append(result)

            except Exception as e:
                logger.error(f"處理失敗 (input={input_text[:50]}...): {e}")

                # 記錄錯誤
                error = {
                    "input": input_text,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                    "status": "error",
                }

                batch_results.append(error)
                self.errors.append(error)
                self.total_errors += 1

        return batch_results

    # ========================================================================
    # 進度追蹤
    # ========================================================================

    def _get_avg_time(self) -> float:
        """計算平均生成時間"""
        if not self.results:
            return 0.0

        successful_results = [
            r for r in self.results if r.get("status") == "success"
        ]

        if not successful_results:
            return 0.0

        total_time = sum(r["generation_time"] for r in successful_results)
        return total_time / len(successful_results)

    def get_stats(self) -> Dict[str, Any]:
        """
        獲取統計資訊

        Returns:
            統計資訊字典
        """
        total_time = (
            (self.end_time or time.time()) - self.start_time
            if self.start_time
            else 0
        )

        successful_results = [
            r for r in self.results if r.get("status") == "success"
        ]

        stats = {
            "total_inputs": self.total_processed + self.total_errors,
            "total_processed": self.total_processed,
            "total_errors": self.total_errors,
            "error_rate": (
                self.total_errors / (self.total_processed + self.total_errors)
                if (self.total_processed + self.total_errors) > 0
                else 0.0
            ),
            "total_time": total_time,
            "avg_time_per_sample": (
                total_time / len(successful_results) if successful_results else 0.0
            ),
            "throughput": (
                len(successful_results) / total_time if total_time > 0 else 0.0
            ),
        }

        return stats

    # ========================================================================
    # 結果保存和載入
    # ========================================================================

    def save_results(self, filename: Optional[str] = None) -> str:
        """
        保存結果

        Args:
            filename: 檔案名稱

        Returns:
            保存的檔案路徑
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"batch_results_{timestamp}.json"

        filepath = self.save_dir / filename

        output = {
            "stats": self.get_stats(),
            "results": self.results,
            "errors": self.errors,
            "metadata": {
                "batch_size": self.batch_size,
                "start_time": (
                    datetime.fromtimestamp(self.start_time).isoformat()
                    if self.start_time
                    else None
                ),
                "end_time": (
                    datetime.fromtimestamp(self.end_time).isoformat()
                    if self.end_time
                    else None
                ),
            },
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        logger.info(f"結果已保存: {filepath}")

        return str(filepath)

    def _checkpoint_save(self):
        """檢查點保存"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"checkpoint_{timestamp}_{self.total_processed}.json"
        self.save_results(filename)
        logger.info(f"檢查點保存: {filename}")

    def load_results(self, filepath: str):
        """
        載入結果

        Args:
            filepath: 檔案路徑
        """
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.results = data.get("results", [])
        self.errors = data.get("errors", [])

        logger.info(f"結果已載入: {filepath}")

    # ========================================================================
    # 結果過濾和導出
    # ========================================================================

    def get_successful_results(self) -> List[Dict[str, Any]]:
        """獲取成功的結果"""
        return [r for r in self.results if r.get("status") == "success"]

    def get_failed_results(self) -> List[Dict[str, Any]]:
        """獲取失敗的結果"""
        return [r for r in self.results if r.get("status") == "error"]

    def export_outputs(self, output_file: str, format: str = "txt"):
        """
        導出生成結果

        Args:
            output_file: 輸出檔案路徑
            format: 格式（txt/json/csv）
        """
        successful_results = self.get_successful_results()

        if format == "txt":
            with open(output_file, "w", encoding="utf-8") as f:
                for result in successful_results:
                    f.write(result["output"] + "\n")

        elif format == "json":
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(
                    [{"input": r["input"], "output": r["output"]} for r in successful_results],
                    f,
                    ensure_ascii=False,
                    indent=2,
                )

        elif format == "csv":
            import csv

            with open(output_file, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(
                    f, fieldnames=["input", "output", "generation_time"]
                )
                writer.writeheader()
                for r in successful_results:
                    writer.writerow(
                        {
                            "input": r["input"],
                            "output": r["output"],
                            "generation_time": r["generation_time"],
                        }
                    )

        else:
            raise ValueError(f"不支援的格式: {format}")

        logger.info(f"結果已導出: {output_file}")

    # ========================================================================
    # 重試失敗的樣本
    # ========================================================================

    def retry_failed(
        self,
        max_retries: int = 3,
        show_progress: bool = True,
        **generate_kwargs,
    ) -> List[Dict[str, Any]]:
        """
        重試失敗的樣本

        Args:
            max_retries: 最大重試次數
            show_progress: 是否顯示進度條
            **generate_kwargs: 生成參數

        Returns:
            重試結果
        """
        failed_results = self.get_failed_results()

        if not failed_results:
            logger.info("沒有失敗的樣本需要重試")
            return []

        logger.info(f"重試 {len(failed_results)} 個失敗樣本，最大重試 {max_retries} 次")

        retry_results = []
        remaining_failures = failed_results.copy()

        for retry_num in range(max_retries):
            if not remaining_failures:
                break

            logger.info(f"第 {retry_num + 1} 次重試: {len(remaining_failures)} 個樣本")

            current_failures = []

            iterator = tqdm(
                remaining_failures,
                desc=f"重試 {retry_num + 1}/{max_retries}",
                disable=not show_progress,
            )

            for failed in iterator:
                try:
                    start_time = time.time()
                    output = self.generator.generate(
                        failed["input"], **generate_kwargs
                    )
                    generation_time = time.time() - start_time

                    result = {
                        "input": failed["input"],
                        "output": output,
                        "generation_time": generation_time,
                        "timestamp": datetime.now().isoformat(),
                        "status": "success",
                        "retries": retry_num + 1,
                    }

                    retry_results.append(result)
                    self.total_processed += 1
                    self.total_errors -= 1

                except Exception as e:
                    logger.error(f"重試失敗: {e}")
                    current_failures.append(failed)

            remaining_failures = current_failures

        logger.info(
            f"重試完成: {len(retry_results)} 個成功, "
            f"{len(remaining_failures)} 個仍然失敗"
        )

        return retry_results

    # ========================================================================
    # 特殊方法
    # ========================================================================

    def __repr__(self) -> str:
        """字串表示"""
        stats = self.get_stats()
        return (
            f"BatchProcessor(processed={stats['total_processed']}, "
            f"errors={stats['total_errors']}, "
            f"error_rate={stats['error_rate']:.2%})"
        )
