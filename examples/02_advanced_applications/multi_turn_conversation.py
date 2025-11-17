#!/usr/bin/env python3
"""
案例 2.2: 多輪對話管理示例

這個範例展示如何實現和管理多輪對話，包括對話歷史記錄、
上下文維護和對話狀態管理。

運行方式:
    python examples/02_advanced_applications/multi_turn_conversation.py
"""

import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
from medical_chatbot.models.model_manager import ModelManager
from medical_chatbot.inference.generator import TextGenerator


class ConversationManager:
    """對話管理器類"""

    def __init__(
        self,
        model_manager: ModelManager,
        max_history: int = 10,
        system_prompt: str = None
    ):
        """初始化對話管理器

        Args:
            model_manager: 模型管理器實例
            max_history: 最大對話歷史長度
            system_prompt: 系統提示詞
        """
        self.model_manager = model_manager
        self.generator = TextGenerator(
            model=model_manager.model,
            tokenizer=model_manager.tokenizer
        )
        self.max_history = max_history

        # 預設系統提示詞
        self.system_prompt = system_prompt or (
            "你是一位專業的醫療人員，請提供準確且有幫助的醫療建議。"
            "你會根據對話歷史提供連貫的回答。"
        )

        # 對話歷史
        self.conversation_history: List[Dict[str, str]] = []

        # 會話元數據
        self.metadata = {
            "session_id": datetime.now().strftime("%Y%m%d_%H%M%S"),
            "start_time": datetime.now().isoformat(),
            "turn_count": 0
        }

    def add_message(self, role: str, content: str):
        """添加訊息到對話歷史

        Args:
            role: 角色 (system/user/assistant)
            content: 訊息內容
        """
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }

        self.conversation_history.append(message)

        # 限制歷史長度
        if len(self.conversation_history) > self.max_history:
            # 保留系統訊息和最近的對話
            system_messages = [
                m for m in self.conversation_history
                if m["role"] == "system"
            ]
            recent_messages = [
                m for m in self.conversation_history
                if m["role"] != "system"
            ][-self.max_history:]

            self.conversation_history = system_messages + recent_messages

    def get_messages_for_generation(self) -> List[Dict[str, str]]:
        """獲取用於生成的訊息列表

        Returns:
            訊息列表（不含 timestamp）
        """
        messages = []

        # 確保有系統提示詞
        if not any(m["role"] == "system" for m in self.conversation_history):
            messages.append({
                "role": "system",
                "content": self.system_prompt
            })

        # 添加對話歷史（移除 timestamp）
        for msg in self.conversation_history:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })

        return messages

    def chat(self, user_input: str) -> str:
        """進行一輪對話

        Args:
            user_input: 用戶輸入

        Returns:
            助手回應
        """
        # 添加用戶訊息
        self.add_message("user", user_input)

        # 獲取生成用的訊息
        messages = self.get_messages_for_generation()

        # 生成回應
        response = self.generator.generate(messages)

        # 添加助手回應
        self.add_message("assistant", response)

        # 更新元數據
        self.metadata["turn_count"] += 1
        self.metadata["last_update"] = datetime.now().isoformat()

        return response

    def get_conversation_summary(self) -> Dict[str, Any]:
        """獲取對話摘要

        Returns:
            對話摘要字典
        """
        user_messages = [
            m for m in self.conversation_history
            if m["role"] == "user"
        ]
        assistant_messages = [
            m for m in self.conversation_history
            if m["role"] == "assistant"
        ]

        return {
            "session_id": self.metadata["session_id"],
            "total_turns": self.metadata["turn_count"],
            "total_messages": len(self.conversation_history),
            "user_messages": len(user_messages),
            "assistant_messages": len(assistant_messages),
            "start_time": self.metadata["start_time"],
            "last_update": self.metadata.get("last_update", "N/A")
        }

    def save_conversation(self, output_path: str):
        """保存對話歷史

        Args:
            output_path: 輸出文件路徑
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        conversation_data = {
            "metadata": self.metadata,
            "system_prompt": self.system_prompt,
            "conversation_history": self.conversation_history,
            "summary": self.get_conversation_summary()
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(conversation_data, f, ensure_ascii=False, indent=2)

        print(f"✓ 對話已保存到: {output_path}")

    def load_conversation(self, input_path: str):
        """載入對話歷史

        Args:
            input_path: 輸入文件路徑
        """
        input_file = Path(input_path)

        if not input_file.exists():
            raise FileNotFoundError(f"文件不存在: {input_path}")

        with open(input_file, 'r', encoding='utf-8') as f:
            conversation_data = json.load(f)

        self.metadata = conversation_data.get("metadata", {})
        self.system_prompt = conversation_data.get("system_prompt", self.system_prompt)
        self.conversation_history = conversation_data.get("conversation_history", [])

        print(f"✓ 對話已載入: {input_path}")

    def reset_conversation(self):
        """重置對話"""
        self.conversation_history = []
        self.metadata = {
            "session_id": datetime.now().strftime("%Y%m%d_%H%M%S"),
            "start_time": datetime.now().isoformat(),
            "turn_count": 0
        }
        print("✓ 對話已重置")

    def display_conversation(self):
        """顯示對話歷史"""
        print("\n" + "=" * 60)
        print("對話歷史")
        print("=" * 60)

        for i, msg in enumerate(self.conversation_history, 1):
            if msg["role"] == "system":
                continue

            role_display = "👤 用戶" if msg["role"] == "user" else "🤖 助手"
            print(f"\n[{i}] {role_display}:")
            print(f"    {msg['content']}")
            print(f"    時間: {msg.get('timestamp', 'N/A')}")


def demo_basic_conversation():
    """示範基本多輪對話"""
    print("\n" + "=" * 60)
    print("示範 1: 基本多輪對話")
    print("=" * 60)

    # 初始化
    model_manager = ModelManager()
    model_manager.load_model()
    conversation = ConversationManager(model_manager)

    # 模擬多輪對話
    dialogue = [
        "我最近經常頭痛",
        "已經持續一週了",
        "是悶痛的感覺，主要在額頭部位",
        "我平常工作壓力比較大，經常加班",
        "好的，我會注意休息，謝謝醫生"
    ]

    print("\n開始對話...\n")

    for i, user_input in enumerate(dialogue, 1):
        print(f"\n{'─' * 60}")
        print(f"第 {i} 輪對話")
        print(f"{'─' * 60}")
        print(f"👤 用戶: {user_input}")

        response = conversation.chat(user_input)
        print(f"🤖 助手: {response}")

    # 顯示對話摘要
    summary = conversation.get_conversation_summary()
    print("\n" + "=" * 60)
    print("對話摘要:")
    print("=" * 60)
    for key, value in summary.items():
        print(f"{key}: {value}")

    # 保存對話
    conversation.save_conversation("output/conversation_basic.json")


def demo_context_management():
    """示範上下文管理"""
    print("\n" + "=" * 60)
    print("示範 2: 上下文管理")
    print("=" * 60)

    # 初始化
    model_manager = ModelManager()
    model_manager.load_model()

    # 使用較短的歷史長度來示範
    conversation = ConversationManager(model_manager, max_history=6)

    # 長對話
    dialogue = [
        "我有糖尿病",
        "是第二型糖尿病",
        "確診大約兩年了",
        "目前有在吃藥控制",
        "血糖控制還算穩定",
        "飲食上我該注意什麼？",
        "運動方面呢？",
        "我可以吃水果嗎？"
    ]

    print(f"\n開始對話（歷史長度限制: {conversation.max_history}）...\n")

    for i, user_input in enumerate(dialogue, 1):
        print(f"\n第 {i} 輪: {user_input}")
        response = conversation.chat(user_input)
        print(f"回應: {response[:80]}...")

        # 顯示當前歷史長度
        print(f"當前歷史長度: {len(conversation.conversation_history)}")

    # 顯示最終對話歷史
    conversation.display_conversation()


def demo_conversation_persistence():
    """示範對話持久化"""
    print("\n" + "=" * 60)
    print("示範 3: 對話持久化")
    print("=" * 60)

    # 初始化
    model_manager = ModelManager()
    model_manager.load_model()
    conversation = ConversationManager(model_manager)

    # 第一階段對話
    print("\n第一階段對話:")
    response1 = conversation.chat("我有高血壓")
    print(f"回應 1: {response1}")

    response2 = conversation.chat("飲食上應該注意什麼？")
    print(f"回應 2: {response2}")

    # 保存對話
    save_path = "output/conversation_saved.json"
    conversation.save_conversation(save_path)

    # 創建新的對話管理器並載入
    print("\n創建新的會話並載入之前的對話...")
    new_conversation = ConversationManager(model_manager)
    new_conversation.load_conversation(save_path)

    # 顯示載入的對話
    new_conversation.display_conversation()

    # 繼續對話
    print("\n繼續對話:")
    response3 = new_conversation.chat("那運動方面呢？")
    print(f"回應 3: {response3}")

    # 顯示更新後的摘要
    summary = new_conversation.get_conversation_summary()
    print("\n對話摘要:")
    for key, value in summary.items():
        print(f"{key}: {value}")


def demo_interactive_conversation():
    """示範互動式對話"""
    print("\n" + "=" * 60)
    print("示範 4: 互動式對話")
    print("=" * 60)
    print("\n輸入 'save' 保存對話，'quit' 或 'exit' 結束\n")

    # 初始化
    model_manager = ModelManager()
    model_manager.load_model()
    conversation = ConversationManager(model_manager)

    while True:
        try:
            # 獲取用戶輸入
            user_input = input("\n👤 您: ").strip()

            # 檢查命令
            if user_input.lower() in ['quit', 'exit', '退出', '結束']:
                # 詢問是否保存
                save_choice = input("\n是否保存對話? (y/n): ").strip().lower()
                if save_choice == 'y':
                    session_id = conversation.metadata["session_id"]
                    save_path = f"output/conversation_{session_id}.json"
                    conversation.save_conversation(save_path)
                print("\n再見！")
                break

            elif user_input.lower() == 'save':
                session_id = conversation.metadata["session_id"]
                save_path = f"output/conversation_{session_id}.json"
                conversation.save_conversation(save_path)
                continue

            elif user_input.lower() == 'summary':
                summary = conversation.get_conversation_summary()
                print("\n對話摘要:")
                for key, value in summary.items():
                    print(f"  {key}: {value}")
                continue

            elif not user_input:
                print("請輸入有效的問題。")
                continue

            # 生成回應
            response = conversation.chat(user_input)
            print(f"\n🤖 助手: {response}")

        except KeyboardInterrupt:
            print("\n\n對話已中斷")
            break
        except Exception as e:
            print(f"\n發生錯誤: {str(e)}")
            continue


def main():
    """主函數"""
    print("""
╔══════════════════════════════════════════════════════════╗
║        醫療聊天機器人 - 多輪對話管理示例                ║
╚══════════════════════════════════════════════════════════╝
    """)

    print("\n選擇要運行的示範:")
    print("1. 基本多輪對話")
    print("2. 上下文管理")
    print("3. 對話持久化")
    print("4. 互動式對話")
    print("5. 運行所有示範（除了互動式）")

    try:
        choice = input("\n請輸入選項 (1-5): ").strip()

        if choice == "1":
            demo_basic_conversation()
        elif choice == "2":
            demo_context_management()
        elif choice == "3":
            demo_conversation_persistence()
        elif choice == "4":
            demo_interactive_conversation()
        elif choice == "5":
            demo_basic_conversation()
            demo_context_management()
            demo_conversation_persistence()
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
