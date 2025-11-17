#!/usr/bin/env python3
"""
案例 1.2: REST API 調用示例

這個範例展示如何通過 HTTP API 與醫療聊天機器人交互。
包含單輪對話和多輪對話的完整示例。

前置條件:
    確保 API 服務已啟動: python -m medical_chatbot.api.server

運行方式:
    python examples/01_basic_usage/api_call.py
"""

import requests
import json
from typing import Dict, List, Any


# API 配置
API_BASE_URL = "http://localhost:8000"
HEADERS = {"Content-Type": "application/json"}


def test_health_check():
    """測試 API 健康狀態"""
    print("\n" + "=" * 60)
    print("測試 1: 健康檢查")
    print("=" * 60)

    try:
        response = requests.get(f"{API_BASE_URL}/health")
        response.raise_for_status()

        data = response.json()
        print(f"✓ API 狀態: {data.get('status', 'unknown')}")
        print(f"✓ 服務: {data.get('service', 'unknown')}")

        return True
    except Exception as e:
        print(f"✗ 健康檢查失敗: {str(e)}")
        return False


def test_single_chat(question: str, temperature: float = 0.15) -> Dict[str, Any]:
    """測試單輪對話 API

    Args:
        question: 要詢問的問題
        temperature: 生成溫度參數 (0.0-1.0)

    Returns:
        API 回應的字典
    """
    print("\n" + "=" * 60)
    print("測試 2: 單輪對話")
    print("=" * 60)

    payload = {
        "message": question,
        "temperature": temperature,
        "max_new_tokens": 90
    }

    print(f"\n問題: {question}")
    print(f"參數: temperature={temperature}")

    try:
        response = requests.post(
            f"{API_BASE_URL}/chat",
            headers=HEADERS,
            json=payload
        )
        response.raise_for_status()

        data = response.json()
        print(f"\n回答: {data.get('response', 'No response')}")

        # 顯示額外資訊
        if "metadata" in data:
            metadata = data["metadata"]
            print(f"\n生成資訊:")
            print(f"  - 生成的 tokens: {metadata.get('tokens_generated', 'N/A')}")
            print(f"  - 推理時間: {metadata.get('inference_time', 'N/A')}s")

        return data

    except requests.exceptions.ConnectionError:
        print("✗ 無法連接到 API 服務。請確保服務已啟動:")
        print("  python -m medical_chatbot.api.server")
        return {}
    except Exception as e:
        print(f"✗ 單輪對話失敗: {str(e)}")
        return {}


def test_multi_turn_conversation(
    messages: List[Dict[str, str]],
    temperature: float = 0.15
) -> Dict[str, Any]:
    """測試多輪對話 API

    Args:
        messages: 對話歷史列表
        temperature: 生成溫度參數

    Returns:
        API 回應的字典
    """
    print("\n" + "=" * 60)
    print("測試 3: 多輪對話")
    print("=" * 60)

    payload = {
        "messages": messages,
        "temperature": temperature,
        "max_new_tokens": 90
    }

    print("\n對話歷史:")
    for i, msg in enumerate(messages, 1):
        role = msg["role"]
        content = msg["content"]
        print(f"  {i}. [{role}] {content}")

    try:
        response = requests.post(
            f"{API_BASE_URL}/conversation",
            headers=HEADERS,
            json=payload
        )
        response.raise_for_status()

        data = response.json()
        print(f"\n回答: {data.get('response', 'No response')}")

        return data

    except Exception as e:
        print(f"✗ 多輪對話失敗: {str(e)}")
        return {}


def test_batch_questions():
    """批量測試多個問題"""
    print("\n" + "=" * 60)
    print("測試 4: 批量問題處理")
    print("=" * 60)

    questions = [
        "我有高血壓，飲食上應該注意什麼？",
        "糖尿病患者可以吃哪些水果？",
        "如何預防心血管疾病？",
        "長期失眠會有什麼影響？"
    ]

    results = []

    for i, question in enumerate(questions, 1):
        print(f"\n[{i}/{len(questions)}] 處理問題: {question[:30]}...")

        payload = {
            "message": question,
            "temperature": 0.15
        }

        try:
            response = requests.post(
                f"{API_BASE_URL}/chat",
                headers=HEADERS,
                json=payload,
                timeout=30
            )
            response.raise_for_status()

            data = response.json()
            results.append({
                "question": question,
                "answer": data.get("response", ""),
                "status": "success"
            })
            print(f"  ✓ 完成")

        except Exception as e:
            results.append({
                "question": question,
                "error": str(e),
                "status": "failed"
            })
            print(f"  ✗ 失敗: {str(e)}")

    # 顯示結果摘要
    print("\n" + "─" * 60)
    print("批量處理結果摘要:")
    print("─" * 60)

    success_count = sum(1 for r in results if r["status"] == "success")
    print(f"成功: {success_count}/{len(questions)}")
    print(f"失敗: {len(questions) - success_count}/{len(questions)}")

    return results


def test_custom_parameters():
    """測試不同的生成參數"""
    print("\n" + "=" * 60)
    print("測試 5: 自定義生成參數")
    print("=" * 60)

    question = "如何保持身體健康？"

    # 測試不同的溫度設定
    temperatures = [0.1, 0.3, 0.5, 0.7]

    print(f"\n問題: {question}\n")

    for temp in temperatures:
        print(f"\n{'─' * 40}")
        print(f"溫度 = {temp}")
        print(f"{'─' * 40}")

        payload = {
            "message": question,
            "temperature": temp,
            "max_new_tokens": 60,
            "top_p": 0.9,
            "top_k": 50
        }

        try:
            response = requests.post(
                f"{API_BASE_URL}/chat",
                headers=HEADERS,
                json=payload
            )
            response.raise_for_status()

            data = response.json()
            print(f"回答: {data.get('response', 'No response')}")

        except Exception as e:
            print(f"錯誤: {str(e)}")


def main():
    """主函數"""
    print("""
╔══════════════════════════════════════════════════════════╗
║        醫療聊天機器人 - API 調用示例                    ║
╚══════════════════════════════════════════════════════════╝
    """)

    # 1. 健康檢查
    if not test_health_check():
        print("\n⚠️  API 服務未運行，請先啟動服務:")
        print("   python -m medical_chatbot.api.server")
        return

    # 2. 單輪對話測試
    test_single_chat("我最近經常頭暈，這是什麼原因？")

    # 3. 多輪對話測試
    messages = [
        {
            "role": "system",
            "content": "你是一位專業的醫療人員，請提供準確且有幫助的醫療建議。"
        },
        {
            "role": "user",
            "content": "我有高血壓"
        },
        {
            "role": "assistant",
            "content": "高血壓需要長期管理。請問您目前有在服用藥物嗎？"
        },
        {
            "role": "user",
            "content": "有，但還是偶爾會頭暈"
        }
    ]
    test_multi_turn_conversation(messages)

    # 4. 批量處理測試
    test_batch_questions()

    # 5. 參數調整測試
    test_custom_parameters()

    print("\n" + "=" * 60)
    print("所有測試完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
