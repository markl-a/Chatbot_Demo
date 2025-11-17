#!/usr/bin/env python3
"""
案例 1.3: 自定義配置參數使用示例

這個範例展示如何使用和自定義配置文件來控制模型行為。
學習如何調整推理參數以獲得最佳效果。

運行方式:
    python examples/01_basic_usage/config_usage.py
"""

import yaml
from pathlib import Path
from typing import Dict, Any
from medical_chatbot.models.model_manager import ModelManager
from medical_chatbot.inference.generator import TextGenerator


def load_config(config_path: str = "configs/config.yaml") -> Dict[str, Any]:
    """載入配置文件

    Args:
        config_path: 配置文件路徑

    Returns:
        配置字典
    """
    config_file = Path(config_path)

    if not config_file.exists():
        print(f"⚠️  配置文件不存在: {config_path}")
        print("使用預設配置...")
        return get_default_config()

    with open(config_file, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    return config


def get_default_config() -> Dict[str, Any]:
    """獲取預設配置

    Returns:
        預設配置字典
    """
    return {
        "model": {
            "name": "taide/TAIDE-LX-7B-Chat",
            "device": "cuda",
            "load_in_8bit": True
        },
        "inference": {
            "max_new_tokens": 90,
            "temperature": 0.15,
            "top_p": 0.15,
            "top_k": 50,
            "repetition_penalty": 1.6,
            "do_sample": True
        },
        "safety": {
            "enable_emergency_detection": True,
            "enable_content_filtering": True
        }
    }


def demonstrate_config_loading():
    """示範配置文件載入"""
    print("\n" + "=" * 60)
    print("示範 1: 載入配置文件")
    print("=" * 60)

    config = load_config()

    print("\n當前配置:")
    print(yaml.dump(config, allow_unicode=True, default_flow_style=False))


def demonstrate_inference_params():
    """示範不同推理參數的效果"""
    print("\n" + "=" * 60)
    print("示範 2: 不同推理參數的效果")
    print("=" * 60)

    # 初始化模型
    print("\n正在載入模型...")
    model_manager = ModelManager()
    model_manager.load_model()

    question = "如何保持良好的睡眠品質？"

    # 測試不同的參數組合
    param_configs = [
        {
            "name": "保守型 (低溫度)",
            "params": {
                "temperature": 0.1,
                "top_p": 0.1,
                "top_k": 30,
                "repetition_penalty": 1.8
            }
        },
        {
            "name": "平衡型 (中溫度)",
            "params": {
                "temperature": 0.3,
                "top_p": 0.3,
                "top_k": 50,
                "repetition_penalty": 1.6
            }
        },
        {
            "name": "創意型 (高溫度)",
            "params": {
                "temperature": 0.7,
                "top_p": 0.7,
                "top_k": 80,
                "repetition_penalty": 1.4
            }
        }
    ]

    print(f"\n測試問題: {question}\n")

    for config in param_configs:
        print(f"\n{'─' * 60}")
        print(f"配置: {config['name']}")
        print(f"參數: {config['params']}")
        print(f"{'─' * 60}")

        generator = TextGenerator(
            model=model_manager.model,
            tokenizer=model_manager.tokenizer,
            **config['params']
        )

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

        response = generator.generate(messages)
        print(f"\n回答: {response}")


def demonstrate_max_tokens():
    """示範最大 token 數量的影響"""
    print("\n" + "=" * 60)
    print("示範 3: 最大 Token 數量的影響")
    print("=" * 60)

    model_manager = ModelManager()
    model_manager.load_model()

    question = "請詳細說明糖尿病的預防方法。"

    token_limits = [30, 60, 120, 200]

    print(f"\n問題: {question}\n")

    for max_tokens in token_limits:
        print(f"\n{'─' * 60}")
        print(f"最大 Tokens: {max_tokens}")
        print(f"{'─' * 60}")

        generator = TextGenerator(
            model=model_manager.model,
            tokenizer=model_manager.tokenizer,
            max_new_tokens=max_tokens
        )

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

        response = generator.generate(messages)
        print(f"\n回答: {response}")
        print(f"回答長度: {len(response)} 字元")


def create_custom_config():
    """創建自定義配置文件"""
    print("\n" + "=" * 60)
    print("示範 4: 創建自定義配置文件")
    print("=" * 60)

    custom_config = {
        "model": {
            "name": "taide/TAIDE-LX-7B-Chat",
            "device": "cuda",
            "load_in_8bit": True,
            "trust_remote_code": True
        },
        "inference": {
            "max_new_tokens": 120,
            "temperature": 0.2,
            "top_p": 0.2,
            "top_k": 40,
            "repetition_penalty": 1.7,
            "do_sample": True,
            "num_beams": 1
        },
        "safety": {
            "enable_emergency_detection": True,
            "enable_content_filtering": True,
            "emergency_keywords": [
                "自殺", "輕生", "想死",
                "嚴重出血", "無法呼吸", "劇烈胸痛"
            ]
        },
        "logging": {
            "level": "INFO",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        }
    }

    # 保存自定義配置
    custom_config_path = Path("configs/custom_config.yaml")
    custom_config_path.parent.mkdir(parents=True, exist_ok=True)

    with open(custom_config_path, 'w', encoding='utf-8') as f:
        yaml.dump(custom_config, f, allow_unicode=True, default_flow_style=False)

    print(f"\n✓ 自定義配置已保存到: {custom_config_path}")
    print("\n配置內容:")
    print(yaml.dump(custom_config, allow_unicode=True, default_flow_style=False))


def demonstrate_safety_config():
    """示範安全配置的使用"""
    print("\n" + "=" * 60)
    print("示範 5: 安全配置")
    print("=" * 60)

    safety_config = {
        "enable_emergency_detection": True,
        "enable_content_filtering": True,
        "emergency_keywords": [
            "自殺", "輕生", "想死",
            "嚴重出血", "無法呼吸", "劇烈胸痛",
            "中毒", "昏迷", "意識模糊"
        ],
        "emergency_response": "這似乎是緊急情況。請立即撥打 119 或前往最近的急診室尋求專業醫療協助。",
        "disclaimer": "⚠️ 本系統提供的資訊僅供參考，不能替代專業醫療診斷和治療。"
    }

    print("\n安全配置:")
    print(yaml.dump(safety_config, allow_unicode=True, default_flow_style=False))

    print("\n緊急關鍵字偵測測試:")

    test_cases = [
        "我覺得胸口很痛，呼吸困難",
        "如何預防感冒？",
        "我有自殺的念頭"
    ]

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n測試 {i}: {test_case}")

        # 檢查是否包含緊急關鍵字
        is_emergency = any(
            keyword in test_case
            for keyword in safety_config["emergency_keywords"]
        )

        if is_emergency:
            print(f"⚠️  偵測到緊急狀況！")
            print(f"回應: {safety_config['emergency_response']}")
        else:
            print("✓ 正常問題")


def main():
    """主函數"""
    print("""
╔══════════════════════════════════════════════════════════╗
║        醫療聊天機器人 - 配置使用示例                    ║
╚══════════════════════════════════════════════════════════╝
    """)

    print("\n選擇要運行的示範:")
    print("1. 載入配置文件")
    print("2. 不同推理參數的效果")
    print("3. 最大 Token 數量的影響")
    print("4. 創建自定義配置文件")
    print("5. 安全配置示範")
    print("6. 運行所有示範")

    try:
        choice = input("\n請輸入選項 (1-6): ").strip()

        if choice == "1":
            demonstrate_config_loading()
        elif choice == "2":
            demonstrate_inference_params()
        elif choice == "3":
            demonstrate_max_tokens()
        elif choice == "4":
            create_custom_config()
        elif choice == "5":
            demonstrate_safety_config()
        elif choice == "6":
            demonstrate_config_loading()
            demonstrate_inference_params()
            demonstrate_max_tokens()
            create_custom_config()
            demonstrate_safety_config()
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
