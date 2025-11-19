"""
模型評估基礎範例

展示如何評估單個模型和比較多個模型。
"""
import sys
from pathlib import Path

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.medical_chatbot.evaluation import (
    EvaluationMetrics,
    ModelEvaluator,
    ModelComparator,
)


# ============================================================================
# 範例 1: 基本評估指標
# ============================================================================


def example_1_basic_metrics():
    """基本評估指標計算"""
    print("\n" + "=" * 80)
    print("範例 1: 基本評估指標")
    print("=" * 80)

    reference = "高血壓是一種血壓持續高於正常值的疾病，需要長期控制和管理。"
    candidate = "高血壓是血壓偏高的疾病，需要控制和管理。"

    print(f"\n參考答案: {reference}")
    print(f"候選答案: {candidate}")
    print(f"\n{'=' * 80}")

    # 1. BLEU 分數
    bleu = EvaluationMetrics.bleu_score(reference, candidate)
    print(f"\nBLEU 分數: {bleu:.4f}")
    print("  說明: 基於 N-gram 重疊的精確度指標，0-1 之間，越高越好")

    # 2. ROUGE 分數
    rouge_1 = EvaluationMetrics.rouge_score(reference, candidate, "rouge-1")
    rouge_2 = EvaluationMetrics.rouge_score(reference, candidate, "rouge-2")
    rouge_l = EvaluationMetrics.rouge_score(reference, candidate, "rouge-l")

    print(f"\nROUGE-1 F1: {rouge_1['f1']:.4f}")
    print(f"  Precision: {rouge_1['precision']:.4f}")
    print(f"  Recall: {rouge_1['recall']:.4f}")

    print(f"\nROUGE-2 F1: {rouge_2['f1']:.4f}")
    print(f"  說明: 基於 2-gram 重疊，考慮詞序")

    print(f"\nROUGE-L F1: {rouge_l['f1']:.4f}")
    print(f"  說明: 基於最長公共子序列")

    # 3. F1 分數
    f1 = EvaluationMetrics.f1_score(reference, candidate)
    print(f"\nToken F1: {f1:.4f}")
    print("  說明: 字符級別的精確率和召回率調和平均")

    # 4. 精確匹配
    exact = EvaluationMetrics.exact_match(reference, candidate)
    print(f"\n精確匹配: {exact:.4f}")
    print("  說明: 完全匹配為 1.0，否則為 0.0")

    # 5. 編輯距離
    edit_dist = EvaluationMetrics.edit_distance(reference, candidate)
    print(f"\n編輯距離: {edit_dist}")
    print(f"  說明: 需要 {edit_dist} 次編輯操作才能將候選答案轉換為參考答案")

    # 6. 長度比率
    length_ratio = EvaluationMetrics.length_ratio(reference, candidate)
    print(f"\n長度比率: {length_ratio:.4f}")
    print(f"  說明: 候選答案長度 / 參考答案長度")


# ============================================================================
# 範例 2: 批次評估
# ============================================================================


def example_2_batch_evaluation():
    """批次評估範例"""
    print("\n" + "=" * 80)
    print("範例 2: 批次評估")
    print("=" * 80)

    # 準備測試資料
    references = [
        "高血壓需要長期服藥控制。",
        "糖尿病患者應該控制飲食。",
        "定期運動有助於健康。",
    ]

    candidates = [
        "高血壓要長期吃藥。",
        "糖尿病人要注意飲食。",
        "運動對健康有益。",
    ]

    print(f"\n評估 {len(references)} 個樣本...")

    # 批次評估
    results = EvaluationMetrics.evaluate_batch(
        references=references,
        candidates=candidates,
        metrics=["bleu", "rouge-1", "rouge-2", "f1", "exact_match"],
    )

    print(f"\n{'=' * 80}")
    print("評估結果摘要:")
    print(f"{'=' * 80}")

    for metric, stats in results.items():
        print(f"\n{metric.upper()}:")
        print(f"  平均值: {stats['mean']:.4f}")
        if 'std' in stats:
            print(f"  標準差: {stats['std']:.4f}")
        print(f"  最小值: {stats['min']:.4f}")
        print(f"  最大值: {stats['max']:.4f}")


