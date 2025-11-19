"""
範例：RAG 系統完整使用指南

展示如何構建和使用醫療知識庫增強的對話系統。
"""
from pathlib import Path
import sys

# 添加專案路徑
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from medical_chatbot.rag import (
    MedicalEmbedder,
    MedicalRetriever,
    MedicalVectorStore,
    RAGGenerator,
)
from medical_chatbot.inference.generator import Generator
from medical_chatbot.utils.config import load_config
from medical_chatbot.utils.logger import setup_logger

logger = setup_logger()


def example_basic_rag():
    """基礎 RAG 使用"""
    print("\n" + "=" * 60)
    print("範例 1: 基礎 RAG 系統")
    print("=" * 60)

    # 1. 創建嵌入器
    logger.info("初始化嵌入器...")
    embedder = MedicalEmbedder(
        model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        device="auto",
    )

    # 2. 創建檢索器
    logger.info("初始化檢索器...")
    retriever = MedicalRetriever(
        embedder=embedder, top_k=3, score_threshold=0.5
    )

    # 3. 添加醫療知識
    medical_knowledge = [
        """
        高血壓定義：
        高血壓是指血壓持續高於正常值的狀態。根據世界衛生組織（WHO）的標準，
        成人血壓持續在 140/90 mmHg 以上即為高血壓。
        """,
        """
        高血壓症狀：
        大多數高血壓患者早期無明顯症狀，常被稱為「隱形殺手」。
        部分患者可能出現頭痛、頭暈、心悸、疲勞等症狀。
        """,
        """
        高血壓預防：
        1. 減少鹽分攝取（每日少於 5 克）
        2. 保持健康體重（BMI 18.5-24）
        3. 規律運動（每週至少 150 分鐘中等強度運動）
        4. 限制飲酒
        5. 戒菸
        6. 減少壓力
        """,
        """
        糖尿病定義：
        糖尿病是一種代謝性疾病，特徵是血糖長期高於正常值。
        主要類型包括第一型糖尿病、第二型糖尿病和妊娠糖尿病。
        診斷標準：空腹血糖 ≥ 126 mg/dL 或糖化血色素 ≥ 6.5%。
        """,
        """
        糖尿病症狀：
        典型症狀包括「三多一少」：
        - 多尿（頻尿）
        - 多飲（口渴）
        - 多食（容易餓）
        - 體重減少
        其他症狀：疲勞、視力模糊、傷口癒合慢。
        """,
    ]

    logger.info("添加醫療知識到向量存儲...")
    retriever.add_documents(medical_knowledge)

    # 4. 測試檢索
    query = "高血壓有什麼症狀？"
    logger.info(f"檢索查詢: {query}")

    results = retriever.retrieve(query, top_k=2)

    print(f"\n查詢: {query}")
    print(f"\n檢索到 {len(results)} 個相關文檔：\n")

    for i, result in enumerate(results, 1):
        print(f"文檔 {i} (相似度: {result['score']:.3f}):")
        print(result["text"].strip())
        print()

    print("✓ 基礎 RAG 範例完成")


def example_rag_with_generator():
    """RAG 結合生成器"""
    print("\n" + "=" * 60)
    print("範例 2: RAG + 語言模型生成")
    print("=" * 60)

    # 載入配置和模型
    logger.info("載入模型配置...")
    config = load_config("configs/config.yaml")

    # 創建生成器（模擬）
    # generator = Generator(config)

    # 創建 RAG 組件
    embedder = MedicalEmbedder()
    retriever = MedicalRetriever(embedder=embedder, top_k=3)

    # 添加知識
    medical_docs = [
        "心臟病的常見症狀包括胸痛、呼吸困難、心悸、疲勞和頭暈。",
        "冠心病是最常見的心臟病類型，由冠狀動脈狹窄或阻塞引起。",
        "預防心臟病的方法：健康飲食、規律運動、控制體重、戒菸限酒。",
        "急性心肌梗塞的警訊：劇烈胸痛、冒冷汗、噁心、呼吸困難。",
    ]

    retriever.add_documents(medical_docs)

    # 創建 RAG 生成器
    # rag_generator = RAGGenerator(
    #     generator=generator,
    #     retriever=retriever,
    #     max_context_docs=3
    # )

    # 測試生成
    query = "如何預防心臟病？"
    logger.info(f"RAG 查詢: {query}")

    # result = rag_generator.generate(query, use_rag=True)

    # print(f"\n問題: {query}")
    # print(f"回答: {result['response']}")
    # print(f"\n使用了 {result['num_docs']} 個參考文檔")
    # print(f"上下文增強: {'是' if result['context_used'] else '否'}")

    print("\n✓ RAG + 生成器範例完成")


