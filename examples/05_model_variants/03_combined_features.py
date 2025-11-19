"""
範例：組合功能使用

展示如何組合使用 RAG、安全過濾、錯誤處理等多種功能。
"""
from pathlib import Path
import sys
import time
from typing import Dict, Any

# 添加專案路徑
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from medical_chatbot.rag import MedicalEmbedder, MedicalRetriever, RAGGenerator
from medical_chatbot.utils.safety import SafetyFilter
from medical_chatbot.utils.logger import setup_logger
from medical_chatbot.utils.error_handler import handle_errors, ErrorContext
from medical_chatbot.utils.exceptions import (
    ModelInferenceException,
    UnsafeContentException,
)

logger = setup_logger()


def example_rag_with_safety():
    """RAG + 安全過濾"""
    print("\n" + "=" * 60)
    print("範例 1: RAG + 安全過濾")
    print("=" * 60)

    # 初始化組件
    embedder = MedicalEmbedder()
    retriever = MedicalRetriever(embedder=embedder, top_k=3)
    safety_filter = SafetyFilter()

    # 添加醫療知識
    medical_knowledge = [
        "高血壓患者應定期測量血壓，遵醫囑服藥。",
        "糖尿病患者需要控制飲食，監測血糖。",
        "緊急情況下（如胸痛、呼吸困難）請立即撥打 119。",
    ]
    retriever.add_documents(medical_knowledge)

    # 測試查詢
    test_queries = [
        "如何控制高血壓？",  # 正常查詢
        "我胸口很痛怎麼辦？",  # 緊急情況
        "<script>alert('test')</script>",  # XSS 攻擊
    ]

    print("\n安全檢查 + RAG 檢索:\n")

    for query in test_queries:
        print(f"原始查詢: {query}")

        # 1. 安全檢查
        sanitized = safety_filter.sanitize_input(query)
        is_safe = safety_filter.is_safe(query)
        is_emergency = safety_filter.is_emergency(query)

        print(f"  消毒後: {sanitized}")
        print(f"  安全性: {'✓' if is_safe else '✗'}")
        print(f"  緊急: {'⚠️ 是' if is_emergency else '否'}")

        # 2. 如果安全，進行 RAG 檢索
        if is_safe and not is_emergency:
            results = retriever.retrieve(sanitized, top_k=2)
            print(f"  檢索結果: {len(results)} 個相關文檔")

            if results:
                top_result = results[0]
                print(f"  最相關: {top_result['text'][:50]}...")
        elif is_emergency:
            print(f"  ⚠️ 檢測到緊急情況，建議立即就醫或撥打 119")
        else:
            print(f"  ⚠️ 不安全的輸入，已拒絕處理")

        print()

    print("✓ RAG + 安全過濾範例完成")


def example_rag_with_cache():
    """RAG + 快取機制"""
    print("\n" + "=" * 60)
    print("範例 2: RAG + 快取機制")
    print("=" * 60)

    class SimpleCache:
        """簡單的記憶體快取"""

        def __init__(self):
            self.cache: Dict[str, Any] = {}
            self.hits = 0
            self.misses = 0

        def get(self, key: str) -> Any:
            if key in self.cache:
                self.hits += 1
                return self.cache[key]
            self.misses += 1
            return None

        def set(self, key: str, value: Any):
            self.cache[key] = value

        def get_stats(self):
            total = self.hits + self.misses
            hit_rate = self.hits / total if total > 0 else 0
            return {
                "hits": self.hits,
                "misses": self.misses,
                "hit_rate": f"{hit_rate:.2%}",
            }

    # 初始化組件
    embedder = MedicalEmbedder()
    retriever = MedicalRetriever(embedder=embedder)
    cache = SimpleCache()

    # 添加知識
    docs = ["高血壓定義...", "糖尿病症狀...", "心臟病預防..."]
    retriever.add_documents(docs)

    # 測試查詢（包含重複）
    queries = [
        "什麼是高血壓？",
        "糖尿病有什麼症狀？",
        "什麼是高血壓？",  # 重複
        "如何預防心臟病？",
        "什麼是高血壓？",  # 重複
    ]

    print("\n帶快取的 RAG 檢索:\n")

    for i, query in enumerate(queries, 1):
        print(f"查詢 {i}: {query}")

        # 檢查快取
        cache_key = f"rag:{query}"
        cached_result = cache.get(cache_key)

        if cached_result:
            print(f"  ✓ 從快取獲取 (耗時: 0ms)")
            results = cached_result
        else:
            print(f"  ⊗ 快取未命中，執行 RAG 檢索...")
            start_time = time.time()
            results = retriever.retrieve(query, top_k=1)
            elapsed = (time.time() - start_time) * 1000
            print(f"  ✓ 檢索完成 (耗時: {elapsed:.1f}ms)")

            # 存入快取
            cache.set(cache_key, results)

        print()

    # 顯示快取統計
    stats = cache.get_stats()
    print(f"快取統計:")
    print(f"  命中: {stats['hits']} 次")
    print(f"  未命中: {stats['misses']} 次")
    print(f"  命中率: {stats['hit_rate']}")

    print("\n✓ RAG + 快取範例完成")


