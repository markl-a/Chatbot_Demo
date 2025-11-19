"""
RAG 生成器

整合檢索和生成，提供檢索增強的回應生成。
"""
from typing import Optional, List, Dict, Any
from loguru import logger

from .retriever import MedicalRetriever
from ..inference.generator import Generator
from ..utils.exceptions import ModelInferenceException


class RAGGenerator:
    """RAG 生成器"""

    def __init__(
        self,
        generator: Generator,
        retriever: MedicalRetriever,
        use_context: bool = True,
        context_template: str = "參考以下醫療知識：\n\n{context}\n\n根據上述知識，回答問題：{query}",
        max_context_docs: int = 3,
    ):
        """
        初始化 RAG 生成器

        Args:
            generator: 語言模型生成器
            retriever: 文檔檢索器
            use_context: 是否使用檢索的上下文
            context_template: 上下文模板
            max_context_docs: 最大上下文文檔數量
        """
        self.generator = generator
        self.retriever = retriever
        self.use_context = use_context
        self.context_template = context_template
        self.max_context_docs = max_context_docs

        logger.info(
            f"RAG 生成器初始化: use_context={use_context}, max_docs={max_context_docs}"
        )

    def generate(
        self,
        query: str,
        use_rag: bool = True,
        max_context_docs: Optional[int] = None,
        **generation_kwargs,
    ) -> Dict[str, Any]:
        """
        生成回應

        Args:
            query: 用戶查詢
            use_rag: 是否使用 RAG
            max_context_docs: 上下文文檔數量
            **generation_kwargs: 生成參數

        Returns:
            包含回應和元數據的字典
        """
        try:
            retrieved_docs = []
            context = ""

            # 檢索相關文檔
            if use_rag and self.use_context:
                max_docs = max_context_docs or self.max_context_docs

                retrieved_docs = self.retriever.retrieve(query, top_k=max_docs)

                if retrieved_docs:
                    # 組合上下文
                    context_parts = []
                    for i, doc in enumerate(retrieved_docs, 1):
                        doc_text = doc["text"]
                        score = doc["score"]
                        context_parts.append(
                            f"參考資料 {i} (相關度: {score:.2f}):\n{doc_text}"
                        )

                    context = "\n\n".join(context_parts)

                    # 構建帶上下文的提示
                    prompt = self.context_template.format(
                        context=context, query=query
                    )

                    logger.info(
                        f"使用 {len(retrieved_docs)} 個檢索文檔生成回應"
                    )
                else:
                    # 沒有找到相關文檔，使用原始查詢
                    prompt = query
                    logger.warning("未找到相關文檔，使用原始查詢")
            else:
                # 不使用 RAG
                prompt = query

            # 生成回應
            response = self.generator.generate(prompt, **generation_kwargs)

            # 返回結果
            result = {
                "query": query,
                "response": response,
                "retrieved_docs": retrieved_docs,
                "context_used": bool(context),
                "num_docs": len(retrieved_docs),
            }

            return result

        except Exception as e:
            logger.error(f"RAG 生成失敗: {e}")
            raise ModelInferenceException(f"RAG 生成失敗: {str(e)}")

    def generate_conversation(
        self,
        messages: List[Dict[str, str]],
        use_rag: bool = True,
        **generation_kwargs,
    ) -> Dict[str, Any]:
        """
        多輪對話生成

        Args:
            messages: 對話歷史
            use_rag: 是否使用 RAG
            **generation_kwargs: 生成參數

        Returns:
            包含回應和元數據的字典
        """
        try:
            # 獲取最後一個用戶消息
            last_user_message = ""
            for msg in reversed(messages):
                if msg.get("role") == "user":
                    last_user_message = msg.get("content", "")
                    break

            if not last_user_message:
                raise ModelInferenceException("未找到用戶消息")

            retrieved_docs = []
            context = ""

            # 檢索相關文檔
            if use_rag and self.use_context:
                retrieved_docs = self.retriever.retrieve(
                    last_user_message, top_k=self.max_context_docs
                )

                if retrieved_docs:
                    # 組合上下文
                    context_parts = []
                    for doc in retrieved_docs:
                        context_parts.append(doc["text"])

                    context = "\n\n---\n\n".join(context_parts)

                    # 將上下文添加到對話歷史
                    context_message = {
                        "role": "system",
                        "content": f"參考以下醫療知識：\n\n{context}",
                    }

                    # 插入上下文到倒數第二個位置（最後一個用戶消息之前）
                    messages_with_context = messages[:-1] + [
                        context_message,
                        messages[-1],
                    ]

                    logger.info(
                        f"對話中使用 {len(retrieved_docs)} 個檢索文檔"
                    )
                else:
                    messages_with_context = messages
            else:
                messages_with_context = messages

            # 生成回應
            response = self.generator.generate_conversation(
                messages_with_context, **generation_kwargs
            )

            # 返回結果
            result = {
                "messages": messages,
                "response": response,
                "retrieved_docs": retrieved_docs,
                "context_used": bool(context),
                "num_docs": len(retrieved_docs),
            }

            return result

        except Exception as e:
            logger.error(f"RAG 對話生成失敗: {e}")
            raise ModelInferenceException(f"RAG 對話生成失敗: {str(e)}")

    def add_knowledge(
        self, documents: List[str], metadata: Optional[List[Dict[str, Any]]] = None
    ):
        """
        添加知識到檢索系統

        Args:
            documents: 文檔列表
            metadata: 元數據列表
        """
        self.retriever.add_documents(documents, metadata)
        logger.info(f"添加 {len(documents)} 個知識文檔到 RAG 系統")

    def add_knowledge_from_file(self, file_path: str, chunk_size: int = 512):
        """
        從文件添加知識

        Args:
            file_path: 文件路徑
            chunk_size: 分塊大小
        """
        self.retriever.add_from_file(file_path, chunk_size=chunk_size)
        logger.info(f"從文件添加知識: {file_path}")

    def add_knowledge_from_directory(
        self, directory: str, file_pattern: str = "*.txt", chunk_size: int = 512
    ):
        """
        從目錄批次添加知識

        Args:
            directory: 目錄路徑
            file_pattern: 文件匹配模式
            chunk_size: 分塊大小
        """
        self.retriever.add_from_directory(
            directory, file_pattern=file_pattern, chunk_size=chunk_size
        )
        logger.info(f"從目錄添加知識: {directory}")

    def save_knowledge_base(self, save_path: str):
        """
        保存知識庫

        Args:
            save_path: 保存路徑
        """
        self.retriever.save(save_path)
        logger.info(f"知識庫已保存: {save_path}")

    def load_knowledge_base(self, load_path: str):
        """
        載入知識庫

        Args:
            load_path: 載入路徑
        """
        # 重新載入檢索器
        self.retriever = MedicalRetriever.load(
            load_path,
            embedder=self.retriever.embedder,
            top_k=self.max_context_docs,
        )
        logger.info(f"知識庫已載入: {load_path}")

    def get_stats(self) -> Dict[str, Any]:
        """獲取統計信息"""
        retriever_stats = self.retriever.get_stats()

        stats = {
            "use_context": self.use_context,
            "max_context_docs": self.max_context_docs,
            "retriever": retriever_stats,
        }

        return stats

    def toggle_rag(self, enabled: bool):
        """
        切換 RAG 功能

        Args:
            enabled: 是否啟用
        """
        self.use_context = enabled
        logger.info(f"RAG 功能已{'啟用' if enabled else '禁用'}")
