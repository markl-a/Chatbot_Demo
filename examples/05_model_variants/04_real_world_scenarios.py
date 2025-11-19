"""
範例：實際應用場景

展示在真實醫療場景中如何使用 RAG 和多模型系統。
"""
from pathlib import Path
import sys
import json
from datetime import datetime
from typing import List, Dict, Any

# 添加專案路徑
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from medical_chatbot.rag import MedicalEmbedder, MedicalRetriever
from medical_chatbot.utils.safety import SafetyFilter
from medical_chatbot.utils.logger import setup_logger

logger = setup_logger()


def scenario_1_virtual_clinic():
    """場景 1: 虛擬診所助手"""
    print("\n" + "=" * 60)
    print("場景 1: 虛擬診所 24/7 線上諮詢助手")
    print("=" * 60)

    class VirtualClinicAssistant:
        """虛擬診所助手"""

        def __init__(self):
            self.embedder = MedicalEmbedder()
            self.retriever = MedicalRetriever(embedder=self.embedder, top_k=3)
            self.safety_filter = SafetyFilter()
            self.consultation_history = []

        def load_clinical_guidelines(self):
            """載入臨床指南"""
            guidelines = [
                """
                高血壓診療指南：
                - 診斷標準：收縮壓 ≥ 140 mmHg 或舒張壓 ≥ 90 mmHg
                - 分級：1級(140-159/90-99)，2級(160-179/100-109)，3級(≥180/110)
                - 生活方式干預：減鹽、運動、減重、限酒、戒菸
                - 藥物治療：根據分級和併發症選擇
                """,
                """
                糖尿病管理指南：
                - 診斷：空腹血糖 ≥ 126 mg/dL 或 HbA1c ≥ 6.5%
                - 目標：HbA1c < 7%（個體化調整）
                - 飲食：碳水化合物控制、定時定量
                - 運動：每週至少 150 分鐘中等強度運動
                - 監測：血糖、血壓、血脂、腎功能
                """,
                """
                感冒和流感鑑別：
                - 感冒：逐漸發作、鼻塞流涕、咳嗽、輕度發燒
                - 流感：突然發作、高燒、全身痠痛、嚴重疲勞
                - 治療：症狀緩解、休息、多喝水
                - 就醫指標：高燒持續 > 3天、呼吸困難、胸痛
                """,
                """
                緊急就醫指標：
                - 胸痛或胸悶超過 5 分鐘
                - 呼吸困難或喘不過氣
                - 突發性劇烈頭痛
                - 意識改變或暈倒
                - 嚴重創傷或大量出血
                - 懷疑中風症狀（FAST）
                立即撥打 119 或前往急診
                """,
            ]

            self.retriever.add_documents(guidelines)
            logger.info(f"已載入 {len(guidelines)} 份臨床指南")

        def consult(self, patient_query: str) -> Dict[str, Any]:
            """諮詢處理"""
            consultation = {
                "timestamp": datetime.now().isoformat(),
                "query": patient_query,
                "is_emergency": False,
                "response": None,
                "references": [],
                "recommendation": None,
            }

            # 安全檢查
            is_emergency = self.safety_filter.is_emergency(patient_query)
            consultation["is_emergency"] = is_emergency

            if is_emergency:
                consultation["response"] = (
                    "⚠️ 緊急警告：您描述的症狀可能需要立即醫療處理。\n"
                    "請立即撥打 119 或前往最近的急診室。\n"
                    "在等待期間，請保持冷靜，不要移動（如有創傷）。"
                )
                consultation["recommendation"] = "立即就醫"
                return consultation

            # RAG 檢索相關指南
            results = self.retriever.retrieve(patient_query, top_k=2)

            if results:
                # 組合回應
                response_parts = [
                    "根據臨床指南，以下是相關資訊：\n",
                ]

                for i, result in enumerate(results, 1):
                    response_parts.append(f"\n參考 {i}:\n{result['text'].strip()}")
                    consultation["references"].append(
                        {
                            "text": result["text"].strip(),
                            "relevance": result["score"],
                        }
                    )

                response_parts.append(
                    "\n\n⚠️ 免責聲明：以上資訊僅供參考，不能替代專業醫療建議。"
                    "如症狀持續或加重，請諮詢醫療專業人員。"
                )

                consultation["response"] = "\n".join(response_parts)
                consultation["recommendation"] = "諮詢醫生以獲取個人化建議"
            else:
                consultation["response"] = (
                    "抱歉，我無法在知識庫中找到相關資訊。\n"
                    "建議您諮詢醫療專業人員以獲取準確的醫療建議。"
                )
                consultation["recommendation"] = "諮詢醫生"

            # 記錄諮詢歷史
            self.consultation_history.append(consultation)

            return consultation

    # 創建虛擬診所助手
    assistant = VirtualClinicAssistant()
    assistant.load_clinical_guidelines()

    # 模擬病患諮詢
    patient_queries = [
        "我最近測量血壓是 150/95，這樣正常嗎？",
        "糖尿病患者應該如何控制飲食？",
        "我突然胸口很痛，呼吸困難",
    ]

    print("\n虛擬診所諮詢記錄：\n")

    for i, query in enumerate(patient_queries, 1):
        print(f"諮詢 {i}:")
        print(f"患者: {query}")

        consultation = assistant.consult(query)

        if consultation["is_emergency"]:
            print(f"⚠️ 緊急情況！")

        print(f"助手: {consultation['response'][:200]}...")
        print(f"建議: {consultation['recommendation']}")
        print()

    print(f"總諮詢次數: {len(assistant.consultation_history)}")
    print("✓ 虛擬診所場景完成")