def example_rag_with_error_handling():
    """RAG + 錯誤處理"""
    print("\n" + "=" * 60)
    print("範例 3: RAG + 錯誤處理")
    print("=" * 60)

    @handle_errors(default_message="RAG 檢索失敗", reraise=False)
    def safe_retrieve(retriever, query):
        """帶錯誤處理的檢索"""
        if not query or len(query.strip()) == 0:
            raise ValueError("查詢不能為空")

        return retriever.retrieve(query, top_k=3)

    # 初始化
    embedder = MedicalEmbedder()
    retriever = MedicalRetriever(embedder=embedder)

    # 添加文檔
    retriever.add_documents(["文檔 1", "文檔 2", "文檔 3"])

    # 測試查詢（包含錯誤）
    test_cases = [
        ("正常查詢", "什麼是高血壓？"),
        ("空查詢", ""),
        ("None 查詢", None),
        ("超長查詢", "查詢" * 1000),
    ]

    print("\n帶錯誤處理的 RAG 檢索:\n")

    for name, query in test_cases:
        print(f"測試: {name}")
        print(f"  查詢: {str(query)[:50]}{'...' if query and len(str(query)) > 50 else ''}")

        # 使用錯誤上下文
        with ErrorContext(operation=f"RAG 檢索 - {name}", reraise=False):
            results = safe_retrieve(retriever, query)

            if results:
                print(f"  ✓ 成功: 檢索到 {len(results)} 個結果")
            else:
                print(f"  ✗ 失敗: 無結果或發生錯誤")

        print()

    print("✓ RAG + 錯誤處理範例完成")