# ============================================================================
# 範例 3: 模型評估器
# ============================================================================


def example_3_model_evaluator():
    """使用模型評估器"""
    print("\n" + "=" * 80)
    print("範例 3: 模型評估器")
    print("=" * 80)

    # 創建模擬生成器（實際應用中使用真實的模型生成器）
    class MockGenerator:
        def generate(self, prompt: str, **kwargs):
            # 簡單的模擬生成
            responses = {
                "什麼是高血壓？": "高血壓是一種血壓持續高於正常值的慢性疾病。",
                "糖尿病如何預防？": "糖尿病預防包括控制體重、健康飲食和定期運動。",
                "運動的好處？": "運動可以增強心肺功能、控制體重、改善心情。",
            }
            return responses.get(prompt, "無法回答此問題。")

    # 創建評估器
    generator = MockGenerator()
    evaluator = ModelEvaluator(
        model_name="TAIDE-LX-8B",
        generator=generator,
        metrics=["bleu", "rouge-1", "rouge-2", "f1"],
    )

    print(f"\n評估器已創建: {evaluator.model_name}")

    # 評估單個樣本
    print(f"\n{'=' * 80}")
    print("評估單個樣本:")
    print(f"{'=' * 80}")

    result = evaluator.evaluate_sample(
        prompt="什麼是高血壓？",
        reference="高血壓是血壓持續偏高的疾病。",
    )

    print(f"\n提示: {result['prompt']}")
    print(f"參考: {result['reference']}")
    print(f"生成: {result['generated']}")
    print(f"\n評估分數:")
    for metric, score in result["scores"].items():
        print(f"  {metric}: {score:.4f}")

    # 評估資料集
    print(f"\n{'=' * 80}")
    print("評估資料集:")
    print(f"{'=' * 80}")

    dataset = [
        {
            "prompt": "什麼是高血壓？",
            "reference": "高血壓是血壓持續高於正常值的疾病。",
        },
        {
            "prompt": "糖尿病如何預防？",
            "reference": "預防糖尿病需要控制體重和健康飲食。",
        },
        {
            "prompt": "運動的好處？",
            "reference": "運動有益於健康，可以增強體質。",
        },
    ]

    summary = evaluator.evaluate_dataset(dataset, batch_size=2)

    print(f"\n評估摘要:")
    print(f"  模型: {summary['model_name']}")
    print(f"  樣本數: {summary['total_samples']}")
    print(f"\n指標:")
    for metric, stats in summary["metrics"].items():
        print(f"  {metric}:")
        print(f"    平均值: {stats['mean']:.4f}")
        print(f"    標準差: {stats['std']:.4f}")

    # 保存結果
    filepath = evaluator.save_results()
    print(f"\n結果已保存: {filepath}")

    # 生成報告
    report = evaluator.generate_report(output_format="markdown")
    print(f"\n{'=' * 80}")
    print("Markdown 報告預覽:")
    print(f"{'=' * 80}")
    print(report[:500] + "...")


# ============================================================================
# 範例 4: 模型比較
# ============================================================================


