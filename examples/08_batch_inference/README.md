# 批次推理系統

高效的批次推理工具，支援大規模推理、並行處理和進度追蹤。

## 功能特性

### 1. 批次推理處理器 (BatchProcessor)

自動分批處理，適合順序推理和檢查點保存。

#### 特點
- ✅ 自動分批處理
- ✅ 進度條顯示（tqdm）
- ✅ 自動保存檢查點
- ✅ 錯誤處理和重試
- ✅ 多種格式導出

#### 使用範例

```python
from src.medical_chatbot.batch_inference import BatchProcessor

# 創建處理器
processor = BatchProcessor(
    generator=my_generator,
    batch_size=8,
    save_dir="./batch_results",
    save_interval=100,  # 每 100 個樣本自動保存
)

# 批次推理
results = processor.process(
    inputs=input_list,
    show_progress=True,
    auto_save=True,
    max_length=512,
)

# 獲取統計
stats = processor.get_stats()
print(f"吞吐量: {stats['throughput']:.2f} 樣本/秒")

# 保存結果
processor.save_results("results.json")
```

### 2. 並行推理處理器 (ParallelProcessor)

多線程/多進程並行處理，適合大規模快速推理。

#### 特點
- ✅ 多線程支援（I/O 密集）
- ✅ 多進程支援（CPU 密集）
- ✅ 自動任務分配
- ✅ 結果順序保持
- ✅ 性能分析

#### 使用範例

```python
from src.medical_chatbot.batch_inference import ParallelProcessor

# 創建並行處理器
processor = ParallelProcessor(
    generator=my_generator,
    max_workers=4,
    mode="thread",  # 或 "process"
)

# 並行推理
results = processor.process(
    inputs=input_list,
    show_progress=True,
)

# 性能分析
analysis = processor.analyze_performance()
print(f"平均時間: {analysis['mean_time']:.3f}s")
print(f"加速比: {analysis['speedup']:.2f}x")
```

## 詳細功能

### 批次推理

#### 基本使用

```python
processor = BatchProcessor(
    generator=generator,
    batch_size=8,
)

results = processor.process(
    inputs=["問題1", "問題2", "問題3", ...],
    show_progress=True,
)
```

#### 使用提示模板

```python
# 輸入
questions = ["高血壓", "糖尿病", "心臟病"]

# 提示模板
prompts = [
    "請詳細說明什麼是{input}？",
    "請解釋如何預防{input}？",
    "請說明{input}的症狀有哪些？",
]

# 推理
results = processor.process(
    inputs=questions,
    prompts=prompts,
)
```

#### 自動保存檢查點

```python
processor = BatchProcessor(
    generator=generator,
    batch_size=8,
    save_interval=100,  # 每 100 個樣本保存一次
)

results = processor.process(
    inputs=large_input_list,
    auto_save=True,
)
```

### 並行推理

#### 多線程模式（推薦用於 I/O 密集）

```python
processor = ParallelProcessor(
    generator=generator,
    max_workers=4,
    mode="thread",
)

results = processor.process(inputs=input_list)
```

#### 多進程模式（推薦用於 CPU 密集）

```python
processor = ParallelProcessor(
    generator=generator,
    max_workers=4,
    mode="process",
)

results = processor.process(inputs=input_list)
```

### 錯誤處理

#### 自動捕獲錯誤

```python
# 推理（自動捕獲錯誤）
results = processor.process(inputs=input_list)

# 查看統計
stats = processor.get_stats()
print(f"錯誤率: {stats['error_rate']:.2%}")

# 獲取失敗樣本
failed = processor.get_failed_results()
for error in failed:
    print(f"輸入: {error['input']}")
    print(f"錯誤: {error['error']}")
```

#### 重試失敗樣本

```python
# 初次推理
results = processor.process(inputs=input_list)

# 重試失敗的樣本
retry_results = processor.retry_failed(
    max_retries=3,
    show_progress=True,
)

print(f"重試成功: {len(retry_results)} 個")
```

### 結果管理

#### 過濾結果

```python
# 獲取成功的結果
successful = processor.get_successful_results()

# 獲取失敗的結果
failed = processor.get_failed_results()
```

#### 導出結果

```python
# 純文本格式（僅輸出）
processor.export_outputs("outputs.txt", format="txt")

# JSON 格式
processor.export_outputs("outputs.json", format="json")

# CSV 格式（包含輸入、輸出、生成時間）
processor.export_outputs("outputs.csv", format="csv")

# 完整結果（包含統計和錯誤）
processor.save_results("full_results.json")
```

#### 載入之前的結果

```python
# 載入結果
processor.load_results("previous_results.json")

# 繼續處理
remaining_inputs = get_remaining_inputs()
new_results = processor.process(remaining_inputs)
```

### 統計資訊

#### 基本統計

```python
stats = processor.get_stats()

print(f"總樣本數: {stats['total_inputs']}")
print(f"成功處理: {stats['total_processed']}")
print(f"錯誤數: {stats['total_errors']}")
print(f"錯誤率: {stats['error_rate']:.2%}")
print(f"總耗時: {stats['total_time']:.2f}s")
print(f"平均每樣本: {stats['avg_time_per_sample']:.3f}s")
print(f"吞吐量: {stats['throughput']:.2f} 樣本/秒")
```

#### 性能分析（並行處理器）

```python
analysis = parallel_processor.analyze_performance()

print(f"平均時間: {analysis['mean_time']:.3f}s")
print(f"中位數: {analysis['median_time']:.3f}s")
print(f"標準差: {analysis['std_time']:.3f}s")
print(f"95% 分位: {analysis['percentile_95']:.3f}s")
print(f"加速比: {analysis['speedup']:.2f}x")
```

## 性能優化指南

### 批次大小選擇