def example_rag_with_monitoring():
    """RAG + 監控"""
    print("\n" + "=" * 60)
    print("範例 4: RAG + 性能監控")
    print("=" * 60)

    class RAGMonitor:
        """RAG 性能監控"""

        def __init__(self):
            self.metrics = {
                "total_queries": 0,
                "successful_queries": 0,
                "failed_queries": 0,
                "total_latency": 0,
                "avg_similarity_score": 0,
            }

        def record_query(
            self, success: bool, latency: float, avg_score: float = 0
        ):
            """記錄查詢指標"""
            self.metrics["total_queries"] += 1

            if success:
                self.metrics["successful_queries"] += 1
                self.metrics["total_latency"] += latency
                self.metrics["avg_similarity_score"] += avg_score
            else:
                self.metrics["failed_queries"] += 1

        def get_metrics(self):
            """獲取指標"""
            total = self.metrics["total_queries"]
            successful = self.metrics["successful_queries"]

            return {
                "total_queries": total,
                "successful_queries": successful,
                "failed_queries": self.metrics["failed_queries"],
                "success_rate": f"{successful/total:.2%}" if total > 0 else "0%",
                "avg_latency": f"{self.metrics['total_latency']/successful:.2f}ms"
                if successful > 0
                else "N/A",
                "avg_similarity": f"{self.metrics['avg_similarity_score']/successful:.3f}"
                if successful > 0
                else "N/A",
            }

    # 初始化
    embedder = MedicalEmbedder()
    retriever = MedicalRetriever(embedder=embedder)
    monitor = RAGMonitor()

    # 添加文檔
    docs = [f"醫療文檔 {i}" for i in range(10)]
    retriever.add_documents(docs)

    # 模擬查詢
    queries = [
        "查詢 1",
        "查詢 2",
        "",  # 會失敗
        "查詢 3",
        "查詢 4",
    ]

    print("\n監控 RAG 性能:\n")

    for query in queries:
        try:
            start_time = time.time()

            if query:
                results = retriever.retrieve(query, top_k=3)
                latency = (time.time() - start_time) * 1000

                avg_score = (
                    sum(r["score"] for r in results) / len(results)
                    if results
                    else 0
                )

                monitor.record_query(success=True, latency=latency, avg_score=avg_score)
                print(f"✓ {query}: {len(results)} 結果, {latency:.1f}ms")
            else:
                monitor.record_query(success=False, latency=0)
                print(f"✗ 空查詢失敗")

        except Exception as e:
            monitor.record_query(success=False, latency=0)
            print(f"✗ 錯誤: {e}")

    # 顯示監控指標
    metrics = monitor.get_metrics()
    print(f"\n性能指標:")
    print(f"  總查詢: {metrics['total_queries']}")
    print(f"  成功: {metrics['successful_queries']}")
    print(f"  失敗: {metrics['failed_queries']}")
    print(f"  成功率: {metrics['success_rate']}")
    print(f"  平均延遲: {metrics['avg_latency']}")
    print(f"  平均相似度: {metrics['avg_similarity']}")

    print("\n✓ RAG + 監控範例完成")


def example_multi_model_rag():
    """多模型 RAG"""
    print("\n" + "=" * 60)
    print("範例 5: 多模型 RAG 系統")
    print("=" * 60)

    class MultiModelRAG:
        """多模型 RAG 系統"""

        def __init__(self):
            self.models = {}
            self.retrievers = {}

        def add_model(self, name: str, model_config: dict):
            """添加模型配置"""
            self.models[name] = model_config

            # 為每個模型創建獨立的檢索器
            embedder = MedicalEmbedder()
            self.retrievers[name] = MedicalRetriever(embedder=embedder)

        def retrieve(self, model_name: str, query: str, top_k: int = 3):
            """使用指定模型檢索"""
            if model_name not in self.retrievers:
                raise ValueError(f"模型 {model_name} 不存在")

            return self.retrievers[model_name].retrieve(query, top_k=top_k)

        def add_knowledge(self, model_name: str, docs: list):
            """為指定模型添加知識"""
            if model_name not in self.retrievers:
                raise ValueError(f"模型 {model_name} 不存在")

            self.retrievers[model_name].add_documents(docs)

    # 創建多模型系統
    multi_rag = MultiModelRAG()

    # 添加不同的模型配置
    multi_rag.add_model(
        "taide",
        {"model": "taide/Llama3-TAIDE-LX-8B-Chat-Alpha1", "lang": "zh-TW"},
    )

    multi_rag.add_model(
        "breeze", {"model": "MediaTek-Research/Breeze-7B-Instruct-v1_0", "lang": "zh-TW"}
    )

    multi_rag.add_model("qwen", {"model": "Qwen/Qwen-7B-Chat", "lang": "zh"})

    # 為不同模型添加專門的知識
    multi_rag.add_knowledge("taide", ["台灣醫療體系相關知識..."])
    multi_rag.add_knowledge("breeze", ["繁體中文醫療知識..."])
    multi_rag.add_knowledge("qwen", ["通用醫療知識..."])

    # 測試不同模型
    query = "高血壓治療"
    print(f"\n查詢: {query}\n")

    for model_name in ["taide", "breeze", "qwen"]:
        print(f"使用 {model_name} 模型:")
        results = multi_rag.retrieve(model_name, query, top_k=1)

        if results:
            print(f"  檢索到 {len(results)} 個結果")
            print(f"  最佳匹配: {results[0]['text'][:50]}...")
        print()

    print("✓ 多模型 RAG 範例完成")


