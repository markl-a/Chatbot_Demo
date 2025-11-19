"""
模型比較器

提供多個模型的並排比較功能。
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
from pathlib import Path
import time

from loguru import logger
import numpy as np
from tabulate import tabulate

from .metrics import EvaluationMetrics
from .evaluator import ModelEvaluator
from ..utils.exceptions import EvaluationException


class ModelComparator:
    """模型比較器"""

    def __init__(
        self,
        models: Dict[str, Any],
        metrics: Optional[List[str]] = None,
        save_dir: Optional[str] = None,
    ):
        """
        初始化模型比較器

        Args:
            models: 模型字典 {"model_name": generator_instance}
            metrics: 要評估的指標列表
            save_dir: 結果保存目錄
        """
        self.models = models
        self.model_names = list(models.keys())
        self.metrics = metrics or [
            "bleu",
            "rouge-1",
            "rouge-2",
            "rouge-l",
            "f1",
            "exact_match",
        ]
        self.save_dir = Path(save_dir) if save_dir else Path("./comparison_results")
        self.save_dir.mkdir(parents=True, exist_ok=True)

        # 為每個模型創建評估器
        self.evaluators = {
            name: ModelEvaluator(
                model_name=name, generator=gen, metrics=self.metrics
            )
            for name, gen in models.items()
        }

        logger.info(
            f"模型比較器初始化: models={self.model_names}, metrics={self.metrics}"
        )

    # ========================================================================
    # 並排比較
    # ========================================================================

    def compare_on_dataset(
        self,
        dataset: List[Dict[str, str]],
        prompt_key: str = "prompt",
        reference_key: str = "reference",
        **generate_kwargs,
    ) -> Dict[str, Any]:
        """
        在資料集上比較所有模型

        Args:
            dataset: 資料集
            prompt_key: 提示鍵名
            reference_key: 參考答案鍵名
            **generate_kwargs: 生成參數

        Returns:
            比較結果
        """
        logger.info(
            f"開始比較 {len(self.models)} 個模型，共 {len(dataset)} 個樣本"
        )

        # 評估所有模型
        all_results = {}
        for model_name in self.model_names:
            logger.info(f"評估模型: {model_name}")
            evaluator = self.evaluators[model_name]

            results = evaluator.evaluate_dataset(
                dataset=dataset,
                prompt_key=prompt_key,
                reference_key=reference_key,
                **generate_kwargs,
            )

            all_results[model_name] = results

        # 生成比較表
        comparison = self._generate_comparison_table(all_results)

        # 排名
        rankings = self._rank_models(all_results)

        output = {
            "models": self.model_names,
            "total_samples": len(dataset),
            "results": all_results,
            "comparison": comparison,
            "rankings": rankings,
            "timestamp": datetime.now().isoformat(),
        }

        logger.info(f"比較完成: {comparison}")

        return output

    def compare_single_prompt(
        self,
        prompt: str,
        reference: Optional[str] = None,
        **generate_kwargs,
    ) -> Dict[str, Any]:
        """
        在單個提示上比較所有模型

        Args:
            prompt: 輸入提示
            reference: 參考答案（可選）
            **generate_kwargs: 生成參數

        Returns:
            比較結果
        """
        logger.info(f"比較單個提示: {prompt[:50]}...")

        results = {}

        for model_name, generator in self.models.items():
            start_time = time.time()
            generated = generator.generate(prompt, **generate_kwargs)
            generation_time = time.time() - start_time

            result = {
                "generated": generated,
                "generation_time": generation_time,
            }

            # 如果提供了參考答案，計算指標
            if reference:
                scores = {}
                for metric in self.metrics:
                    if metric == "bleu":
                        scores[metric] = EvaluationMetrics.bleu_score(
                            reference, generated
                        )
                    elif metric.startswith("rouge"):
                        rouge_result = EvaluationMetrics.rouge_score(
                            reference, generated, metric
                        )
                        scores[metric] = rouge_result["f1"]
                    elif metric == "f1":
                        scores[metric] = EvaluationMetrics.f1_score(
                            reference, generated
                        )
                    elif metric == "exact_match":
                        scores[metric] = EvaluationMetrics.exact_match(
                            reference, generated
                        )

                result["scores"] = scores

            results[model_name] = result

        return {
            "prompt": prompt,
            "reference": reference,
            "results": results,
            "timestamp": datetime.now().isoformat(),
        }

    # ========================================================================
    # 顯示結果
    # ========================================================================

    def display_comparison(
        self,
        comparison_result: Dict[str, Any],
        show_generations: bool = True,
    ):
        """
        顯示比較結果

        Args:
            comparison_result: compare_single_prompt 的結果
            show_generations: 是否顯示生成文本
        """
        print(f"\n{'=' * 100}")
        print(f"模型比較結果")
        print(f"{'=' * 100}")
        print(f"\n提示: {comparison_result['prompt']}")

        if comparison_result['reference']:
            print(f"\n參考答案: {comparison_result['reference']}")

        print(f"\n{'-' * 100}")

        for model_name in self.model_names:
            result = comparison_result["results"][model_name]

            print(f"\n【{model_name}】")

            if show_generations:
                print(f"\n生成: {result['generated']}")

            print(f"\n生成時間: {result['generation_time']:.3f}s")

            if "scores" in result:
                print(f"\n評估分數:")
                for metric, score in result["scores"].items():
                    print(f"  {metric}: {score:.4f}")

            print(f"\n{'-' * 100}")

        # 顯示對比表（如果有分數）
        if comparison_result['reference']:
            self._display_score_table(comparison_result)

    def _display_score_table(self, comparison_result: Dict[str, Any]):
        """顯示分數對比表"""
        print(f"\n評估分數對比:")

        # 準備表格數據
        headers = ["模型"] + self.metrics + ["生成時間(s)"]
        rows = []

        for model_name in self.model_names:
            result = comparison_result["results"][model_name]
            row = [model_name]

            if "scores" in result:
                for metric in self.metrics:
                    score = result["scores"].get(metric, 0.0)
                    row.append(f"{score:.4f}")
            else:
                row.extend(["-"] * len(self.metrics))

            row.append(f"{result['generation_time']:.3f}")

            rows.append(row)

        print(f"\n{tabulate(rows, headers=headers, tablefmt='grid')}")

    # ========================================================================
    # 統計分析
    # ========================================================================

    def _generate_comparison_table(
        self, all_results: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Dict[str, float]]:
        """生成比較表"""
        comparison = {}

        for metric in self.metrics:
            comparison[metric] = {}

            for model_name, results in all_results.items():
                if metric in results["metrics"]:
                    comparison[metric][model_name] = results["metrics"][metric]["mean"]

        return comparison

    def _rank_models(self, all_results: Dict[str, Dict[str, Any]]) -> Dict[str, List]:
        """對模型進行排名"""
        rankings = {}

        for metric in self.metrics:
            scores = []
            for model_name, results in all_results.items():
                if metric in results["metrics"]:
                    scores.append(
                        (model_name, results["metrics"][metric]["mean"])
                    )

            # 按分數排序（降序）
            scores.sort(key=lambda x: x[1], reverse=True)

            rankings[metric] = [
                {"rank": i + 1, "model": name, "score": score}
                for i, (name, score) in enumerate(scores)
            ]

        return rankings

    # ========================================================================
    # 統計檢驗
    # ========================================================================

    def statistical_test(
        self,
        model_a: str,
        model_b: str,
        metric: str = "bleu",
        alpha: float = 0.05,
    ) -> Dict[str, Any]:
        """
        對兩個模型進行統計檢驗

        Args:
            model_a: 模型 A 名稱
            model_b: 模型 B 名稱
            metric: 評估指標
            alpha: 顯著性水平

        Returns:
            統計檢驗結果
        """
        from scipy import stats

        # 獲取兩個模型的分數
        scores_a = [
            r["scores"][metric]
            for r in self.evaluators[model_a].results
            if metric in r["scores"]
        ]
        scores_b = [
            r["scores"][metric]
            for r in self.evaluators[model_b].results
            if metric in r["scores"]
        ]

        if not scores_a or not scores_b:
            raise EvaluationException(f"缺少 {metric} 分數")

        # 進行 t 檢驗
        t_stat, p_value = stats.ttest_ind(scores_a, scores_b)

        # 計算效應大小（Cohen's d）
        pooled_std = np.sqrt(
            (np.std(scores_a) ** 2 + np.std(scores_b) ** 2) / 2
        )
        cohens_d = (np.mean(scores_a) - np.mean(scores_b)) / pooled_std

        result = {
            "model_a": {
                "name": model_a,
                "mean": float(np.mean(scores_a)),
                "std": float(np.std(scores_a)),
            },
            "model_b": {
                "name": model_b,
                "mean": float(np.mean(scores_b)),
                "std": float(np.std(scores_b)),
            },
            "metric": metric,
            "t_statistic": float(t_stat),
            "p_value": float(p_value),
            "significant": p_value < alpha,
            "cohens_d": float(cohens_d),
            "effect_size": self._interpret_cohens_d(cohens_d),
        }

        logger.info(
            f"統計檢驗: {model_a} vs {model_b} ({metric}), "
            f"p={p_value:.4f}, d={cohens_d:.4f}"
        )

        return result

    @staticmethod
    def _interpret_cohens_d(d: float) -> str:
        """解釋 Cohen's d 效應大小"""
        abs_d = abs(d)
        if abs_d < 0.2:
            return "negligible"
        elif abs_d < 0.5:
            return "small"
        elif abs_d < 0.8:
            return "medium"
        else:
            return "large"

    # ========================================================================
    # 結果保存
    # ========================================================================

    def save_comparison(
        self, comparison_result: Dict[str, Any], filename: Optional[str] = None
    ) -> str:
        """
        保存比較結果

        Args:
            comparison_result: 比較結果
            filename: 檔案名稱

        Returns:
            保存的檔案路徑
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"comparison_{timestamp}.json"

        filepath = self.save_dir / filename

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(comparison_result, f, ensure_ascii=False, indent=2)

        logger.info(f"比較結果已保存: {filepath}")

        return str(filepath)

    # ========================================================================
    # 報告生成
    # ========================================================================

    def generate_comparison_report(
        self, comparison_result: Dict[str, Any], output_format: str = "markdown"
    ) -> str:
        """
        生成比較報告

        Args:
            comparison_result: 比較結果
            output_format: 輸出格式（markdown/html）

        Returns:
            報告內容
        """
        if output_format == "markdown":
            return self._generate_markdown_comparison_report(comparison_result)
        elif output_format == "html":
            return self._generate_html_comparison_report(comparison_result)
        else:
            raise ValueError(f"不支援的格式: {output_format}")

    def _generate_markdown_comparison_report(
        self, comparison_result: Dict[str, Any]
    ) -> str:
        """生成 Markdown 比較報告"""
        lines = [
            f"# 模型比較報告",
            f"",
            f"## 基本資訊",
            f"",
            f"- **模型數量**: {len(comparison_result['models'])}",
            f"- **模型**: {', '.join(comparison_result['models'])}",
            f"- **樣本數**: {comparison_result['total_samples']}",
            f"- **生成時間**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"",
            f"## 評估指標比較",
            f"",
        ]

        # 為每個指標生成表格
        for metric in self.metrics:
            if metric in comparison_result["comparison"]:
                lines.append(f"### {metric.upper()}")
                lines.append(f"")
                lines.append(f"| 模型 | 平均分數 | 排名 |")
                lines.append(f"|------|----------|------|")

                rankings = comparison_result["rankings"][metric]
                for item in rankings:
                    lines.append(
                        f"| {item['model']} | {item['score']:.4f} | {item['rank']} |"
                    )

                lines.append(f"")

        # 最佳模型
        lines.extend(
            [
                f"## 最佳模型",
                f"",
            ]
        )

        best_models = {}
        for metric, rankings in comparison_result["rankings"].items():
            if rankings:
                best_models[metric] = rankings[0]["model"]

        for metric, model in best_models.items():
            lines.append(f"- **{metric}**: {model}")

        return "\n".join(lines)

    def _generate_html_comparison_report(
        self, comparison_result: Dict[str, Any]
    ) -> str:
        """生成 HTML 比較報告"""
        # 簡化版 HTML
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>模型比較報告</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #4CAF50; color: white; }}
        .rank-1 {{ background-color: #FFD700; }}
        .rank-2 {{ background-color: #C0C0C0; }}
        .rank-3 {{ background-color: #CD7F32; }}
    </style>
</head>
<body>
    <h1>模型比較報告</h1>
    <h2>基本資訊</h2>
    <ul>
        <li><strong>模型數量</strong>: {len(comparison_result['models'])}</li>
        <li><strong>模型</strong>: {', '.join(comparison_result['models'])}</li>
        <li><strong>樣本數</strong>: {comparison_result['total_samples']}</li>
    </ul>
"""

        for metric in self.metrics:
            if metric in comparison_result["comparison"]:
                html += f"""
    <h2>{metric.upper()}</h2>
    <table>
        <tr>
            <th>排名</th>
            <th>模型</th>
            <th>平均分數</th>
        </tr>
"""
                rankings = comparison_result["rankings"][metric]
                for item in rankings:
                    rank_class = f"rank-{item['rank']}" if item['rank'] <= 3 else ""
                    html += f"""
        <tr class="{rank_class}">
            <td>{item['rank']}</td>
            <td>{item['model']}</td>
            <td>{item['score']:.4f}</td>
        </tr>
"""
                html += """
    </table>
"""

        html += """
</body>
</html>
"""

        return html
