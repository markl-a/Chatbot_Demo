# 模型評估和比較系統

完整的模型評估工具，支援多種評估指標、自動化評估、模型比較和統計分析。

## 功能特性

### 1. 評估指標

#### BLEU (Bilingual Evaluation Understudy)
- **用途**: 機器翻譯和文本生成
- **範圍**: 0-1，越高越好
- **特點**: 基於 N-gram 精確度

```python
bleu = EvaluationMetrics.bleu_score(reference, candidate)
```

#### ROUGE (Recall-Oriented Understudy for Gisting Evaluation)
- **ROUGE-1**: 單字重疊（Unigram）
- **ROUGE-2**: 雙字重疊（Bigram）
- **ROUGE-L**: 最長公共子序列

```python
rouge_1 = EvaluationMetrics.rouge_score(reference, candidate, "rouge-1")
rouge_2 = EvaluationMetrics.rouge_score(reference, candidate, "rouge-2")
rouge_l = EvaluationMetrics.rouge_score(reference, candidate, "rouge-l")
```

#### Token F1
- **用途**: 字符級別的精確率和召回率
- **特點**: 平衡precision和recall

```python
f1 = EvaluationMetrics.f1_score(reference, candidate)
```

#### 精確匹配 (Exact Match)
- **用途**: QA系統評估
- **範圍**: 0或1

```python
exact = EvaluationMetrics.exact_match(reference, candidate)
```

#### 編輯距離 (Levenshtein Distance)
- **用途**: 文本相似度
- **特點**: 需要的編輯操作次數

```python
distance = EvaluationMetrics.edit_distance(reference, candidate)
```

#### 多樣性分數
- **用途**: 評估生成文本的豐富度
- **指標**: Unique Unigrams/Bigrams/Trigrams

```python
diversity = EvaluationMetrics.diversity_score(texts)
```

### 2. 模型評估器

#### 單樣本評估

```python
from src.medical_chatbot.evaluation import ModelEvaluator

evaluator = ModelEvaluator(
    model_name="TAIDE-LX-8B",
    generator=my_generator,
    metrics=["bleu", "rouge-1", "rouge-2", "f1"],
)

result = evaluator.evaluate_sample(
    prompt="什麼是高血壓？",
    reference="高血壓是血壓持續高於正常值的疾病。",
)

print(result["scores"])
# {'bleu': 0.65, 'rouge-1': 0.72, 'rouge-2': 0.58, 'f1': 0.68}
```

#### 批次評估

```python
dataset = [
    {"prompt": "問題1", "reference": "答案1"},
    {"prompt": "問題2", "reference": "答案2"},
    ...
]

summary = evaluator.evaluate_dataset(
    dataset,
    batch_size=8,
    max_length=512,
)

print(summary["metrics"])
# {
#   'bleu': {'mean': 0.65, 'std': 0.12, 'min': 0.45, 'max': 0.85},
#   'rouge-1': {'mean': 0.72, 'std': 0.10, ...},
#   ...
# }
```

#### 保存和載入結果

```python
# 保存
filepath = evaluator.save_results("taide_lx_8b_results.json")

# 載入
evaluator.load_results(filepath)

# 獲取摘要
summary = evaluator.get_summary()
```

#### 生成報告

```python
# Markdown 報告
markdown_report = evaluator.generate_report(output_format="markdown")

# HTML 報告
html_report = evaluator.generate_report(output_format="html")
```

### 3. 模型比較器

#### 創建比較器

```python
from src.medical_chatbot.evaluation import ModelComparator

models = {
    "TAIDE-LX-8B": taide_generator,
    "Breeze-7B": breeze_generator,
    "Taiwan-LLM-7B": taiwan_llm_generator,
}

comparator = ModelComparator(
    models=models,
    metrics=["bleu", "rouge-1", "rouge-2", "f1"],
)
```

#### 單個提示比較

```python
result = comparator.compare_single_prompt(
    prompt="什麼是高血壓？",
    reference="高血壓是血壓持續高於正常值的疾病。",
)

comparator.display_comparison(result, show_generations=True)
```

輸出：
```
====================================================================================================
模型比較結果
====================================================================================================

提示: 什麼是高血壓？

參考答案: 高血壓是血壓持續高於正常值的疾病。

----------------------------------------------------------------------------------------------------

【TAIDE-LX-8B】

生成: 高血壓是一種血壓持續高於正常值的慢性疾病，需要長期控制。

生成時間: 0.523s

評估分數:
  bleu: 0.7234
  rouge-1: 0.8156
  rouge-2: 0.6543
  f1: 0.7654

----------------------------------------------------------------------------------------------------

【Breeze-7B】

生成: 高血壓是血壓偏高的病。

生成時間: 0.412s

評估分數:
  bleu: 0.4521
  rouge-1: 0.5234
  rouge-2: 0.3421
  f1: 0.5123
```

#### 資料集比較