def example_rag_pipeline():
    """完整 RAG 流水線"""
    print("\n" + "=" * 60)
    print("範例 6: 完整 RAG 流水線")
    print("=" * 60)

    class RAGPipeline:
        """完整的 RAG 處理流水線"""

        def __init__(self):
            self.embedder = MedicalEmbedder()
            self.retriever = MedicalRetriever(embedder=self.embedder)
            self.safety_filter = SafetyFilter()
            self.cache = {}

        def process_query(self, query: str) -> Dict[str, Any]:
            """處理查詢的完整流水線"""
            result = {
                "original_query": query,
                "sanitized_query": None,
                "is_safe": False,
                "is_emergency": False,
                "cached": False,
                "retrieved_docs": [],
                "response": None,
                "error": None,
            }

            try:
                # 1. 安全檢查和消毒
                sanitized = self.safety_filter.sanitize_input(query)
                result["sanitized_query"] = sanitized
                result["is_safe"] = self.safety_filter.is_safe(sanitized)
                result["is_emergency"] = self.safety_filter.is_emergency(sanitized)

                if not result["is_safe"]:
                    result["error"] = "不安全的輸入"
                    return result

                if result["is_emergency"]:
                    result[
                        "response"
                    ] = "⚠️ 檢測到緊急情況，請立即就醫或撥打 119！"
                    return result

                # 2. 檢查快取
                cache_key = f"query:{sanitized}"
                if cache_key in self.cache:
                    result["cached"] = True
                    result["retrieved_docs"] = self.cache[cache_key]
                else:
                    # 3. RAG 檢索
                    docs = self.retriever.retrieve(sanitized, top_k=3)
                    result["retrieved_docs"] = docs
                    self.cache[cache_key] = docs

                # 4. 生成回應（這裡簡化為摘要）
                if result["retrieved_docs"]:
                    result["response"] = f"基於 {len(result['retrieved_docs'])} 個文檔的回答..."
                else:
                    result["response"] = "未找到相關資訊"

            except Exception as e:
                result["error"] = str(e)
                logger.error(f"RAG 流水線錯誤: {e}")

            return result

    # 創建流水線
    pipeline = RAGPipeline()

    # 添加知識
    pipeline.retriever.add_documents(
        [
            "高血壓相關知識...",
            "糖尿病相關知識...",
            "心臟病相關知識...",
        ]
    )

    # 測試流水線
    test_queries = [
        "什麼是高血壓？",
        "什麼是高血壓？",  # 測試快取
        "我胸口很痛",  # 緊急情況
        "<script>alert()</script>",  # 不安全
    ]

    print("\n完整 RAG 流水線處理:\n")

    for query in test_queries:
        print(f"查詢: {query}")
        result = pipeline.process_query(query)

        print(f"  安全: {'✓' if result['is_safe'] else '✗'}")
        print(f"  緊急: {'⚠️' if result['is_emergency'] else '否'}")
        print(f"  快取: {'✓' if result['cached'] else '✗'}")
        print(f"  檢索文檔: {len(result['retrieved_docs'])}")
        print(f"  回應: {result['response']}")
        if result["error"]:
            print(f"  錯誤: {result['error']}")
        print()

    print("✓ 完整 RAG 流水線範例完成")


def main():
    """執行所有範例"""
    print("\n" + "=" * 60)
    print("組合功能使用範例")
    print("=" * 60)

    try:
        example_rag_with_safety()
        example_rag_with_cache()
        example_rag_with_error_handling()
        example_rag_with_monitoring()
        example_multi_model_rag()
        example_rag_pipeline()

        print("\n" + "=" * 60)
        print("所有組合功能範例執行完成！")
        print("=" * 60)

        print("\n關鍵要點:")
        print("1. RAG + 安全過濾 = 安全可靠的知識檢索")
        print("2. RAG + 快取 = 提升性能和響應速度")
        print("3. RAG + 錯誤處理 = 穩定的生產系統")
        print("4. RAG + 監控 = 可觀測的系統運行")
        print("5. 多模型 RAG = 靈活的模型選擇")
        print("6. 完整流水線 = 企業級解決方案")

    except Exception as e:
        logger.error(f"執行範例時發生錯誤: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