def scenario_2_health_education():
    """場景 2: 健康教育平台"""
    print("\n" + "=" * 60)
    print("場景 2: 個人化健康教育平台")
    print("=" * 60)

    class HealthEducationPlatform:
        """健康教育平台"""

        def __init__(self):
            self.embedder = MedicalEmbedder()
            self.retriever = MedicalRetriever(embedder=self.embedder)
            self.user_profiles = {}

        def load_educational_content(self):
            """載入教育內容"""
            content = {
                "heart_health": [
                    "心臟健康：定期有氧運動可以強化心臟功能，建議每週 150 分鐘。",
                    "心臟病預防：控制血壓、血糖、血脂，保持健康體重。",
                    "心臟健康飲食：增加魚類、堅果、全穀物，減少飽和脂肪。",
                ],
                "diabetes_prevention": [
                    "糖尿病預防：維持健康體重，BMI 保持在 18.5-24 之間。",
                    "糖尿病風險因子：家族史、肥胖、缺乏運動、不良飲食習慣。",
                    "糖尿病篩檢：40歲以上、有風險因子者建議每年檢查。",
                ],
                "nutrition": [
                    "均衡飲食：每天攝取 5 份蔬果，多樣化食物來源。",
                    "健康蛋白質：優選魚類、豆類、瘦肉，限制紅肉攝取。",
                    "水分補充：每天至少 8 杯水（約 2000ml）。",
                ],
            }

            all_docs = []
            metadata = []

            for category, docs in content.items():
                all_docs.extend(docs)
                metadata.extend(
                    [{"category": category, "type": "education"} for _ in docs]
                )

            self.retriever.add_documents(all_docs, metadata=metadata)
            logger.info(f"已載入 {len(all_docs)} 份教育內容")

        def create_user_profile(self, user_id: str, interests: List[str]):
            """創建用戶檔案"""
            self.user_profiles[user_id] = {
                "id": user_id,
                "interests": interests,
                "learning_history": [],
            }

        def personalized_recommendation(
            self, user_id: str, query: str = None
        ) -> List[Dict]:
            """個人化推薦"""
            if user_id not in self.user_profiles:
                return []

            profile = self.user_profiles[user_id]

            # 基於興趣生成查詢
            if not query:
                query = " ".join(profile["interests"])

            # 檢索相關內容
            results = self.retriever.retrieve(query, top_k=5)

            # 過濾已學習的內容
            learned_texts = {
                item["text"] for item in profile.get("learning_history", [])
            }

            recommendations = [
                {
                    "content": result["text"],
                    "category": result["metadata"].get("category", "general"),
                    "relevance": result["score"],
                }
                for result in results
                if result["text"] not in learned_texts
            ]

            return recommendations

    # 創建教育平台
    platform = HealthEducationPlatform()
    platform.load_educational_content()

    # 創建用戶檔案
    platform.create_user_profile(
        user_id="user001", interests=["心臟健康", "運動", "飲食"]
    )

    platform.create_user_profile(
        user_id="user002", interests=["糖尿病預防", "減重"]
    )

    # 個人化推薦
    print("\n個人化健康教育推薦：\n")

    for user_id in ["user001", "user002"]:
        print(f"用戶 {user_id}:")
        profile = platform.user_profiles[user_id]
        print(f"  興趣: {', '.join(profile['interests'])}")

        recommendations = platform.personalized_recommendation(user_id)

        print(f"  推薦內容 ({len(recommendations)} 則):")
        for i, rec in enumerate(recommendations[:3], 1):
            print(f"    {i}. [{rec['category']}] {rec['content'][:60]}...")
        print()

    print("✓ 健康教育平台場景完成")


