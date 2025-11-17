#!/usr/bin/env python3
"""
案例 3.1: 心血管疾病諮詢示例

這個範例專注於心血管相關的醫療諮詢，展示如何處理特定領域的問題。
包括高血壓、心臟病、膽固醇等相關諮詢。

運行方式:
    python examples/03_domain_specific/cardiovascular_consultation.py
"""

from typing import List, Dict, Any
from medical_chatbot.models.model_manager import ModelManager
from medical_chatbot.inference.generator import TextGenerator


# 心血管相關的問題庫
CARDIOVASCULAR_QUESTIONS = {
    "高血壓": [
        "我有高血壓，血壓經常在 150/95 左右，該怎麼辦？",
        "高血壓患者在飲食上應該注意什麼？",
        "高血壓可以不吃藥嗎？有什麼自然降壓的方法？",
        "高血壓患者可以運動嗎？適合什麼運動？",
        "高血壓藥物需要終身服用嗎？"
    ],
    "心臟病": [
        "經常感覺心悸，是心臟有問題嗎？",
        "胸悶胸痛是心臟病的徵兆嗎？",
        "心臟病患者日常生活需要注意什麼？",
        "如何預防心臟病發作？",
        "心臟病家族史的人應該如何預防？"
    ],
    "膽固醇": [
        "膽固醇過高有什麼危害？",
        "如何降低膽固醇？",
        "膽固醇高的人飲食上應該怎麼吃？",
        "好膽固醇和壞膽固醇有什麼區別？",
        "吃藥降膽固醇有副作用嗎？"
    ],
    "心血管保健": [
        "如何保養心血管健康？",
        "什麼食物對心血管有益？",
        "心血管疾病的預警信號有哪些？",
        "年紀大了如何預防心血管疾病？",
        "壓力對心血管健康有什麼影響？"
    ]
}


class CardiovascularConsultant:
    """心血管諮詢助手"""

    def __init__(self, model_manager: ModelManager):
        """初始化心血管諮詢助手

        Args:
            model_manager: 模型管理器
        """
        self.model_manager = model_manager
        self.generator = TextGenerator(
            model=model_manager.model,
            tokenizer=model_manager.tokenizer
        )

        # 心血管專業系統提示詞
        self.system_prompt = """你是一位專業的心血管科醫療人員。
你的專長包括：
- 高血壓的診斷和管理
- 心臟疾病的預防和治療
- 膽固醇管理
- 心血管健康促進

在回答時，請：
1. 提供專業且準確的醫療建議
2. 強調定期檢查和專業診斷的重要性
3. 提供生活方式改善建議
4. 對於嚴重症狀，建議立即就醫
"""

    def consult(self, question: str) -> Dict[str, Any]:
        """進行諮詢

        Args:
            question: 問題

        Returns:
            諮詢結果字典
        """
        messages = [
            {
                "role": "system",
                "content": self.system_prompt
            },
            {
                "role": "user",
                "content": question
            }
        ]

        response = self.generator.generate(messages)

        # 檢測是否為緊急狀況
        emergency_keywords = [
            "劇烈胸痛", "胸口劇痛", "無法呼吸",
            "呼吸困難", "昏厥", "意識模糊",
            "嚴重頭暈", "冷汗", "臉色蒼白"
        ]

        is_emergency = any(keyword in question for keyword in emergency_keywords)

        result = {
            "question": question,
            "answer": response,
            "is_emergency": is_emergency
        }

        if is_emergency:
            result["emergency_note"] = (
                "⚠️ 這可能是緊急情況！請立即撥打 119 或前往最近的急診室。"
            )

        return result

    def multi_turn_consult(
        self,
        questions: List[str],
        maintain_context: bool = True
    ) -> List[Dict[str, Any]]:
        """多輪諮詢

        Args:
            questions: 問題列表
            maintain_context: 是否維持上下文

        Returns:
            諮詢結果列表
        """
        results = []
        conversation_history = []

        for question in questions:
            if maintain_context:
                # 建立訊息列表
                messages = [
                    {
                        "role": "system",
                        "content": self.system_prompt
                    }
                ]

                # 加入對話歷史
                messages.extend(conversation_history)

                # 加入當前問題
                messages.append({
                    "role": "user",
                    "content": question
                })

            else:
                # 單獨諮詢
                messages = [
                    {
                        "role": "system",
                        "content": self.system_prompt
                    },
                    {
                        "role": "user",
                        "content": question
                    }
                ]

            # 生成回應
            response = self.generator.generate(messages)

            # 更新對話歷史
            if maintain_context:
                conversation_history.append({
                    "role": "user",
                    "content": question
                })
                conversation_history.append({
                    "role": "assistant",
                    "content": response
                })

            results.append({
                "question": question,
                "answer": response
            })

        return results


def demo_single_consultation():
    """示範單次諮詢"""
    print("\n" + "=" * 60)
    print("示範 1: 單次心血管諮詢")
    print("=" * 60)

    # 初始化
    model_manager = ModelManager()
    model_manager.load_model()
    consultant = CardiovascularConsultant(model_manager)

    # 測試問題
    question = "我有高血壓，血壓經常在 150/95 左右，該怎麼辦？"

    print(f"\n問題: {question}")

    result = consultant.consult(question)

    print(f"\n回答: {result['answer']}")

    if result['is_emergency']:
        print(f"\n{result['emergency_note']}")


