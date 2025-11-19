"""
範例：使用不同的中文/醫療模型

展示如何在專案中使用不同的預訓練模型。
"""
from pathlib import Path
import sys

# 添加專案路徑
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from medical_chatbot.models.model_manager import ModelManager
from medical_chatbot.inference.generator import Generator
from medical_chatbot.utils.config import Config, ModelConfig
from medical_chatbot.utils.logger import setup_logger

logger = setup_logger()


def example_taide_model():
    """使用 TAIDE 模型"""
    print("\n" + "=" * 60)
    print("範例 1: TAIDE-LX-8B-Chat 模型")
    print("=" * 60)

    # 配置 TAIDE 模型
    config = Config()
    config.model = ModelConfig(
        base_model="taide/Llama3-TAIDE-LX-8B-Chat-Alpha1",
        device="auto",
        load_in_8bit=True,  # 使用 8-bit 量化節省記憶體
        trust_remote_code=True,
    )

    # 創建模型管理器和生成器
    logger.info("載入 TAIDE 模型...")
    # model_manager = ModelManager(config, autoload=True)
    # generator = Generator(config)

    # # 測試生成
    # query = "什麼是高血壓？如何預防？"
    # response = generator.generate(query, max_length=256, temperature=0.7)

    # print(f"\n問題: {query}")
    # print(f"回答: {response}")

    print("\n✓ TAIDE 模型範例完成")
    print("特點: 繁體中文優化、台灣在地化")


def example_breeze_model():
    """使用 Breeze 模型"""
    print("\n" + "=" * 60)
    print("範例 2: Breeze-7B-Instruct 模型")
    print("=" * 60)

    # 配置 Breeze 模型
    config = Config()
    config.model = ModelConfig(
        base_model="MediaTek-Research/Breeze-7B-Instruct-v1_0",
        device="auto",
        load_in_8bit=True,
    )

    logger.info("載入 Breeze 模型...")
    # model_manager = ModelManager(config, autoload=True)
    # generator = Generator(config)

    # query = "糖尿病患者的飲食建議"
    # response = generator.generate(query, max_length=256)

    # print(f"\n問題: {query}")
    # print(f"回答: {response}")

    print("\n✓ Breeze 模型範例完成")
    print("特點: MediaTek 開發、繁體中文支援")


def example_taiwan_llm():
    """使用 Taiwan-LLM 模型"""
    print("\n" + "=" * 60)
    print("範例 3: Taiwan-LLM-7B-v2.1-Chat")
    print("=" * 60)

    # 配置 Taiwan-LLM 模型
    config = Config()
    config.model = ModelConfig(
        base_model="yentinglin/Taiwan-LLM-7B-v2.1-chat",
        device="auto",
        load_in_8bit=True,
    )

    logger.info("載入 Taiwan-LLM 模型...")
    # model_manager = ModelManager(config, autoload=True)
    # generator = Generator(config)

    # query = "感冒和流感的區別是什麼？"
    # response = generator.generate(query)

    # print(f"\n問題: {query}")
    # print(f"回答: {response}")

    print("\n✓ Taiwan-LLM 模型範例完成")
    print("特點: 台灣大學開發、繁體中文訓練")


def example_qwen_medical():
    """使用 Qwen 醫療模型"""
    print("\n" + "=" * 60)
    print("範例 4: Qwen-7B-Chat (醫療微調)")
    print("=" * 60)

    # 配置 Qwen 模型
    config = Config()
    config.model = ModelConfig(
        base_model="Qwen/Qwen-7B-Chat",
        device="auto",
        load_in_8bit=True,
        trust_remote_code=True,
    )

    logger.info("載入 Qwen 模型...")
    # model_manager = ModelManager(config, autoload=True)
    # generator = Generator(config)

    # query = "心臟病的早期症狀有哪些？"
    # response = generator.generate(query)

    # print(f"\n問題: {query}")
    # print(f"回答: {response}")

    print("\n✓ Qwen 模型範例完成")
    print("特點: 阿里巴巴開發、多語言支援、醫療知識豐富")


