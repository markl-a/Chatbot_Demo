#!/usr/bin/env python3
"""
案例 3.2: 呼吸系統疾病處理示例

這個範例專注於呼吸系統相關的醫療諮詢，包括感冒、咳嗽、
氣喘、肺部健康等問題的處理。

運行方式:
    python examples/03_domain_specific/respiratory_system.py
"""

from typing import List, Dict, Any
from medical_chatbot.models.model_manager import ModelManager
from medical_chatbot.inference.generator import TextGenerator


class RespiratoryConsultant:
    """呼吸系統諮詢助手"""

    def __init__(self, model_manager: ModelManager):
        """初始化呼吸系統諮詢助手

        Args:
            model_manager: 模型管理器
        """
        self.model_manager = model_manager
        self.generator = TextGenerator(
            model=model_manager.model,
            tokenizer=model_manager.tokenizer
        )

        self.system_prompt = """你是一位專業的呼吸科醫療人員。
你的專長包括：
- 上呼吸道感染（感冒、流感）
- 慢性呼吸道疾病（氣喘、慢性阻塞性肺病）
- 咳嗽的診斷和治療
- 肺部健康維護

在回答時，請：
1. 區分急性和慢性症狀
2. 提供症狀緩解的建議
3. 強調何時需要就醫
4. 提供預防措施
"""

    def diagnose_symptom(self, symptoms: List[str]) -> Dict[str, Any]:
        """症狀診斷

        Args:
            symptoms: 症狀列表

        Returns:
            診斷結果
        """
        # 將症狀組合成問題
        symptom_text = "、".join(symptoms)
        question = f"我有以下症狀：{symptom_text}。這可能是什麼問題？該如何處理？"

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

        # 嚴重症狀檢查
        severe_symptoms = [
            "無法呼吸", "呼吸困難", "嚴重氣喘",
            "咳血", "胸痛", "高燒不退"
        ]

        is_severe = any(
            severe in symptom_text
            for severe in severe_symptoms
        )

        return {
            "symptoms": symptoms,
            "assessment": response,
            "severity": "嚴重" if is_severe else "輕微至中等",
            "requires_immediate_attention": is_severe
        }


def demo_common_cold():
    """示範感冒諮詢"""
    print("\n" + "=" * 60)
    print("示範 1: 感冒相關諮詢")
    print("=" * 60)

    model_manager = ModelManager()
    model_manager.load_model()
    consultant = RespiratoryConsultant(model_manager)

    # 感冒相關問題
    cold_questions = [
        "我感冒了，流鼻水、打噴嚏，該怎麼辦？",
        "感冒多久會好？需要看醫生嗎？",
        "感冒期間可以運動嗎？",
        "如何預防感冒？"
    ]

    for i, question in enumerate(cold_questions, 1):
        print(f"\n{'─' * 60}")
        print(f"問題 {i}: {question}")
        print(f"{'─' * 60}")

        messages = [
            {
                "role": "system",
                "content": consultant.system_prompt
            },
            {
                "role": "user",
                "content": question
            }
        ]

        response = consultant.generator.generate(messages)
        print(f"\n回答: {response}")


def demo_cough_analysis():
    """示範咳嗽分析"""
    print("\n" + "=" * 60)
    print("示範 2: 咳嗽症狀分析")
    print("=" * 60)

    model_manager = ModelManager()
    model_manager.load_model()
    consultant = RespiratoryConsultant(model_manager)

    # 不同類型的咳嗽
    cough_cases = [
        {
            "description": "乾咳，已經持續一週",
            "duration": "一週"
        },
        {
            "description": "咳嗽有痰，黃綠色",
            "duration": "三天"
        },
        {
            "description": "夜間咳嗽特別嚴重",
            "duration": "兩週"
        },
        {
            "description": "咳嗽伴隨胸痛",
            "duration": "昨天開始"
        }
    ]

    for i, case in enumerate(cough_cases, 1):
        print(f"\n{'─' * 60}")
        print(f"案例 {i}")
        print(f"{'─' * 60}")
        print(f"症狀: {case['description']}")
        print(f"持續時間: {case['duration']}")

        question = f"{case['description']}，持續{case['duration']}了。這是什麼問題？該如何治療？"

        messages = [
            {
                "role": "system",
                "content": consultant.system_prompt
            },
            {
                "role": "user",
                "content": question
            }
        ]

        response = consultant.generator.generate(messages)
        print(f"\n評估: {response}")