| 模型大小 | 推薦批次大小 | 記憶體需求 |
|---------|-------------|-----------|
| 小模型 (< 1B) | 16-32 | 低 |
| 中模型 (1B-7B) | 8-16 | 中 |
| 大模型 (> 7B) | 2-8 | 高 |

```python
# 根據模型大小選擇批次大小
if model_size < 1_000_000_000:  # < 1B
    batch_size = 32
elif model_size < 7_000_000_000:  # < 7B
    batch_size = 8
else:  # > 7B
    batch_size = 4

processor = BatchProcessor(generator=generator, batch_size=batch_size)
```

### 工作數選擇

```python
import os

# 根據 CPU 核心數選擇工作數
cpu_count = os.cpu_count()

# I/O 密集（多線程）
max_workers = cpu_count * 2  # 可以超過核心數

# CPU 密集（多進程）
max_workers = cpu_count  # 等於核心數

processor = ParallelProcessor(
    generator=generator,
    max_workers=max_workers,
    mode="thread",  # 或 "process"
)
```

### 記憶體管理

```python
# 大規模推理時啟用自動保存和清理
processor = BatchProcessor(
    generator=generator,
    batch_size=8,
    save_interval=100,  # 每 100 個樣本保存
)

# 分段處理
chunk_size = 1000
for i in range(0, len(all_inputs), chunk_size):
    chunk = all_inputs[i:i + chunk_size]
    results = processor.process(chunk, auto_save=True)

    # 清理記憶體（如果需要）
    import gc
    gc.collect()
```

## 使用場景

### 1. 資料集生成

```python
# 生成訓練資料
questions = load_questions()

processor = BatchProcessor(generator=generator, batch_size=16)
results = processor.process(
    inputs=questions,
    prompts=["請為以下問題生成詳細答案：{input}"] * len(questions),
)

# 導出為訓練資料
processor.export_outputs("training_data.json", format="json")
```

### 2. 模型評估

```python
# 大規模評估
test_dataset = load_test_dataset()
inputs = [item["prompt"] for item in test_dataset]

processor = ParallelProcessor(generator=generator, max_workers=4)
results = processor.process(inputs=inputs)

# 計算評估指標
from src.medical_chatbot.evaluation import EvaluationMetrics

scores = []
for result, test_item in zip(results, test_dataset):
    if result["status"] == "success":
        score = EvaluationMetrics.bleu_score(
            test_item["reference"],
            result["output"]
        )
        scores.append(score)

print(f"平均 BLEU: {sum(scores) / len(scores):.4f}")
```

### 3. 生產環境推理

```python
# 處理用戶請求隊列
from queue import Queue

request_queue = Queue()

def process_requests():
    while True:
        # 收集一批請求
        batch = []
        for _ in range(batch_size):
            if not request_queue.empty():
                batch.append(request_queue.get())

        if batch:
            # 批次處理
            inputs = [req["prompt"] for req in batch]
            results = processor.process(inputs, show_progress=False)

            # 返回結果給用戶
            for req, result in zip(batch, results):
                send_response(req["user_id"], result["output"])
```

### 4. 資料擴增

```python
# 為每個輸入生成多個變體
inputs = ["原始問題1", "原始問題2", ...]

# 生成變體提示
prompts = []
for input_text in inputs:
    for variation in ["正式", "非正式", "簡短", "詳細"]:
        prompts.append(f"請用{variation}的方式重寫：{input_text}")

processor = BatchProcessor(generator=generator, batch_size=16)
results = processor.process(prompts)
```

## 性能比較

### 批次 vs 並行

| 方法 | 吞吐量 | 記憶體 | 適用場景 |
|-----|-------|--------|---------|
| **順序** | 1x | 低 | 小規模、調試 |
| **批次** | 2-4x | 中 | 中等規模、GPU 推理 |
| **並行（線程）** | 3-6x | 中 | I/O 密集、API 調用 |
| **並行（進程）** | 4-8x | 高 | CPU 密集、多 GPU |

### 實際測試結果

```
測試條件: 100 個樣本，模型生成時間 0.1s/樣本

順序處理:    10.0s  (10 樣本/秒)
批次處理(8): 3.5s   (28 樣本/秒) - 2.8x 加速
並行(4線程): 2.8s   (35 樣本/秒) - 3.5x 加速
並行(8線程): 1.8s   (55 樣本/秒) - 5.5x 加速
```

## 故障排除

### Q: 記憶體不足怎麼辦？

A: 減小批次大小或啟用檢查點保存：

```python
processor = BatchProcessor(
    generator=generator,
    batch_size=4,  # 減小批次
    save_interval=50,  # 頻繁保存
)
```

### Q: 如何處理長時間運行的任務？

A: 啟用自動保存和檢查點：

```python
# 啟用自動保存
results = processor.process(
    inputs=large_input_list,
    auto_save=True,  # 自動保存
)

# 如果中斷，可以從檢查點恢復
processor.load_results("checkpoint_*.json")
# 繼續處理剩餘樣本
```

### Q: 並行處理時如何保持順序？

A: ParallelProcessor 會自動保持原始順序：

```python
# 結果會按照輸入順序排列
results = parallel_processor.process(inputs)

# 驗證順序
for inp, res in zip(inputs, results):
    assert inp == res["input"]
```

### Q: 如何選擇線程 vs 進程？

A:
- **線程 (thread)**: 推薦用於 I/O 密集（API 調用、網路請求）
- **進程 (process)**: 推薦用於 CPU 密集（本地模型推理）

```python
# I/O 密集
processor = ParallelProcessor(mode="thread", max_workers=8)

# CPU 密集
processor = ParallelProcessor(mode="process", max_workers=4)
```

## 依賴套件

```bash
pip install tqdm numpy
```

## 授權

MIT License
