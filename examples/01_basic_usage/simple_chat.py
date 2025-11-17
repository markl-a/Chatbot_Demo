#!/usr/bin/env python3
"""
案例 1.1: 簡單的命令行對話示例

這個範例展示如何使用醫療聊天機器人進行基本的問答交互。
適合初學者快速了解系統的基本使用方式。

運行方式:
    python examples/01_basic_usage/simple_chat.py
"""

from medical_chatbot.models.model_manager import ModelManager
from medical_chatbot.inference.generator import TextGenerator


def simple_chat_example():
    """簡單的單輪對話示例"""
    print("=" * 60)
    print("醫療聊天機器人 - 簡單對話示例")
    print("=" * 60)

    # 1. 初始化模型管理器
    print("\n[步驟 1] 正在載入模型...")
    model_manager = ModelManager()
    model_manager.load_model()

    # 2. 創建文本生成器
    print("[步驟 2] 正在初始化生成器...")
    generator = TextGenerator(
        model=model_manager.model,
        tokenizer=model_manager.tokenizer
    )

    # 3. 準備測試問題
    test_questions = [
        "我最近經常頭痛，該怎麼辦？",
        "感冒了應該注意什麼？",
        "如何預防高血壓？",
        "每天肚子痛是什麼狀況？",
        "失眠該如何改善？"
    ]

    print("\n[步驟 3] 開始對話測試\n")

    # 4. 逐一處理問題
    for i, question in enumerate(test_questions, 1):
        print(f"\n{'─' * 60}")
        print(f"問題 {i}: {question}")
        print(f"{'─' * 60}")

        # 準備對話訊息
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

        # 生成回應
        response = generator.generate(messages)

        print(f"\n回答: {response}")

    print("\n" + "=" * 60)
    print("對話測試完成！")
    print("=" * 60)


def interactive_chat():
    """互動式對話模式"""
    print("\n" + "=" * 60)
    print("互動式對話模式 (輸入 'quit' 或 'exit' 結束)")
    print("=" * 60)

    # 初始化
    model_manager = ModelManager()
    model_manager.load_model()
    generator = TextGenerator(
        model=model_manager.model,
        tokenizer=model_manager.tokenizer
    )

    # 對話循環
    while True:
        try:
            # 獲取用戶輸入
            question = input("\n您的問題: ").strip()

            # 檢查退出命令
            if question.lower() in ['quit', 'exit', '退出', '結束']:
                print("\n感謝使用，再見！")
                break

            # 空輸入檢查
            if not question:
                print("請輸入有效的問題。")
                continue

            # 生成回應
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

            print("\n正在思考...")
            response = generator.generate(messages)
            print(f"\n醫療助手: {response}")

        except KeyboardInterrupt:
            print("\n\n程序已中斷，再見！")
            break
        except Exception as e:
            print(f"\n發生錯誤: {str(e)}")
            continue


def main():
    """主函數"""
    print("""
╔══════════════════════════════════════════════════════════╗
║        醫療聊天機器人 - 簡單對話示例                    ║
╚══════════════════════════════════════════════════════════╝

請選擇模式:
1. 運行預設問題示例
2. 進入互動式對話模式

    """)

    try:
        choice = input("請輸入選項 (1 或 2): ").strip()

        if choice == "1":
            simple_chat_example()
        elif choice == "2":
            interactive_chat()
        else:
            print("無效的選項，請重新運行程序。")

    except Exception as e:
        print(f"\n發生錯誤: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