def demo_asthma_management():
    """示範氣喘管理"""
    print("\n" + "=" * 60)
    print("示範 3: 氣喘管理諮詢")
    print("=" * 60)

    model_manager = ModelManager()
    model_manager.load_model()
    consultant = RespiratoryConsultant(model_manager)

    # 氣喘相關問題序列
    asthma_questions = [
        "我有氣喘，最近發作比較頻繁",
        "什麼情況會誘發氣喘？",
        "氣喘患者日常生活要注意什麼？",
        "如何預防氣喘發作？",
        "氣喘可以根治嗎？"
    ]

    conversation_history = []

    for i, question in enumerate(asthma_questions, 1):
        print(f"\n{'─' * 60}")
        print(f"問題 {i}: {question}")
        print(f"{'─' * 60}")

        messages = [
            {
                "role": "system",
                "content": consultant.system_prompt
            }
        ]

        # 加入對話歷史
        messages.extend(conversation_history)

        # 加入當前問題
        messages.append({
            "role": "user",
            "content": question
        })

        response = consultant.generator.generate(messages)
        print(f"\n回答: {response}")

        # 更新對話歷史
        conversation_history.append({
            "role": "user",
            "content": question
        })
        conversation_history.append({
            "role": "assistant",
            "content": response
        })


def demo_symptom_diagnosis():
    """示範症狀診斷"""
    print("\n" + "=" * 60)
    print("示範 4: 多症狀診斷")
    print("=" * 60)

    model_manager = ModelManager()
    model_manager.load_model()
    consultant = RespiratoryConsultant(model_manager)

    # 不同的症狀組合
    symptom_combinations = [
        ["咳嗽", "流鼻水", "喉嚨痛"],
        ["發燒", "咳嗽", "全身痠痛"],
        ["呼吸急促", "胸悶", "咳嗽"],
        ["長期咳嗽", "體重下降", "疲倦"]
    ]

    for i, symptoms in enumerate(symptom_combinations, 1):
        print(f"\n{'─' * 60}")
        print(f"案例 {i}")
        print(f"{'─' * 60}")

        result = consultant.diagnose_symptom(symptoms)

        print(f"症狀: {', '.join(result['symptoms'])}")
        print(f"嚴重程度: {result['severity']}")

        if result['requires_immediate_attention']:
            print("⚠️  需要立即就醫！")

        print(f"\n評估: {result['assessment']}")


def demo_prevention_guidance():
    """示範預防指導"""
    print("\n" + "=" * 60)
    print("示範 5: 呼吸系統健康預防")
    print("=" * 60)

    model_manager = ModelManager()
    model_manager.load_model()
    consultant = RespiratoryConsultant(model_manager)

    # 預防相關問題
    prevention_questions = [
        "如何預防呼吸道感染？",
        "空氣污染對肺部有什麼影響？該如何防護？",
        "吸菸對呼吸系統的危害有哪些？",
        "如何增強呼吸系統的抵抗力？",
        "老年人如何保養肺部健康？"
    ]

    for i, question in enumerate(prevention_questions, 1):
        print(f"\n{'─' * 60}")
        print(f"主題 {i}")
        print(f"{'─' * 60}")
        print(f"問題: {question}")

        messages = [
            {
                "role": "system",
                "content": consultant.system_prompt
            },
            {
                "role": "user",
                "content": question
            }
        ]

        response = consultant.generator.generate(messages)
        print(f"\n建議: {response}")


def main():
    """主函數"""
    print("""
╔══════════════════════════════════════════════════════════╗
║        醫療聊天機器人 - 呼吸系統諮詢示例                ║
╚══════════════════════════════════════════════════════════╝
    """)

    print("\n選擇要運行的示範:")
    print("1. 感冒諮詢")
    print("2. 咳嗽分析")
    print("3. 氣喘管理")
    print("4. 症狀診斷")
    print("5. 預防指導")
    print("6. 運行所有示範")

    try:
        choice = input("\n請輸入選項 (1-6): ").strip()

        if choice == "1":
            demo_common_cold()
        elif choice == "2":
            demo_cough_analysis()
        elif choice == "3":
            demo_asthma_management()
        elif choice == "4":
            demo_symptom_diagnosis()
        elif choice == "5":
            demo_prevention_guidance()
        elif choice == "6":
            demo_common_cold()
            demo_cough_analysis()
            demo_asthma_management()
            demo_symptom_diagnosis()
            demo_prevention_guidance()
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