def example_chatglm_medical():
    """使用 ChatGLM 醫療模型"""
    print("\n" + "=" * 60)
    print("範例 5: ChatGLM3-6B (醫療微調)")
    print("=" * 60)

    # 配置 ChatGLM 模型
    config = Config()
    config.model = ModelConfig(
        base_model="THUDM/chatglm3-6b",
        device="auto",
        load_in_8bit=True,
        trust_remote_code=True,
    )

    logger.info("載入 ChatGLM3 模型...")
    # model_manager = ModelManager(config, autoload=True)
    # generator = Generator(config)

    # query = "如何降低膽固醇？"
    # response = generator.generate(query)

    # print(f"\n問題: {query}")
    # print(f"回答: {response}")

    print("\n✓ ChatGLM3 模型範例完成")
    print("特點: 清華開發、對話能力強、中文優化")


def example_model_comparison():
    """比較不同模型的表現"""
    print("\n" + "=" * 60)
    print("範例 6: 多模型比較")
    print("=" * 60)

    models = [
        {
            "name": "TAIDE-LX-8B",
            "model": "taide/Llama3-TAIDE-LX-8B-Chat-Alpha1",
            "features": ["繁體中文", "台灣在地化", "LLaMA3 架構"],
        },
        {
            "name": "Breeze-7B",
            "model": "MediaTek-Research/Breeze-7B-Instruct-v1_0",
            "features": ["繁體中文", "MediaTek 開發", "Mistral 架構"],
        },
        {
            "name": "Taiwan-LLM-7B",
            "model": "yentinglin/Taiwan-LLM-7B-v2.1-chat",
            "features": ["繁體中文", "台大開發", "LLaMA2 架構"],
        },
        {
            "name": "Qwen-7B",
            "model": "Qwen/Qwen-7B-Chat",
            "features": ["多語言", "醫療知識", "阿里巴巴"],
        },
        {
            "name": "ChatGLM3-6B",
            "model": "THUDM/chatglm3-6b",
            "features": ["中文優化", "對話能力", "清華開發"],
        },
    ]

    print("\n可用的醫療對話模型：\n")
    for i, model in enumerate(models, 1):
        print(f"{i}. {model['name']}")
        print(f"   模型: {model['model']}")
        print(f"   特點: {', '.join(model['features'])}")
        print()

    print("\n選擇建議:")
    print("- 繁體中文醫療: TAIDE-LX-8B 或 Breeze-7B")
    print("- 簡體中文醫療: Qwen-7B 或 ChatGLM3-6B")
    print("- 台灣在地化: TAIDE-LX-8B 或 Taiwan-LLM-7B")
    print("- 記憶體有限: 使用 load_in_8bit=True 或 4-bit 量化")


def example_custom_model():
    """使用自定義微調模型"""
    print("\n" + "=" * 60)
    print("範例 7: 自定義微調模型")
    print("=" * 60)

    # 配置自定義模型（基於 TAIDE 微調）
    config = Config()
    config.model = ModelConfig(
        base_model="taide/Llama3-TAIDE-LX-8B-Chat-Alpha1",
        # 如果有 LoRA 適配器，指定路徑
        # adapter_path="./output/medical_chatbot_lora",
        device="auto",
        load_in_8bit=True,
    )

    logger.info("載入自定義微調模型...")

    print("\n自定義微調流程:")
    print("1. 選擇基礎模型 (如 TAIDE-LX-8B)")
    print("2. 準備醫療對話資料集")
    print("3. 使用 LoRA 微調")
    print("4. 載入基礎模型 + LoRA 適配器")

    print("\n✓ 自定義模型範例完成")


def main():
    """執行所有範例"""
    print("\n" + "=" * 60)
    print("不同模型使用範例")
    print("=" * 60)

    try:
        # 執行各個範例（實際使用時取消註解）
        example_taide_model()
        example_breeze_model()
        example_taiwan_llm()
        example_qwen_medical()
        example_chatglm_medical()
        example_model_comparison()
        example_custom_model()

        print("\n" + "=" * 60)
        print("所有範例執行完成！")
        print("=" * 60)

        print("\n注意事項:")
        print("1. 首次使用需要下載模型（可能需要數 GB 空間）")
        print("2. 建議使用 8-bit 量化以節省記憶體")
        print("3. 不同模型對醫療問題的回答質量可能不同")
        print("4. 可以使用 HuggingFace Token 訪問私有模型")
        print("5. 記得設置適當的系統提示詞以提升醫療回答質量")

    except Exception as e:
        logger.error(f"執行範例時發生錯誤: {e}")
        raise


if __name__ == "__main__":
    main()