def example_knowledge_base_management():
    """知識庫管理"""
    print("\n" + "=" * 60)
    print("範例 3: 醫療知識庫管理")
    print("=" * 60)

    embedder = MedicalEmbedder()
    retriever = MedicalRetriever(embedder=embedder)

    # 從文件添加知識
    print("\n方法 1: 從單個文件添加")
    # retriever.add_from_file(
    #     "data/medical_knowledge/hypertension.txt",
    #     chunk_size=512,
    #     overlap=50
    # )

    # 從目錄批次添加
    print("方法 2: 從目錄批次添加")
    # retriever.add_from_directory(
    #     "data/medical_knowledge/",
    #     file_pattern="*.txt",
    #     chunk_size=512
    # )

    # 手動添加文檔
    print("方法 3: 手動添加文檔")
    docs = [
        "文檔 1: 高血壓的定義和診斷標準...",
        "文檔 2: 糖尿病的類型和症狀...",
        "文檔 3: 心臟病的預防措施...",
    ]

    metadata = [
        {"source": "醫學教科書", "category": "高血壓", "date": "2025-01"},
        {"source": "臨床指南", "category": "糖尿病", "date": "2025-01"},
        {"source": "預防醫學", "category": "心臟病", "date": "2025-01"},
    ]

    retriever.add_documents(docs, metadata=metadata)

    # 保存知識庫
    print("\n方法 4: 保存和載入知識庫")
    save_path = "data/vector_stores/medical_kb"
    # retriever.save(save_path)
    # logger.info(f"知識庫已保存到: {save_path}")

    # 載入知識庫
    # loaded_retriever = MedicalRetriever.load(save_path)
    # logger.info("知識庫已載入")

    # 查看統計
    stats = retriever.get_stats()
    print(f"\n知識庫統計:")
    print(f"- 文檔數量: {stats['num_documents']}")
    print(f"- 嵌入維度: {stats['embedding_dim']}")
    print(f"- 索引類型: {stats['index_type']}")

    print("\n✓ 知識庫管理範例完成")


def example_advanced_rag():
    """進階 RAG 功能"""
    print("\n" + "=" * 60)
    print("範例 4: 進階 RAG 功能")
    print("=" * 60)

    # 使用不同的嵌入模型
    print("\n選項 1: 使用醫療專用嵌入模型")
    embedder_medical = MedicalEmbedder(
        model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        # 或使用其他模型:
        # model_name="BAAI/bge-large-zh-v1.5",  # 中文優化
        # model_name="sentence-transformers/all-MiniLM-L6-v2",  # 輕量級
    )

    # 使用不同的向量索引
    print("\n選項 2: 使用不同的 FAISS 索引")

    # Flat 索引 - 精確但慢
    embedding_dim = embedder_medical.get_embedding_dimension()
    vector_store_flat = MedicalVectorStore(
        embedding_dim=embedding_dim, index_type="Flat", metric="cosine"
    )

    # IVF 索引 - 快速但需要訓練
    vector_store_ivf = MedicalVectorStore(
        embedding_dim=embedding_dim,
        index_type="IVF",
        nlist=100,  # 聚類數量
        metric="cosine",
    )

    # HNSW 索引 - 平衡速度和精度
    vector_store_hnsw = MedicalVectorStore(
        embedding_dim=embedding_dim, index_type="HNSW", metric="cosine"
    )

    print("\n索引類型選擇建議:")
    print("- Flat: 小型知識庫 (< 10K 文檔)，精確檢索")
    print("- IVF: 中型知識庫 (10K-1M 文檔)，快速檢索")
    print("- HNSW: 大型知識庫 (> 1M 文檔)，最快檢索")

    # 調整檢索參數
    print("\n選項 3: 調整檢索參數")
    retriever = MedicalRetriever(
        embedder=embedder_medical,
        top_k=5,  # 返回 top 5 文檔
        score_threshold=0.6,  # 最低相似度 0.6
    )

    print("\n✓ 進階 RAG 範例完成")


def example_rag_evaluation():
    """RAG 系統評估"""
    print("\n" + "=" * 60)
    print("範例 5: RAG 系統評估")
    print("=" * 60)

    embedder = MedicalEmbedder()
    retriever = MedicalRetriever(embedder=embedder)

    # 添加測試知識
    test_docs = [
        "高血壓的診斷標準是血壓持續 ≥ 140/90 mmHg。",
        "糖尿病的診斷標準是空腹血糖 ≥ 126 mg/dL。",
        "BMI = 體重(kg) / 身高(m)²，正常範圍 18.5-24。",
    ]
    retriever.add_documents(test_docs)

    # 測試查詢
    test_queries = [
        "什麼是高血壓？",
        "如何診斷糖尿病？",
        "BMI 怎麼計算？",
        "感冒怎麼辦？",  # 不相關查詢
    ]

    print("\n檢索質量測試:\n")
    for query in test_queries:
        results = retriever.retrieve(query, top_k=1)

        if results:
            top_result = results[0]
            print(f"查詢: {query}")
            print(f"最相關文檔 (分數: {top_result['score']:.3f}):")
            print(f"{top_result['text'][:100]}...")
            print()
        else:
            print(f"查詢: {query}")
            print("未找到相關文檔")
            print()

    print("\n評估指標:")
    print("1. 相似度分數 (越高越好，通常 > 0.5)")
    print("2. 檢索準確率 (是否檢索到相關文檔)")
    print("3. 檢索速度 (毫秒)")
    print("4. 記憶體使用量")

    print("\n✓ RAG 評估範例完成")


