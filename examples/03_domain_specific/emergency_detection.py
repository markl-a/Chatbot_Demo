#!/usr/bin/env python3
"""
案例 3.3: 緊急狀況檢測與處理示例

這個範例展示如何檢測和處理醫療緊急狀況，包括：
- 緊急關鍵字檢測
- 嚴重程度評估
- 緊急回應生成
- 安全提示

運行方式:
    python examples/03_domain_specific/emergency_detection.py
"""

import re
from typing import List, Dict, Any, Tuple
from enum import Enum
from medical_chatbot.models.model_manager import ModelManager
from medical_chatbot.inference.generator import TextGenerator


class SeverityLevel(Enum):
    """嚴重程度級別"""
    NORMAL = "正常"
    MILD = "輕微"
    MODERATE = "中等"
    SEVERE = "嚴重"
    EMERGENCY = "緊急"


class EmergencyDetector:
    """緊急狀況檢測器"""

    def __init__(self, model_manager: ModelManager):
        """初始化緊急狀況檢測器

        Args:
            model_manager: 模型管理器
        """
        self.model_manager = model_manager
        self.generator = TextGenerator(
            model=model_manager.model,
            tokenizer=model_manager.tokenizer
        )

        # 緊急關鍵字（按嚴重程度分類）
        self.emergency_keywords = {
            SeverityLevel.EMERGENCY: [
                "劇烈胸痛", "無法呼吸", "呼吸困難", "胸口劇痛",
                "意識模糊", "昏迷", "昏厥", "抽搐",
                "嚴重出血", "大量出血", "咳血", "吐血",
                "嚴重燒傷", "自殺", "輕生", "想死",
                "中毒", "過敏休克", "窒息"
            ],
            SeverityLevel.SEVERE: [
                "高燒不退", "持續嘔吐", "嚴重腹痛",
                "劇烈頭痛", "視力突然模糊", "半身麻痺",
                "說話困難", "吞嚥困難", "嚴重頭暈"
            ],
            SeverityLevel.MODERATE: [
                "發燒", "腹痛", "頭痛", "噁心",
                "嘔吐", "腹瀉", "胸悶", "心悸"
            ]
        }

        # 緊急回應模板
        self.emergency_responses = {
            SeverityLevel.EMERGENCY: """
⚠️ 🚨 緊急警告 🚨 ⚠️

您描述的症狀可能代表生命危險的緊急狀況！

請立即採取以下行動：
1. 立即撥打 119 叫救護車
2. 如果可能，請前往最近的急診室
3. 在等待救援時，保持冷靜
4. 如有他人在場，請尋求協助

⚠️ 這不是一般的醫療諮詢可以處理的情況，需要立即專業醫療介入！
""",
            SeverityLevel.SEVERE: """
⚠️ 注意：這可能是嚴重的醫療狀況

建議：
1. 儘快就醫，建議在 24 小時內看診
2. 如果症狀惡化，請立即前往急診
3. 記錄症狀的變化
4. 避免自行服用藥物

請尋求專業醫療人員的評估和診斷。
""",
            SeverityLevel.MODERATE: """
建議：
1. 如症狀持續或惡化，請就醫
2. 注意休息和飲食
3. 觀察症狀變化
4. 必要時可尋求醫療諮詢
"""
        }

    def detect_severity(self, text: str) -> Tuple[SeverityLevel, List[str]]:
        """檢測嚴重程度

        Args:
            text: 文本內容

        Returns:
            (嚴重程度, 匹配的關鍵字列表)
        """
        matched_keywords = []

        # 檢查緊急級別
        for keyword in self.emergency_keywords[SeverityLevel.EMERGENCY]:
            if keyword in text:
                matched_keywords.append(keyword)

        if matched_keywords:
            return SeverityLevel.EMERGENCY, matched_keywords

        # 檢查嚴重級別
        for keyword in self.emergency_keywords[SeverityLevel.SEVERE]:
            if keyword in text:
                matched_keywords.append(keyword)

        if matched_keywords:
            return SeverityLevel.SEVERE, matched_keywords

        # 檢查中等級別
        for keyword in self.emergency_keywords[SeverityLevel.MODERATE]:
            if keyword in text:
                matched_keywords.append(keyword)

        if matched_keywords:
            return SeverityLevel.MODERATE, matched_keywords

        return SeverityLevel.NORMAL, []

    def analyze_emergency(self, question: str) -> Dict[str, Any]:
        """分析緊急狀況

        Args:
            question: 用戶問題

        Returns:
            分析結果字典
        """
        # 檢測嚴重程度
        severity, keywords = self.detect_severity(question)

        result = {
            "question": question,
            "severity": severity.value,
            "severity_level": severity,
            "matched_keywords": keywords,
            "is_emergency": severity in [
                SeverityLevel.EMERGENCY,
                SeverityLevel.SEVERE
            ]
        }

        # 對於緊急或嚴重情況，直接返回預設回應
        if severity in self.emergency_responses:
            result["response"] = self.emergency_responses[severity]
            result["auto_response"] = True
        else:
            # 對於一般情況，使用模型生成回應
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
            result["response"] = response
            result["auto_response"] = False

        return result

    def batch_triage(
        self,
        questions: List[str]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """批量分類

        Args:
            questions: 問題列表

        Returns:
            按嚴重程度分類的結果
        """
        triage_results = {
            "emergency": [],
            "severe": [],
            "moderate": [],
            "normal": []
        }

        for question in questions:
            result = self.analyze_emergency(question)

            if result["severity_level"] == SeverityLevel.EMERGENCY:
                triage_results["emergency"].append(result)
            elif result["severity_level"] == SeverityLevel.SEVERE:
                triage_results["severe"].append(result)
            elif result["severity_level"] == SeverityLevel.MODERATE:
                triage_results["moderate"].append(result)
            else:
                triage_results["normal"].append(result)

        return triage_results


def demo_emergency_detection():
    """示範緊急狀況檢測"""
    print("\n" + "=" * 60)
    print("示範 1: 緊急狀況檢測")
    print("=" * 60)

    model_manager = ModelManager()
    model_manager.load_model()
    detector = EmergencyDetector(model_manager)

    # 測試案例
    test_cases = [
        "我現在胸口劇烈疼痛，無法呼吸！",
        "頭痛了一整天，休息後有好轉",
        "我有自殺的念頭",
        "感冒流鼻水該怎麼辦？"
    ]

    for i, question in enumerate(test_cases, 1):
        print(f"\n{'─' * 60}")
        print(f"案例 {i}")
        print(f"{'─' * 60}")
        print(f"問題: {question}")

        result = detector.analyze_emergency(question)

        print(f"\n嚴重程度: {result['severity']}")

        if result['matched_keywords']:
            print(f"匹配關鍵字: {', '.join(result['matched_keywords'])}")

        if result['is_emergency']:
            print("\n🚨 緊急狀況！")

        print(f"\n回應:\n{result['response']}")


def demo_severity_levels():
    """示範各嚴重程度級別"""
    print("\n" + "=" * 60)
    print("示範 2: 各嚴重程度級別範例")
    print("=" * 60)

    model_manager = ModelManager()
    model_manager.load_model()
    detector = EmergencyDetector(model_manager)

    # 各級別的範例
    examples_by_level = {
        "緊急": [
            "胸口劇痛，冷汗直流，呼吸困難！",
            "突然昏倒，現在意識模糊",
            "大量咳血"
        ],
        "嚴重": [
            "高燒 40 度持續三天不退",
            "劇烈頭痛伴隨視力模糊",
            "持續嘔吐無法進食"
        ],
        "中等": [
            "發燒 38 度，有點咳嗽",
            "肚子痛，輕微腹瀉",
            "頭痛，可能是感冒"
        ],
        "正常": [
            "如何預防感冒？",
            "健康飲食的建議",
            "運動的好處有哪些？"
        ]
    }

    for level, examples in examples_by_level.items():
        print(f"\n{'=' * 60}")
        print(f"{level} 級別")
        print(f"{'=' * 60}")

        for i, question in enumerate(examples, 1):
            print(f"\n範例 {i}: {question}")

            result = detector.analyze_emergency(question)
            print(f"檢測結果: {result['severity']}")

            if result['matched_keywords']:
                print(f"關鍵字: {', '.join(result['matched_keywords'])}")


def demo_batch_triage():
    """示範批量分類"""
    print("\n" + "=" * 60)
    print("示範 3: 批量問題分類")
    print("=" * 60)

    model_manager = ModelManager()
    model_manager.load_model()
    detector = EmergencyDetector(model_manager)

    # 混合的問題列表
    questions = [
        "胸口劇痛，無法呼吸！",
        "如何預防高血壓？",
        "高燒不退已經三天了",
        "輕微頭痛該怎麼辦？",
        "我有輕生的念頭",
        "健康飲食的建議",
        "突然昏厥，意識不清",
        "感冒流鼻水"
    ]

    print(f"\n總共 {len(questions)} 個問題待分類\n")

    # 批量分類
    results = detector.batch_triage(questions)

    # 顯示分類結果
    print("分類結果摘要:")
    print(f"  緊急: {len(results['emergency'])} 個")
    print(f"  嚴重: {len(results['severe'])} 個")
    print(f"  中等: {len(results['moderate'])} 個")
    print(f"  正常: {len(results['normal'])} 個")

    # 詳細顯示緊急案例
    if results['emergency']:
        print(f"\n{'=' * 60}")
        print("🚨 緊急案例（需立即處理）")
        print(f"{'=' * 60}")

        for i, result in enumerate(results['emergency'], 1):
            print(f"\n{i}. {result['question']}")
            print(f"   關鍵字: {', '.join(result['matched_keywords'])}")

    # 詳細顯示嚴重案例
    if results['severe']:
        print(f"\n{'=' * 60}")
        print("⚠️  嚴重案例（需盡快處理）")
        print(f"{'=' * 60}")

        for i, result in enumerate(results['severe'], 1):
            print(f"\n{i}. {result['question']}")
            print(f"   關鍵字: {', '.join(result['matched_keywords'])}")


def demo_custom_keywords():
    """示範自定義關鍵字"""
    print("\n" + "=" * 60)
    print("示範 4: 自定義緊急關鍵字")
    print("=" * 60)

    model_manager = ModelManager()
    model_manager.load_model()
    detector = EmergencyDetector(model_manager)

    # 顯示現有關鍵字
    print("\n當前緊急關鍵字:")
    for level, keywords in detector.emergency_keywords.items():
        print(f"\n{level.value}:")
        print(f"  {', '.join(keywords[:10])}...")  # 只顯示前 10 個

    # 添加自定義關鍵字
    print("\n\n添加自定義關鍵字...")
    detector.emergency_keywords[SeverityLevel.EMERGENCY].extend([
        "心臟驟停",
        "嚴重車禍",
        "溺水"
    ])

    print("✓ 已添加自定義緊急關鍵字")

    # 測試新關鍵字
    test_question = "發生嚴重車禍，有人受傷"

    result = detector.analyze_emergency(test_question)

    print(f"\n測試問題: {test_question}")
    print(f"檢測結果: {result['severity']}")
    print(f"是否緊急: {'是' if result['is_emergency'] else '否'}")


def demo_emergency_response():
    """示範緊急回應生成"""
    print("\n" + "=" * 60)
    print("示範 5: 緊急回應生成")
    print("=" * 60)

    model_manager = ModelManager()
    model_manager.load_model()
    detector = EmergencyDetector(model_manager)

    # 不同嚴重程度的問題
    scenarios = [
        {
            "situation": "胸口劇痛",
            "question": "我現在胸口非常痛，痛到無法站立！"
        },
        {
            "situation": "高燒不退",
            "question": "發燒三天了，溫度一直在 39-40 度"
        },
        {
            "situation": "一般諮詢",
            "question": "我想了解如何預防流感"
        }
    ]

    for i, scenario in enumerate(scenarios, 1):
        print(f"\n{'─' * 60}")
        print(f"情境 {i}: {scenario['situation']}")
        print(f"{'─' * 60}")
        print(f"問題: {scenario['question']}")

        result = detector.analyze_emergency(scenario['question'])

        print(f"\n嚴重程度: {result['severity']}")
        print(f"自動回應: {'是' if result['auto_response'] else '否'}")
        print(f"\n回應:\n{result['response']}")


def main():
    """主函數"""
    print("""
╔══════════════════════════════════════════════════════════╗
║        醫療聊天機器人 - 緊急狀況檢測示例                ║
╚══════════════════════════════════════════════════════════╝
    """)

    print("\n選擇要運行的示範:")
    print("1. 緊急狀況檢測")
    print("2. 各嚴重程度級別")
    print("3. 批量問題分類")
    print("4. 自定義關鍵字")
    print("5. 緊急回應生成")
    print("6. 運行所有示範")

    try:
        choice = input("\n請輸入選項 (1-6): ").strip()

        if choice == "1":
            demo_emergency_detection()
        elif choice == "2":
            demo_severity_levels()
        elif choice == "3":
            demo_batch_triage()
        elif choice == "4":
            demo_custom_keywords()
        elif choice == "5":
            demo_emergency_response()
        elif choice == "6":
            demo_emergency_detection()
            demo_severity_levels()
            demo_batch_triage()
            demo_custom_keywords()
            demo_emergency_response()
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