def example_4_model_comparison():
    """比較多個模型"""
    print("\n" + "=" * 80)
    print("範例 4: 模型比較")
    print("=" * 80)

    # 創建模擬生成器
    class ModelA_Generator:
        def generate(self, prompt: str, **kwargs):
            responses = {
                "什麼是高血壓？": "高血壓是一種血壓持續高於正常值的慢性疾病，需要長期管理。",
                "糖尿病如何預防？": "預防糖尿病需要控制體重、健康飲食、定期運動和定期檢查。",
            }
            return responses.get(prompt, "我不太確定。")

    class ModelB_Generator:
        def generate(self, prompt: str, **kwargs):
            responses = {
                "什麼是高血壓？": "高血壓就是血壓太高的病。",
                "糖尿病如何預防？": "要預防糖尿病就要少吃糖。",
            }
            return responses.get(prompt, "不知道。")

    # 創建比較器
    models = {
        "TAIDE-LX-8B": ModelA_Generator(),
        "Breeze-7B": ModelB_Generator(),
    }

    comparator = ModelComparator(
        models=models,
        metrics=["bleu", "rouge-1", "rouge-2", "f1"],
    )

    print(f"\n比較器已創建，包含 {len(models)} 個模型:")
    for model_name in models.keys():
        print(f"  - {model_name}")

    # 單個提示比較
    print(f"\n{'=' * 80}")
    print("單個提示比較:")
    print(f"{'=' * 80}")

    result = comparator.compare_single_prompt(
        prompt="什麼是高血壓？",
        reference="高血壓是血壓持續高於正常值的疾病，需要長期控制。",
    )

    comparator.display_comparison(result, show_generations=True)

    # 資料集比較
    print(f"\n{'=' * 80}")
    print("資料集比較:")
    print(f"{'=' * 80}")

    dataset = [
        {
            "prompt": "什麼是高血壓？",
            "reference": "高血壓是血壓持續高於正常值的疾病。",
        },
        {
            "prompt": "糖尿病如何預防？",
            "reference": "預防糖尿病需要控制體重、健康飲食和定期運動。",
        },
    ]

    comparison = comparator.compare_on_dataset(dataset)

    print(f"\n比較結果:")
    print(f"  模型: {', '.join(comparison['models'])}")
    print(f"  樣本數: {comparison['total_samples']}")
    print(f"\n指標比較:")

    for metric, scores in comparison["comparison"].items():
        print(f"\n  {metric.upper()}:")
        for model, score in scores.items():
            print(f"    {model}: {score:.4f}")

    print(f"\n排名:")
    for metric, rankings in comparison["rankings"].items():
        print(f"\n  {metric.upper()}:")
        for rank_info in rankings:
            print(
                f"    {rank_info['rank']}. {rank_info['model']}: {rank_info['score']:.4f}"
            )

    # 保存比較結果
    filepath = comparator.save_comparison(comparison)
    print(f"\n比較結果已保存: {filepath}")

    # 生成報告
    report = comparator.generate_comparison_report(
        comparison, output_format="markdown"
    )
    print(f"\n{'=' * 80}")
    print("比較報告預覽:")
    print(f"{'=' * 80}")
    print(report[:500] + "...")


# ============================================================================
# 範例 5: 統計檢驗
# ============================================================================


def example_5_statistical_test():
    """統計顯著性檢驗"""
    print("\n" + "=" * 80)
    print("範例 5: 統計檢驗")
    print("=" * 80)

    # 創建模擬生成器
    class ModelA_Generator:
        def generate(self, prompt: str, **kwargs):
            import random

            responses = [
                "這是詳細的醫療建議，包含多方面的考量和建議。",
                "根據您的情況，建議採取以下措施進行治療。",
                "這是一個複雜的問題，需要綜合考慮多個因素。",
            ]
            return random.choice(responses)

    class ModelB_Generator:
        def generate(self, prompt: str, **kwargs):
            import random

            responses = [
                "簡短回答。",
                "好的。",
                "知道了。",
            ]
            return random.choice(responses)

    # 創建比較器
    models = {"Model-A": ModelA_Generator(), "Model-B": ModelB_Generator()}

    comparator = ModelComparator(models=models)

    # 生成評估資料
    dataset = [
        {"prompt": f"問題 {i}", "reference": "這是詳細的參考答案，包含完整的資訊。"}
        for i in range(20)
    ]

    # 評估資料集
    comparison = comparator.compare_on_dataset(dataset)

    # 統計檢驗
    print(f"\n進行統計檢驗: Model-A vs Model-B")

    try:
        test_result = comparator.statistical_test(
            model_a="Model-A",
            model_b="Model-B",
            metric="bleu",
            alpha=0.05,
        )

        print(f"\n統計檢驗結果:")
        print(f"  指標: {test_result['metric']}")
        print(
            f"\n  {test_result['model_a']['name']}: "
            f"{test_result['model_a']['mean']:.4f} ± {test_result['model_a']['std']:.4f}"
        )
        print(
            f"  {test_result['model_b']['name']}: "
            f"{test_result['model_b']['mean']:.4f} ± {test_result['model_b']['std']:.4f}"
        )
        print(f"\n  t統計量: {test_result['t_statistic']:.4f}")
        print(f"  p值: {test_result['p_value']:.4f}")
        print(
            f"  顯著性 (α=0.05): {'是' if test_result['significant'] else '否'}"
        )
        print(f"  Cohen's d: {test_result['cohens_d']:.4f}")
        print(f"  效應大小: {test_result['effect_size']}")

    except Exception as e:
        print(f"\n統計檢驗需要 scipy 套件: {e}")
        print("請安裝: pip install scipy")