```python
comparison = comparator.compare_on_dataset(dataset)

print(comparison["rankings"])
# {
#   'bleu': [
#     {'rank': 1, 'model': 'TAIDE-LX-8B', 'score': 0.72},
#     {'rank': 2, 'model': 'Breeze-7B', 'score': 0.65},
#     {'rank': 3, 'model': 'Taiwan-LLM-7B', 'score': 0.58},
#   ],
#   ...
# }
```

#### 統計檢驗

```python
test_result = comparator.statistical_test(
    model_a="TAIDE-LX-8B",
    model_b="Breeze-7B",
    metric="bleu",
    alpha=0.05,
)

print(test_result)
# {
#   'model_a': {'name': 'TAIDE-LX-8B', 'mean': 0.72, 'std': 0.08},
#   'model_b': {'name': 'Breeze-7B', 'mean': 0.65, 'std': 0.10},
#   't_statistic': 3.45,
#   'p_value': 0.001,
#   'significant': True,
#   'cohens_d': 0.78,
#   'effect_size': 'medium'
# }
```

#### 生成比較報告

```python
report = comparator.generate_comparison_report(
    comparison,
    output_format="markdown"
)
```

### 4. 人工評估

#### 收集評分

```python
ratings = evaluator.collect_human_ratings(
    prompts=["問題1", "問題2", "問題3"],
    generated_texts=["答案1", "答案2", "答案3"],
    rating_scale=5,
    aspects=["relevance", "fluency", "accuracy", "helpfulness"],
)
```

#### A/B 測試

```python
ab_results = evaluator.ab_test(
    prompts=prompts,
    generations_a=model_a_outputs,
    generations_b=model_b_outputs,
    labels=["TAIDE", "Breeze"],
)

print(ab_results)
# {
#   'total_samples': 100,
#   'preferences': {
#     'TAIDE': {'count': 65, 'percentage': 65.0},
#     'Breeze': {'count': 30, 'percentage': 30.0},
#     'Tie': {'count': 5, 'percentage': 5.0}
#   },
#   'winner': 'TAIDE'
# }
```

## 使用範例

### 範例 1: 快速評估

```python
from src.medical_chatbot.evaluation import EvaluationMetrics

reference = "高血壓需要長期服藥控制。"
candidate = "高血壓要長期吃藥。"

# 計算多個指標
bleu = EvaluationMetrics.bleu_score(reference, candidate)
rouge_1 = EvaluationMetrics.rouge_score(reference, candidate, "rouge-1")
f1 = EvaluationMetrics.f1_score(reference, candidate)

print(f"BLEU: {bleu:.4f}")
print(f"ROUGE-1 F1: {rouge_1['f1']:.4f}")
print(f"Token F1: {f1:.4f}")
```

### 範例 2: 完整評估流程

```python
from src.medical_chatbot.evaluation import ModelEvaluator

# 1. 創建評估器
evaluator = ModelEvaluator(
    model_name="TAIDE-LX-8B",
    generator=my_generator,
    metrics=["bleu", "rouge-1", "rouge-2", "rouge-l", "f1"],
    save_dir="./evaluation_results",
)

# 2. 準備資料集
dataset = load_test_dataset()  # 自訂函數

# 3. 評估
summary = evaluator.evaluate_dataset(dataset, batch_size=8)

# 4. 保存結果
evaluator.save_results("taide_lx_8b_eval.json")

# 5. 生成報告
report = evaluator.generate_report(output_format="markdown")
with open("report.md", "w") as f:
    f.write(report)
```

### 範例 3: 比較多個模型

```python
from src.medical_chatbot.evaluation import ModelComparator

# 1. 準備模型
models = {
    "TAIDE-LX-8B": taide_generator,
    "Breeze-7B": breeze_generator,
    "Taiwan-LLM-7B": taiwan_llm_generator,
}

# 2. 創建比較器
comparator = ModelComparator(models=models)

# 3. 比較
comparison = comparator.compare_on_dataset(test_dataset)

# 4. 查看排名
for metric, rankings in comparison["rankings"].items():
    print(f"\n{metric}:")
    for rank_info in rankings:
        print(f"  {rank_info['rank']}. {rank_info['model']}: {rank_info['score']:.4f}")

# 5. 統計檢驗
test_result = comparator.statistical_test(
    model_a="TAIDE-LX-8B",
    model_b="Breeze-7B",
    metric="bleu",
)

if test_result["significant"]:
    print(f"\n{test_result['model_a']['name']} 顯著優於 {test_result['model_b']['name']}")
    print(f"p值: {test_result['p_value']:.4f}, 效應大小: {test_result['effect_size']}")

# 6. 保存和報告
comparator.save_comparison(comparison, "model_comparison.json")
report = comparator.generate_comparison_report(comparison)
```

## 評估指標選擇指南

### 不同任務的推薦指標

| 任務類型 | 推薦指標 | 說明 |
|---------|---------|------|
| **文本生成** | BLEU, ROUGE-L, F1 | 考慮流暢性和相關性 |
| **問答系統** | Exact Match, F1, ROUGE-1 | 強調答案準確性 |
| **摘要生成** | ROUGE-1/2/L | 重視內容覆蓋 |
| **對話系統** | BLEU, F1, 多樣性 | 平衡相關性和多樣性 |
| **翻譯** | BLEU, ROUGE | 傳統翻譯指標 |

