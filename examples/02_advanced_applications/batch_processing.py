#!/usr/bin/env python3
"""
案例 2.1: 批量問題處理示例

這個範例展示如何高效地批量處理多個醫療問題。
適用於需要處理大量問答對的場景，如數據分析、測試等。

運行方式:
    python examples/02_advanced_applications/batch_processing.py
"""

import json
import csv
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from medical_chatbot.models.model_manager import ModelManager
from medical_chatbot.inference.generator import TextGenerator


class BatchProcessor:
    """批量處理器類"""

    def __init__(self, model_manager: ModelManager):
        """初始化批量處理器

        Args:
            model_manager: 模型管理器實例
        """
        self.model_manager = model_manager
        self.generator = TextGenerator(
            model=model_manager.model,
            tokenizer=model_manager.tokenizer
        )
        self.results = []

    def process_single_question(
        self,
        question: str,
        question_id: int = None
    ) -> Dict[str, Any]:
        """處理單個問題

        Args:
            question: 問題文本
            question_id: 問題 ID

        Returns:
            處理結果字典
        """
        try:
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

            # 記錄開始時間
            start_time = datetime.now()

            # 生成回應
            response = self.generator.generate(messages)

            # 記錄結束時間
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()

            return {
                "id": question_id,
                "question": question,
                "answer": response,
                "status": "success",
                "processing_time": processing_time,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            return {
                "id": question_id,
                "question": question,
                "answer": None,
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    def process_batch(
        self,
        questions: List[str],
        show_progress: bool = True
    ) -> List[Dict[str, Any]]:
        """批量處理問題列表

        Args:
            questions: 問題列表
            show_progress: 是否顯示進度

        Returns:
            結果列表
        """
        results = []
        total = len(questions)

        for i, question in enumerate(questions, 1):
            if show_progress:
                print(f"處理進度: {i}/{total} ({i/total*100:.1f}%)")

            result = self.process_single_question(question, question_id=i)
            results.append(result)

        self.results = results
        return results

    def process_batch_parallel(
        self,
        questions: List[str],
        max_workers: int = 4
    ) -> List[Dict[str, Any]]:
        """並行批量處理問題

        Args:
            questions: 問題列表
            max_workers: 最大工作線程數

        Returns:
            結果列表
        """
        results = []
        total = len(questions)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任務
            future_to_question = {
                executor.submit(
                    self.process_single_question,
                    question,
                    i
                ): question
                for i, question in enumerate(questions, 1)
            }

            # 收集結果
            completed = 0
            for future in as_completed(future_to_question):
                completed += 1
                print(f"完成: {completed}/{total} ({completed/total*100:.1f}%)")

                result = future.result()
                results.append(result)

        # 按 ID 排序結果
        results.sort(key=lambda x: x.get("id", 0))
        self.results = results
        return results

    def save_results_json(self, output_path: str):
        """保存結果為 JSON 格式

        Args:
            output_path: 輸出文件路徑
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)

        print(f"✓ 結果已保存到: {output_path}")

    def save_results_csv(self, output_path: str):
        """保存結果為 CSV 格式

        Args:
            output_path: 輸出文件路徑
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        if not self.results:
            print("⚠️  沒有結果可保存")
            return

        # 定義 CSV 欄位
        fieldnames = [
            "id", "question", "answer",
            "status", "processing_time", "timestamp", "error"
        ]

        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for result in self.results:
                # 處理可能缺失的欄位
                row = {k: result.get(k, "") for k in fieldnames}
                writer.writerow(row)

        print(f"✓ 結果已保存到: {output_path}")

    def generate_report(self) -> Dict[str, Any]:
        """生成處理報告

        Returns:
            報告字典
        """
        if not self.results:
            return {"error": "沒有結果可報告"}

        total = len(self.results)
        success = sum(1 for r in self.results if r["status"] == "success")
        failed = total - success

        # 計算平均處理時間
        processing_times = [
            r["processing_time"]
            for r in self.results
            if "processing_time" in r
        ]
        avg_time = sum(processing_times) / len(processing_times) if processing_times else 0

        report = {
            "總問題數": total,
            "成功": success,
            "失敗": failed,
            "成功率": f"{success/total*100:.2f}%",
            "平均處理時間": f"{avg_time:.2f}秒",
            "總處理時間": f"{sum(processing_times):.2f}秒"
        }

        return report


def load_questions_from_file(file_path: str) -> List[str]:
    """從文件載入問題列表

    Args:
        file_path: 文件路徑 (支持 .txt, .json)

    Returns:
        問題列表
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")

    if file_path.suffix == '.txt':
        # 從文本文件讀取（每行一個問題）
        with open(file_path, 'r', encoding='utf-8') as f:
            questions = [line.strip() for line in f if line.strip()]

    elif file_path.suffix == '.json':
        # 從 JSON 文件讀取
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                questions = data
            elif isinstance(data, dict) and "questions" in data:
                questions = data["questions"]
            else:
                raise ValueError("無效的 JSON 格式")

    else:
        raise ValueError(f"不支持的文件格式: {file_path.suffix}")

    return questions


def demo_basic_batch():
    """示範基本批量處理"""
    print("\n" + "=" * 60)
    print("示範 1: 基本批量處理")
    print("=" * 60)

    # 初始化
    model_manager = ModelManager()
    model_manager.load_model()
    processor = BatchProcessor(model_manager)

    # 測試問題
    questions = [
        "高血壓患者應該注意什麼？",
        "糖尿病如何預防？",
        "如何改善失眠問題？",
        "感冒了該怎麼辦？",
        "頭痛的常見原因有哪些？"
    ]

    # 批量處理
    print(f"\n開始處理 {len(questions)} 個問題...\n")
    results = processor.process_batch(questions)

    # 顯示結果
    print("\n" + "─" * 60)
    print("處理結果:")
    print("─" * 60)

    for result in results:
        print(f"\nQ{result['id']}: {result['question']}")
        print(f"A{result['id']}: {result['answer']}")
        print(f"處理時間: {result.get('processing_time', 'N/A')}秒")

    # 生成報告
    report = processor.generate_report()
    print("\n" + "=" * 60)
    print("處理報告:")
    print("=" * 60)
    for key, value in report.items():
        print(f"{key}: {value}")


def demo_parallel_batch():
    """示範並行批量處理"""
    print("\n" + "=" * 60)
    print("示範 2: 並行批量處理")
    print("=" * 60)

    # 初始化
    model_manager = ModelManager()
    model_manager.load_model()
    processor = BatchProcessor(model_manager)

    # 較大的測試問題集
    questions = [
        "如何預防心血管疾病？",
        "肥胖對健康有什麼影響？",
        "運動對身體有什麼好處？",
        "如何保持良好的飲食習慣？",
        "壓力過大會導致什麼問題？",
        "如何提高免疫力？",
        "老年人應該注意哪些健康問題？",
        "吸煙對健康的危害有哪些？",
        "如何預防骨質疏鬆？",
        "定期體檢的重要性是什麼？"
    ]

    # 並行處理
    print(f"\n開始並行處理 {len(questions)} 個問題...\n")
    results = processor.process_batch_parallel(questions, max_workers=4)

    # 生成報告
    report = processor.generate_report()
    print("\n" + "=" * 60)
    print("處理報告:")
    print("=" * 60)
    for key, value in report.items():
        print(f"{key}: {value}")

    # 保存結果
    processor.save_results_json("output/batch_results.json")
    processor.save_results_csv("output/batch_results.csv")


def demo_file_input():
    """示範從文件讀取並處理"""
    print("\n" + "=" * 60)
    print("示範 3: 從文件讀取並處理")
    print("=" * 60)

    # 創建示例問題文件
    sample_questions = [
        "如何預防流感？",
        "發燒時該怎麼處理？",
        "咳嗽持續多久需要就醫？"
    ]

    # 保存到文件
    questions_file = Path("data/sample_questions.txt")
    questions_file.parent.mkdir(parents=True, exist_ok=True)

    with open(questions_file, 'w', encoding='utf-8') as f:
        for question in sample_questions:
            f.write(question + '\n')

    print(f"✓ 示例問題已保存到: {questions_file}")

    # 從文件讀取
    questions = load_questions_from_file(str(questions_file))
    print(f"✓ 從文件讀取了 {len(questions)} 個問題")

    # 處理
    model_manager = ModelManager()
    model_manager.load_model()
    processor = BatchProcessor(model_manager)

    results = processor.process_batch(questions)

    # 保存結果
    processor.save_results_json("output/file_batch_results.json")


def main():
    """主函數"""
    print("""
╔══════════════════════════════════════════════════════════╗
║        醫療聊天機器人 - 批量處理示例                    ║
╚══════════════════════════════════════════════════════════╝
    """)

    print("\n選擇要運行的示範:")
    print("1. 基本批量處理")
    print("2. 並行批量處理")
    print("3. 從文件讀取並處理")
    print("4. 運行所有示範")

    try:
        choice = input("\n請輸入選項 (1-4): ").strip()

        if choice == "1":
            demo_basic_batch()
        elif choice == "2":
            demo_parallel_batch()
        elif choice == "3":
            demo_file_input()
        elif choice == "4":
            demo_basic_batch()
            demo_parallel_batch()
            demo_file_input()
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