# ============================================================================
# 範例 6: 多樣性評估
# ============================================================================


def example_6_diversity():
    """評估生成文本的多樣性"""
    print("\n" + "=" * 80)
    print("範例 6: 多樣性評估")
    print("=" * 80)

    # 低多樣性文本
    low_diversity_texts = [
        "高血壓是一種疾病。",
        "高血壓是一種疾病。",
        "高血壓是一種疾病。",
    ]

    # 高多樣性文本
    high_diversity_texts = [
        "高血壓需要長期管理和控制。",
        "糖尿病患者應該注意飲食。",
        "定期運動有助於身體健康。",
    ]

    print("\n低多樣性文本:")
    for text in low_diversity_texts:
        print(f"  - {text}")

    low_div_scores = EvaluationMetrics.diversity_score(low_diversity_texts)
    print(f"\n多樣性分數:")
    print(f"  Unique Unigrams: {low_div_scores['unique_unigrams']:.4f}")
    print(f"  Unique Bigrams: {low_div_scores['unique_bigrams']:.4f}")
    print(f"  Unique Trigrams: {low_div_scores['unique_trigrams']:.4f}")

    print(f"\n{'=' * 80}")
    print("\n高多樣性文本:")
    for text in high_diversity_texts:
        print(f"  - {text}")

    high_div_scores = EvaluationMetrics.diversity_score(high_diversity_texts)
    print(f"\n多樣性分數:")
    print(f"  Unique Unigrams: {high_div_scores['unique_unigrams']:.4f}")
    print(f"  Unique Bigrams: {high_div_scores['unique_bigrams']:.4f}")
    print(f"  Unique Trigrams: {high_div_scores['unique_trigrams']:.4f}")

    print(f"\n{'=' * 80}")
    print("說明:")
    print("  - 分數越高表示多樣性越高")
    print("  - Unigrams: 單字級別的多樣性")
    print("  - Bigrams: 雙字級別的多樣性")
    print("  - Trigrams: 三字級別的多樣性")


# ============================================================================
# 主程序
# ============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("模型評估範例")
    print("=" * 80)

    # 運行所有範例
    example_1_basic_metrics()
    example_2_batch_evaluation()
    example_3_model_evaluator()
    example_4_model_comparison()
    example_5_statistical_test()
    example_6_diversity()

    print("\n" + "=" * 80)
    print("範例完成！")
    print("=" * 80)
    print("""
主要功能:

1. 評估指標
   - BLEU: 基於 N-gram 重疊的精確度
   - ROUGE: 召回率導向的評估（ROUGE-1/2/L）
   - F1: 精確率和召回率的調和平均
   - 精確匹配: 完全匹配檢測
   - 編輯距離: Levenshtein 距離

2. 模型評估器
   - 單樣本評估
   - 批次評估
   - 自動保存結果
   - 生成 Markdown/HTML 報告

3. 模型比較器
   - 並排比較多個模型
   - 資料集級別比較
   - 排名和統計
   - 統計顯著性檢驗
   - 比較報告生成

4. 多樣性評估
   - Unigram/Bigram/Trigram 多樣性
   - 適用於評估生成文本的豐富度

使用建議:
    - 開發階段: 使用快速指標（BLEU, F1）
    - 正式評估: 使用完整指標集
    - 模型比較: 結合自動指標和人工評估
    - 統計檢驗: 確保差異具有統計顯著性
    """)