### 指標組合建議

#### 基礎評估（開發階段）
```python
metrics = ["bleu", "rouge-1", "f1"]
```

#### 完整評估（正式發布）
```python
metrics = ["bleu", "rouge-1", "rouge-2", "rouge-l", "f1", "exact_match"]
```

#### 生成質量評估
```python
metrics = ["bleu", "rouge-1", "f1", "diversity"]
```

## 評估最佳實踐

### 1. 資料集準備

```python
# 確保資料集具有代表性
dataset = [
    {"prompt": "...", "reference": "..."},
    {"prompt": "...", "reference": "..."},
    ...  # 至少 100 個樣本
]

# 分層抽樣（如果有類別）
from sklearn.model_selection import train_test_split

train_data, test_data = train_test_split(
    dataset,
    test_size=0.2,
    stratify=categories,  # 按類別分層
)
```

### 2. 評估流程

```python
# 1. 快速測試（小樣本）
quick_test = dataset[:10]
quick_results = evaluator.evaluate_dataset(quick_test)

# 2. 完整評估
full_results = evaluator.evaluate_dataset(dataset, batch_size=8)

# 3. 保存中間結果
evaluator.save_results(f"checkpoint_{datetime.now()}.json")
```

### 3. 結果分析

```python
# 查看分數分佈
import matplotlib.pyplot as plt
import numpy as np

bleu_scores = [r["scores"]["bleu"] for r in evaluator.results]

plt.hist(bleu_scores, bins=20)
plt.xlabel("BLEU Score")
plt.ylabel("Frequency")
plt.title("BLEU Score Distribution")
plt.show()
```

### 4. 錯誤分析

```python
# 找出低分樣本
low_score_samples = [
    r for r in evaluator.results
    if r["scores"]["bleu"] < 0.3
]

for sample in low_score_samples[:5]:
    print(f"Prompt: {sample['prompt']}")
    print(f"Reference: {sample['reference']}")
    print(f"Generated: {sample['generated']}")
    print(f"BLEU: {sample['scores']['bleu']:.4f}")
    print("-" * 80)
```

## 常見問題

### Q: 如何選擇評估指標？

A: 根據任務類型選擇：
- QA系統：Exact Match + F1
- 文本生成：BLEU + ROUGE + F1
- 摘要：ROUGE-1/2/L
- 對話：BLEU + 多樣性

### Q: 評估分數多高算好？

A: 不同任務的標準不同：
- BLEU > 0.4：一般認為可接受
- BLEU > 0.6：較好
- ROUGE-L > 0.5：一般認為可接受
- F1 > 0.7：較好

### Q: 如何處理多個參考答案？

A: 計算與每個參考答案的分數，取最大值：

```python
references = ["答案1", "答案2", "答案3"]
scores = [
    EvaluationMetrics.bleu_score(ref, candidate)
    for ref in references
]
best_score = max(scores)
```

### Q: 自動指標不準確怎麼辦？

A: 結合人工評估：

```python
# 1. 自動評估篩選
auto_eval_results = evaluator.evaluate_dataset(dataset)

# 2. 選擇代表性樣本進行人工評估
representative_samples = sample_by_score_distribution(auto_eval_results)

# 3. 人工評分
human_ratings = evaluator.collect_human_ratings(
    prompts=[s["prompt"] for s in representative_samples],
    generated_texts=[s["generated"] for s in representative_samples],
)

# 4. 分析相關性
correlation = compute_correlation(auto_eval_results, human_ratings)
```

## 進階用法

### 自訂評估指標

```python
def custom_medical_accuracy(reference: str, candidate: str) -> float:
    """自訂醫療準確性指標"""
    # 檢查關鍵醫療術語
    medical_terms = extract_medical_terms(reference)
    matched_terms = [t for t in medical_terms if t in candidate]

    return len(matched_terms) / len(medical_terms) if medical_terms else 0.0

# 整合到評估器
class CustomEvaluator(ModelEvaluator):
    def evaluate_sample(self, prompt, reference, **kwargs):
        result = super().evaluate_sample(prompt, reference, **kwargs)
        result["scores"]["medical_accuracy"] = custom_medical_accuracy(
            reference,
            result["generated"]
        )
        return result
```

### 多線程評估

```python
from concurrent.futures import ThreadPoolExecutor

def evaluate_batch_parallel(evaluator, dataset, max_workers=4):
    def eval_sample(item):
        return evaluator.evaluate_sample(
            item["prompt"],
            item["reference"]
        )

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(eval_sample, dataset))

    return results
```

## 依賴套件

```bash
# 基礎依賴
pip install numpy loguru tabulate

# 統計檢驗（可選）
pip install scipy

# 視覺化（可選）
pip install matplotlib seaborn
```

## 授權

MIT License