def demo_category_questions():
    """示範各類心血管問題"""
    print("\n" + "=" * 60)
    print("示範 2: 各類心血管問題諮詢")
    print("=" * 60)

    # 初始化
    model_manager = ModelManager()
    model_manager.load_model()
    consultant = CardiovascularConsultant(model_manager)

    # 從每個類別選一個問題
    for category, questions in CARDIOVASCULAR_QUESTIONS.items():
        print(f"\n{'─' * 60}")
        print(f"類別: {category}")
        print(f"{'─' * 60}")

        # 取第一個問題
        question = questions[0]
        print(f"\n問題: {question}")

        result = consultant.consult(question)
        print(f"\n回答: {result['answer']}")


def demo_progressive_consultation():
    """示範漸進式諮詢（多輪對話）"""
    print("\n" + "=" * 60)
    print("示範 3: 漸進式心血管諮詢")
    print("=" * 60)

    # 初始化
    model_manager = ModelManager()
    model_manager.load_model()
    consultant = CardiovascularConsultant(model_manager)

    # 模擬一個病人的連續問題
    questions = [
        "我最近量血壓都很高，大概 160/100 左右",
        "我今年 55 歲，有家族高血壓史",
        "目前沒有在吃任何藥物",
        "飲食上我該注意什麼？",
        "運動方面有什麼建議嗎？"
    ]

    print("\n開始漸進式諮詢（維持上下文）...\n")

    results = consultant.multi_turn_consult(questions, maintain_context=True)

    for i, result in enumerate(results, 1):
        print(f"\n{'─' * 60}")
        print(f"第 {i} 輪")
        print(f"{'─' * 60}")
        print(f"問題: {result['question']}")
        print(f"回答: {result['answer']}")


def demo_emergency_detection():
    """示範緊急狀況檢測"""
    print("\n" + "=" * 60)
    print("示範 4: 緊急狀況檢測")
    print("=" * 60)

    # 初始化
    model_manager = ModelManager()
    model_manager.load_model()
    consultant = CardiovascularConsultant(model_manager)

    # 測試問題（包含緊急和非緊急）
    test_cases = [
        {
            "question": "我感覺胸口有點悶，是不是要注意？",
            "expected_emergency": False
        },
        {
            "question": "我現在胸口劇烈疼痛，冷汗直流，呼吸困難！",
            "expected_emergency": True
        },
        {
            "question": "高血壓患者平時該注意什麼？",
            "expected_emergency": False
        },
        {
            "question": "突然感到暈眩，意識有點模糊，胸口很痛！",
            "expected_emergency": True
        }
    ]

    for i, case in enumerate(test_cases, 1):
        print(f"\n{'─' * 60}")
        print(f"測試 {i}")
        print(f"{'─' * 60}")
        print(f"問題: {case['question']}")

        result = consultant.consult(case['question'])

        print(f"檢測結果: {'🚨 緊急' if result['is_emergency'] else '✓ 正常'}")

        if result['is_emergency']:
            print(f"⚠️  {result['emergency_note']}")

        print(f"回答: {result['answer'][:150]}...")


def demo_comprehensive_assessment():
    """示範綜合評估"""
    print("\n" + "=" * 60)
    print("示範 5: 心血管健康綜合評估")
    print("=" * 60)

    # 初始化
    model_manager = ModelManager()
    model_manager.load_model()
    consultant = CardiovascularConsultant(model_manager)

    # 綜合評估問題
    assessment_questions = [
        "我想了解我的心血管健康狀況，我的情況是：年齡 50 歲，有輕微高血壓",
        "家族中父親有心臟病史",
        "我平時不太運動，工作壓力較大",
        "飲食習慣不太健康，經常外食",
        "請給我一個綜合的健康建議"
    ]

    print("\n進行綜合評估...\n")

    results = consultant.multi_turn_consult(
        assessment_questions,
        maintain_context=True
    )

    for i, result in enumerate(results, 1):
        print(f"\n{'─' * 60}")
        print(f"評估項目 {i}")
        print(f"{'─' * 60}")
        print(f"Q: {result['question']}")
        print(f"A: {result['answer']}")

    print("\n" + "=" * 60)
    print("綜合評估完成")
    print("=" * 60)


def main():
    """主函數"""
    print("""
╔══════════════════════════════════════════════════════════╗
║        醫療聊天機器人 - 心血管諮詢示例                  ║
╚══════════════════════════════════════════════════════════╝
    """)

    print("\n選擇要運行的示範:")
    print("1. 單次諮詢")
    print("2. 各類問題諮詢")
    print("3. 漸進式諮詢")
    print("4. 緊急狀況檢測")
    print("5. 綜合健康評估")
    print("6. 運行所有示範")

    try:
        choice = input("\n請輸入選項 (1-6): ").strip()

        if choice == "1":
            demo_single_consultation()
        elif choice == "2":
            demo_category_questions()
        elif choice == "3":
            demo_progressive_consultation()
        elif choice == "4":
            demo_emergency_detection()
        elif choice == "5":
            demo_comprehensive_assessment()
        elif choice == "6":
            demo_single_consultation()
            demo_category_questions()
            demo_progressive_consultation()
            demo_emergency_detection()
            demo_comprehensive_assessment()
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