def scenario_3_medication_assistant():
    """場景 3: 用藥助手"""
    print("\n" + "=" * 60)
    print("場景 3: 智能用藥助手")
    print("=" * 60)

    class MedicationAssistant:
        """用藥助手"""

        def __init__(self):
            self.embedder = MedicalEmbedder()
            self.retriever = MedicalRetriever(embedder=self.embedder)

        def load_medication_database(self):
            """載入藥物資料庫"""
            medications = [
                {
                    "name": "阿斯匹靈 (Aspirin)",
                    "indication": "解熱、鎮痛、抗發炎、心血管疾病預防",
                    "dosage": "成人：每次 325-650mg，每 4-6 小時一次",
                    "precautions": "不可與酒精併用，胃潰瘍患者慎用",
                },
                {
                    "name": "降血壓藥 (ACE inhibitors)",
                    "indication": "高血壓、心衰竭",
                    "dosage": "依醫囑，通常每日一次",
                    "precautions": "可能引起乾咳，定期監測腎功能和血鉀",
                },
                {
                    "name": "降血糖藥 (Metformin)",
                    "indication": "第二型糖尿病",
                    "dosage": "起始劑量 500mg，每日 1-2 次，隨餐服用",
                    "precautions": "可能引起腸胃不適，腎功能不全者慎用",
                },
            ]

            docs = []
            metadata = []

            for med in medications:
                doc = (
                    f"藥物名稱：{med['name']}\n"
                    f"適應症：{med['indication']}\n"
                    f"用法用量：{med['dosage']}\n"
                    f"注意事項：{med['precautions']}"
                )
                docs.append(doc)
                metadata.append({"drug_name": med["name"], "type": "medication"})

            self.retriever.add_documents(docs, metadata=metadata)
            logger.info(f"已載入 {len(medications)} 種藥物資訊")

        def query_medication(self, query: str) -> Dict[str, Any]:
            """查詢藥物資訊"""
            results = self.retriever.retrieve(query, top_k=2)

            response = {"query": query, "medications": [], "warnings": []}

            if results:
                for result in results:
                    response["medications"].append(
                        {
                            "info": result["text"],
                            "drug_name": result["metadata"].get("drug_name", "未知"),
                            "relevance": result["score"],
                        }
                    )

                # 添加通用警告
                response["warnings"] = [
                    "請依照醫師或藥師指示用藥",
                    "不可自行調整劑量或停藥",
                    "如有不適，請立即諮詢醫療人員",
                ]
            else:
                response["medications"] = []
                response["warnings"] = ["未找到相關藥物資訊，請諮詢藥師或醫師"]

            return response

    # 創建用藥助手
    assistant = MedicationAssistant()
    assistant.load_medication_database()

    # 測試查詢
    queries = [
        "我有高血壓，需要吃什麼藥？",
        "糖尿病用什麼藥？",
        "阿斯匹靈怎麼吃？",
    ]

    print("\n用藥諮詢：\n")

    for query in queries:
        print(f"問題: {query}")
        response = assistant.query_medication(query)

        if response["medications"]:
            print(f"相關藥物 ({len(response['medications'])} 種):")
            for med in response["medications"]:
                print(f"\n  {med['drug_name']} (相關度: {med['relevance']:.2f})")
                print(f"  {med['info'][:150]}...")

        print(f"\n⚠️ 注意事項:")
        for warning in response["warnings"]:
            print(f"  - {warning}")
        print()

    print("✓ 用藥助手場景完成")


