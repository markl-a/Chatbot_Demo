"""
模型評估器

提供完整的模型評估功能。
"""
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
import time
import json
from pathlib import Path

from loguru import logger
import numpy as np

from .metrics import EvaluationMetrics
from ..utils.exceptions import EvaluationException


class ModelEvaluator:
    """模型評估器"""

    def __init__(
        self,
        model_name: str,
        generator: Optional[Any] = None,
        metrics: Optional[List[str]] = None,
        save_dir: Optional[str] = None,
    ):
        """
        初始化模型評估器

        Args:
            model_name: 模型名稱
            generator: 生成器實例
            metrics: 要評估的指標列表
            save_dir: 結果保存目錄
        """
        self.model_name = model_name
        self.generator = generator
        self.metrics = metrics or [
            "bleu",
            "rouge-1",
            "rouge-2",
            "rouge-l",
            "f1",
            "exact_match",
        ]
        self.save_dir = Path(save_dir) if save_dir else Path("./evaluation_results")
        self.save_dir.mkdir(parents=True, exist_ok=True)

        # 評估結果
        self.results = []

        logger.info(f"模型評估器初始化: model={model_name}, metrics={self.metrics}")

    # ========================================================================
    # 單個樣本評估
    # ========================================================================

    def evaluate_sample(
        self,
        prompt: str,
        reference: str,
        generated: Optional[str] = None,
        **generate_kwargs,
    ) -> Dict[str, Any]:
        """
        評估單個樣本

        Args:
            prompt: 輸入提示
            reference: 參考答案
            generated: 生成的答案（如果提供則跳過生成）
            **generate_kwargs: 生成參數

        Returns:
            評估結果字典
        """
        try:
            # 生成答案（如果未提供）
            if generated is None:
                if not self.generator:
                    raise EvaluationException("未提供生成器且未提供生成文本")

                start_time = time.time()
                generated = self.generator.generate(prompt, **generate_kwargs)
                generation_time = time.time() - start_time
            else:
                generation_time = 0.0

            # 計算指標
            scores = {}
            for metric in self.metrics:
                if metric == "bleu":
                    scores[metric] = EvaluationMetrics.bleu_score(reference, generated)
                elif metric.startswith("rouge"):
                    rouge_result = EvaluationMetrics.rouge_score(
                        reference, generated, metric
                    )
                    scores[metric] = rouge_result["f1"]
                    scores[f"{metric}_precision"] = rouge_result["precision"]
                    scores[f"{metric}_recall"] = rouge_result["recall"]
                elif metric == "f1":
                    scores[metric] = EvaluationMetrics.f1_score(reference, generated)
                elif metric == "exact_match":
                    scores[metric] = EvaluationMetrics.exact_match(reference, generated)
                elif metric == "edit_distance":
                    scores[metric] = EvaluationMetrics.edit_distance(
                        reference, generated
                    )

            # 記錄結果
            result = {
                "prompt": prompt,
                "reference": reference,
                "generated": generated,
                "scores": scores,
                "generation_time": generation_time,
                "timestamp": datetime.now().isoformat(),
            }

            self.results.append(result)

            return result

        except Exception as e:
            logger.error(f"評估樣本失敗: {e}")
            raise EvaluationException(f"評估失敗: {str(e)}")

    # ========================================================================
    # 批次評估
    # ========================================================================

    def evaluate_dataset(
        self,
        dataset: List[Dict[str, str]],
        prompt_key: str = "prompt",
        reference_key: str = "reference",
        batch_size: int = 8,
        **generate_kwargs,
    ) -> Dict[str, Any]:
        """
        評估整個資料集

        Args:
            dataset: 資料集（包含 prompt 和 reference 的字典列表）
            prompt_key: 提示鍵名
            reference_key: 參考答案鍵名
            batch_size: 批次大小
            **generate_kwargs: 生成參數

        Returns:
            評估結果摘要
        """
        logger.info(f"開始評估資料集: {len(dataset)} 個樣本")

        all_scores = {metric: [] for metric in self.metrics}
        all_scores["generation_time"] = []

        # 分批處理
        for i in range(0, len(dataset), batch_size):
            batch = dataset[i : i + batch_size]

            for sample in batch:
                prompt = sample[prompt_key]
                reference = sample[reference_key]

                # 評估樣本
                result = self.evaluate_sample(
                    prompt=prompt,
                    reference=reference,
                    **generate_kwargs,
                )

                # 收集分數
                for metric in self.metrics:
                    if metric in result["scores"]:
                        all_scores[metric].append(result["scores"][metric])

                all_scores["generation_time"].append(result["generation_time"])

            logger.info(
                f"進度: {min(i + batch_size, len(dataset))}/{len(dataset)} "
                f"({min(i + batch_size, len(dataset)) / len(dataset) * 100:.1f}%)"
            )

        # 計算摘要統計
        summary = {
            "model_name": self.model_name,
            "total_samples": len(dataset),
            "metrics": {},
            "generation_stats": {
                "total_time": sum(all_scores["generation_time"]),
                "avg_time": np.mean(all_scores["generation_time"]),
                "std_time": np.std(all_scores["generation_time"]),
            },
            "timestamp": datetime.now().isoformat(),
        }

        for metric in self.metrics:
            if all_scores[metric]:
                summary["metrics"][metric] = {
                    "mean": float(np.mean(all_scores[metric])),
                    "std": float(np.std(all_scores[metric])),
                    "min": float(np.min(all_scores[metric])),
                    "max": float(np.max(all_scores[metric])),
                    "median": float(np.median(all_scores[metric])),
                }

        logger.info(f"評估完成: {summary['metrics']}")

        return summary

    # ========================================================================
    # 人工評估
    # ========================================================================

    def collect_human_ratings(
        self,
        prompts: List[str],
        generated_texts: List[str],
        rating_scale: int = 5,
        aspects: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        收集人工評分

        Args:
            prompts: 提示列表
            generated_texts: 生成文本列表
            rating_scale: 評分範圍（1-rating_scale）
            aspects: 評估方面（如相關性、流暢性、準確性）

        Returns:
            人工評分結果列表
        """
        if not aspects:
            aspects = ["relevance", "fluency", "accuracy", "helpfulness"]

        ratings = []

        for i, (prompt, generated) in enumerate(zip(prompts, generated_texts)):
            print(f"\n{'=' * 80}")
            print(f"樣本 {i + 1}/{len(prompts)}")
            print(f"{'=' * 80}")
            print(f"提示: {prompt}")
            print(f"\n生成: {generated}")
            print(f"\n請為以下方面評分（1-{rating_scale}）:")

            sample_ratings = {"prompt": prompt, "generated": generated, "ratings": {}}

            for aspect in aspects:
                while True:
                    try:
                        rating = int(
                            input(f"  {aspect} ({1}-{rating_scale}): ").strip()
                        )
                        if 1 <= rating <= rating_scale:
                            sample_ratings["ratings"][aspect] = rating
                            break
                        else:
                            print(f"    請輸入 1-{rating_scale} 之間的數字")
                    except ValueError:
                        print("    請輸入有效的數字")

            # 可選：收集評論
            comment = input(f"\n  評論（可選，直接 Enter 跳過）: ").strip()
            if comment:
                sample_ratings["comment"] = comment

            ratings.append(sample_ratings)

        return ratings

    # ========================================================================
    # A/B 測試
    # ========================================================================

    def ab_test(
        self,
        prompts: List[str],
        generations_a: List[str],
        generations_b: List[str],
        labels: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        A/B 測試（人工偏好）

        Args:
            prompts: 提示列表
            generations_a: 模型 A 的生成列表
            generations_b: 模型 B 的生成列表
            labels: 模型標籤（如 ["Model A", "Model B"]）

        Returns:
            A/B 測試結果
        """
        if not labels:
            labels = ["A", "B"]

        preferences = []
        ties = 0

        for i, (prompt, gen_a, gen_b) in enumerate(
            zip(prompts, generations_a, generations_b)
        ):
            print(f"\n{'=' * 80}")
            print(f"樣本 {i + 1}/{len(prompts)}")
            print(f"{'=' * 80}")
            print(f"提示: {prompt}")
            print(f"\n{labels[0]}: {gen_a}")
            print(f"\n{labels[1]}: {gen_b}")

            while True:
                choice = input(
                    f"\n請選擇更好的回覆 ({labels[0]}/{labels[1]}/Tie): "
                ).strip().upper()

                if choice in [labels[0].upper(), "A", "1"]:
                    preferences.append("A")
                    break
                elif choice in [labels[1].upper(), "B", "2"]:
                    preferences.append("B")
                    break
                elif choice in ["TIE", "T", "0"]:
                    preferences.append("Tie")
                    ties += 1
                    break
                else:
                    print("請輸入有效的選擇")

        # 統計結果
        a_wins = preferences.count("A")
        b_wins = preferences.count("B")
        total = len(preferences)

        results = {
            "total_samples": total,
            "preferences": {
                labels[0]: {"count": a_wins, "percentage": a_wins / total * 100},
                labels[1]: {"count": b_wins, "percentage": b_wins / total * 100},
                "Tie": {"count": ties, "percentage": ties / total * 100},
            },
            "winner": labels[0] if a_wins > b_wins else labels[1] if b_wins > a_wins else "Tie",
        }

        return results

    # ========================================================================
    # 結果保存和載入
    # ========================================================================

    def save_results(self, filename: Optional[str] = None) -> str:
        """
        保存評估結果

        Args:
            filename: 檔案名稱（自動生成如果未提供）

        Returns:
            保存的檔案路徑
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.model_name}_{timestamp}.json"

        filepath = self.save_dir / filename

        # 計算摘要
        summary = self.get_summary()

        # 保存
        output = {"summary": summary, "details": self.results}

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        logger.info(f"評估結果已保存: {filepath}")

        return str(filepath)

    def load_results(self, filepath: str):
        """
        載入評估結果

        Args:
            filepath: 檔案路徑
        """
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.results = data.get("details", [])

        logger.info(f"評估結果已載入: {filepath}")

    def get_summary(self) -> Dict[str, Any]:
        """
        獲取評估摘要

        Returns:
            摘要統計
        """
        if not self.results:
            return {}

        all_scores = {metric: [] for metric in self.metrics}

        for result in self.results:
            for metric in self.metrics:
                if metric in result["scores"]:
                    all_scores[metric].append(result["scores"][metric])

        summary = {
            "model_name": self.model_name,
            "total_samples": len(self.results),
            "metrics": {},
        }

        for metric in self.metrics:
            if all_scores[metric]:
                summary["metrics"][metric] = {
                    "mean": float(np.mean(all_scores[metric])),
                    "std": float(np.std(all_scores[metric])),
                    "min": float(np.min(all_scores[metric])),
                    "max": float(np.max(all_scores[metric])),
                }

        return summary

    # ========================================================================
    # 報告生成
    # ========================================================================

    def generate_report(self, output_format: str = "markdown") -> str:
        """
        生成評估報告

        Args:
            output_format: 輸出格式（markdown/html）

        Returns:
            報告內容
        """
        summary = self.get_summary()

        if output_format == "markdown":
            report = self._generate_markdown_report(summary)
        elif output_format == "html":
            report = self._generate_html_report(summary)
        else:
            raise ValueError(f"不支援的格式: {output_format}")

        return report

    def _generate_markdown_report(self, summary: Dict[str, Any]) -> str:
        """生成 Markdown 報告"""
        lines = [
            f"# 模型評估報告",
            f"",
            f"## 基本資訊",
            f"",
            f"- **模型**: {summary['model_name']}",
            f"- **樣本數**: {summary['total_samples']}",
            f"- **生成時間**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"",
            f"## 評估指標",
            f"",
            f"| 指標 | 平均值 | 標準差 | 最小值 | 最大值 |",
            f"|------|--------|--------|--------|--------|",
        ]

        for metric, stats in summary["metrics"].items():
            lines.append(
                f"| {metric} | {stats['mean']:.4f} | {stats['std']:.4f} | "
                f"{stats['min']:.4f} | {stats['max']:.4f} |"
            )

        lines.extend(
            [
                f"",
                f"## 詳細結果",
                f"",
                f"查看完整的評估結果，請參閱保存的 JSON 檔案。",
            ]
        )

        return "\n".join(lines)

    def _generate_html_report(self, summary: Dict[str, Any]) -> str:
        """生成 HTML 報告"""
        # 簡化版 HTML 報告
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>模型評估報告 - {summary['model_name']}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #4CAF50; color: white; }}
    </style>
</head>
<body>
    <h1>模型評估報告</h1>
    <h2>基本資訊</h2>
    <ul>
        <li><strong>模型</strong>: {summary['model_name']}</li>
        <li><strong>樣本數</strong>: {summary['total_samples']}</li>
    </ul>
    <h2>評估指標</h2>
    <table>
        <tr>
            <th>指標</th>
            <th>平均值</th>
            <th>標準差</th>
            <th>最小值</th>
            <th>最大值</th>
        </tr>
"""

        for metric, stats in summary["metrics"].items():
            html += f"""
        <tr>
            <td>{metric}</td>
            <td>{stats['mean']:.4f}</td>
            <td>{stats['std']:.4f}</td>
            <td>{stats['min']:.4f}</td>
            <td>{stats['max']:.4f}</td>
        </tr>
"""

        html += """
    </table>
</body>
</html>
"""

        return html