def example_multilingual_rag():
    """多語言 RAG"""
    print("\n" + "=" * 60)
    print("範例 6: 多語言醫療 RAG")
    print("=" * 60)

    # 使用多語言嵌入模型
    embedder = MedicalEmbedder(
        model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    )

    retriever = MedicalRetriever(embedder=embedder)

    # 添加多語言醫療知識
    multilingual_docs = [
        # 繁體中文
        "高血壓是血壓持續高於正常值的疾病。",
        # 簡體中文
        "糖尿病是一种代谢性疾病，特征是血糖过高。",
        # 英文
        "Hypertension is a condition where blood pressure is consistently high.",
        # 日文
        "糖尿病は血糖値が高い状態が続く病気です。",
    ]

    metadata = [
        {"language": "zh-TW", "topic": "hypertension"},
        {"language": "zh-CN", "topic": "diabetes"},
        {"language": "en", "topic": "hypertension"},
        {"language": "ja", "topic": "diabetes"},
    ]

    retriever.add_documents(multilingual_docs, metadata=metadata)

    # 測試跨語言檢索
    queries = [
        ("什麼是高血壓？", "zh-TW"),
        ("What is hypertension?", "en"),
        ("糖尿病是什麼？", "zh-TW"),
    ]

    print("\n跨語言檢索測試:\n")
    for query, lang in queries:
        results = retriever.retrieve(query, top_k=2)
        print(f"查詢 ({lang}): {query}")
        print(f"檢索結果:")
        for i, result in enumerate(results, 1):
            print(
                f"  {i}. [{result['metadata'].get('language', 'unknown')}] "
                f"{result['text'][:50]}... (分數: {result['score']:.3f})"
            )
        print()

    print("✓ 多語言 RAG 範例完成")


def example_rag_best_practices():
    """RAG 最佳實踐"""
    print("\n" + "=" * 60)
    print("範例 7: RAG 系統最佳實踐")
    print("=" * 60)

    print("\n最佳實踐建議:\n")

    print("1. 文檔分塊 (Chunking)")
    print("   - 塊大小: 256-512 tokens (醫療文本)")
    print("   - 重疊: 10-20% (保持上下文連貫)")
    print("   - 策略: 按段落、語義單元分塊")

    print("\n2. 嵌入模型選擇")
    print("   - 多語言: paraphrase-multilingual-*")
    print("   - 中文: BAAI/bge-large-zh-v1.5")
    print("   - 醫療: 使用醫療領域微調模型")

    print("\n3. 索引優化")
    print("   - < 10K 文檔: Flat 索引")
    print("   - 10K-1M: IVF 索引 (nlist=sqrt(N))")
    print("   - > 1M: HNSW 索引")

    print("\n4. 檢索參數")
    print("   - top_k: 3-5 個文檔")
    print("   - score_threshold: 0.5-0.7")
    print("   - 根據實際效果調整")

    print("\n5. 上下文整合")
    print("   - 排序: 按相似度排序")
    print("   - 去重: 移除重複內容")
    print("   - 限制: 控制總長度 (避免超過模型限制)")

    print("\n6. 評估和監控")
    print("   - 檢索質量: 相關性評分")
    print("   - 生成質量: 答案準確性")
    print("   - 性能: 檢索延遲、記憶體使用")

    print("\n7. 知識庫維護")
    print("   - 定期更新醫療知識")
    print("   - 版本控制")
    print("   - 備份和恢復")

    print("\n✓ 最佳實踐範例完成")


def main():
    """執行所有範例"""
    print("\n" + "=" * 60)
    print("RAG 系統完整使用指南")
    print("=" * 60)

    try:
        example_basic_rag()
        example_rag_with_generator()
        example_knowledge_base_management()
        example_advanced_rag()
        example_rag_evaluation()
        example_multilingual_rag()
        example_rag_best_practices()

        print("\n" + "=" * 60)
        print("所有 RAG 範例執行完成！")
        print("=" * 60)

        print("\n快速開始:")
        print("1. 初始化嵌入器和檢索器")
        print("2. 添加醫療知識文檔")
        print("3. 創建 RAG 生成器")
        print("4. 使用 RAG 增強的生成")

    except Exception as e:
        logger.error(f"執行範例時發生錯誤: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