def scenario_4_symptom_checker():
    """場景 4: 症狀檢查器"""
    print("\n" + "=" * 60)
    print("場景 4: AI 症狀檢查器")
    print("=" * 60)

    class SymptomChecker:
        """症狀檢查器"""

        def __init__(self):
            self.embedder = MedicalEmbedder()
            self.retriever = MedicalRetriever(embedder=self.embedder)
            self.safety_filter = SafetyFilter()

        def load_symptom_database(self):
            """載入症狀資料庫"""
            symptoms_db = [
                {
                    "symptoms": ["發燒", "咳嗽", "流鼻涕", "喉嚨痛"],
                    "condition": "普通感冒",
                    "severity": "輕度",
                    "action": "多休息、多喝水、症狀治療",
                },
                {
                    "symptoms": ["高燒", "全身痠痛", "嚴重疲勞", "頭痛"],
                    "condition": "流感",
                    "severity": "中度",
                    "action": "就醫檢查、可能需要抗病毒藥物",
                },
                {
                    "symptoms": ["胸痛", "呼吸困難", "心悸", "冒冷汗"],
                    "condition": "可能心臟問題",
                    "severity": "緊急",
                    "action": "立即就醫，撥打 119",
                },
                {
                    "symptoms": ["多尿", "多飲", "多食", "體重減輕"],
                    "condition": "可能糖尿病",
                    "severity": "中度",
                    "action": "儘速就醫檢查血糖",
                },
            ]

            docs = []
            metadata = []

            for item in symptoms_db:
                doc = (
                    f"症狀：{', '.join(item['symptoms'])}\n"
                    f"可能病症：{item['condition']}\n"
                    f"嚴重程度：{item['severity']}\n"
                    f"建議行動：{item['action']}"
                )
                docs.append(doc)
                metadata.append(
                    {"condition": item["condition"], "severity": item["severity"]}
                )

            self.retriever.add_documents(docs, metadata=metadata)
            logger.info(f"已載入 {len(symptoms_db)} 種症狀組合")

        def check_symptoms(self, symptoms_description: str) -> Dict[str, Any]:
            """檢查症狀"""
            result = {
                "input": symptoms_description,
                "is_emergency": False,
                "possible_conditions": [],
                "recommendation": None,
            }

            # 緊急檢查
            is_emergency = self.safety_filter.is_emergency(symptoms_description)
            result["is_emergency"] = is_emergency

            if is_emergency:
                result["recommendation"] = "⚠️ 緊急！立即就醫或撥打 119"
                return result

            # 檢索相似症狀
            matches = self.retriever.retrieve(symptoms_description, top_k=3)

            if matches:
                for match in matches:
                    condition_info = {
                        "description": match["text"],
                        "condition": match["metadata"].get("condition", "未知"),
                        "severity": match["metadata"].get("severity", "未知"),
                        "confidence": match["score"],
                    }
                    result["possible_conditions"].append(condition_info)

                # 根據嚴重程度給建議
                max_severity = max(
                    matches, key=lambda x: x["metadata"].get("severity", "")
                )

                if max_severity["metadata"].get("severity") == "緊急":
                    result["recommendation"] = "立即就醫"
                elif max_severity["metadata"].get("severity") == "中度":
                    result["recommendation"] = "建議在 24 小時內就醫檢查"
                else:
                    result["recommendation"] = "居家觀察，如症狀加重請就醫"
            else:
                result["recommendation"] = "無法判斷，建議諮詢醫療人員"

            return result

    # 創建症狀檢查器
    checker = SymptomChecker()
    checker.load_symptom_database()

    # 測試症狀檢查
    test_cases = [
        "我有點發燒和咳嗽，流鼻涕",
        "突然胸口很痛，呼吸困難，心臟跳很快",
        "最近常常口渴，一直想喝水，體重也減輕了",
    ]

    print("\n症狀檢查結果：\n")

    for i, symptoms in enumerate(test_cases, 1):
        print(f"案例 {i}: {symptoms}")
        result = checker.check_symptoms(symptoms)

        if result["is_emergency"]:
            print(f"  ⚠️⚠️⚠️ 緊急情況！")

        print(f"  可能病症 ({len(result['possible_conditions'])} 種):")
        for j, condition in enumerate(result["possible_conditions"][:2], 1):
            print(
                f"    {j}. {condition['condition']} "
                f"(信心度: {condition['confidence']:.2f}, "
                f"嚴重度: {condition['severity']})"
            )

        print(f"  建議: {result['recommendation']}")
        print()

    print("⚠️ 免責聲明：此工具僅供參考，不能替代專業醫療診斷")
    print("✓ 症狀檢查器場景完成")


def main():
    """執行所有場景"""
    print("\n" + "=" * 60)
    print("實際應用場景範例")
    print("=" * 60)

    try:
        scenario_1_virtual_clinic()
        scenario_2_health_education()
        scenario_3_medication_assistant()
        scenario_4_symptom_checker()

        print("\n" + "=" * 60)
        print("所有實際場景範例執行完成！")
        print("=" * 60)

        print("\n場景總結:")
        print("1. 虛擬診所 - 24/7 線上諮詢服務")
        print("2. 健康教育 - 個人化學習推薦")
        print("3. 用藥助手 - 藥物資訊查詢")
        print("4. 症狀檢查 - AI 輔助初步診斷")

        print("\n這些場景展示了:")
        print("- RAG 系統在真實醫療場景的應用")
        print("- 安全過濾和緊急檢測的重要性")
        print("- 個人化和上下文感知的服務")
        print("- 醫療 AI 的責任和免責聲明")

    except Exception as e:
        logger.error(f"執行場景時發生錯誤: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
