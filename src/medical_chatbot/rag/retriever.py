"""
醫療知識檢索器

整合嵌入和向量存儲，提供文檔檢索功能。
"""
from typing import List, Tuple, Dict, Any, Optional
from pathlib import Path
from loguru import logger

from .embedder import MedicalEmbedder
from .vector_store import MedicalVectorStore
from ..utils.exceptions import RetrievalException
from ..utils.error_handler import handle_errors


class MedicalRetriever:
    """醫療知識檢索器"""

    def __init__(
        self,
        embedder: Optional[MedicalEmbedder] = None,
        vector_store: Optional[MedicalVectorStore] = None,
        top_k: int = 5,
        score_threshold: float = 0.5,
    ):
        """
        初始化檢索器

        Args:
            embedder: 嵌入器實例
            vector_store: 向量存儲實例
            top_k: 默認返回的文檔數量
            score_threshold: 最低相似度閾值
        """
        self.embedder = embedder
        self.vector_store = vector_store
        self.top_k = top_k
        self.score_threshold = score_threshold

        # 如果未提供嵌入器，創建默認的
        if self.embedder is None:
            logger.info("創建默認嵌入器")
            self.embedder = MedicalEmbedder()

        # 如果未提供向量存儲，創建空的
        if self.vector_store is None:
            logger.info("創建空向量存儲")
            embedding_dim = self.embedder.get_embedding_dimension()
            self.vector_store = MedicalVectorStore(embedding_dim=embedding_dim)

        logger.info(
            f"檢索器初始化完成: top_k={top_k}, threshold={score_threshold}"
        )

    @handle_errors(default_message="添加文檔失敗", reraise=True)
    def add_documents(
        self,
        documents: List[str],
        metadata: Optional[List[Dict[str, Any]]] = None,
        batch_size: int = 32,
    ):
        """
        添加文檔到檢索系統

        Args:
            documents: 文檔列表
            metadata: 元數據列表
            batch_size: 嵌入批次大小
        """
        if not documents:
            raise RetrievalException("文檔列表不能為空")

        try:
            logger.info(f"添加 {len(documents)} 個文檔...")

            # 生成嵌入
            embeddings = self.embedder.embed_documents(documents)

            # 添加到向量存儲
            self.vector_store.add(
                embeddings=embeddings, documents=documents, metadata=metadata
            )

            logger.info(f"成功添加 {len(documents)} 個文檔")

        except Exception as e:
            logger.error(f"添加文檔失敗: {e}")
            raise RetrievalException(f"無法添加文檔: {str(e)}")

    @handle_errors(default_message="檢索文檔失敗", reraise=True)
    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        score_threshold: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        檢索相關文檔

        Args:
            query: 查詢文本
            top_k: 返回的文檔數量
            score_threshold: 最低相似度閾值

        Returns:
            文檔列表，每個文檔包含 text, score, metadata
        """
        if not query or not query.strip():
            raise RetrievalException("查詢不能為空")

        try:
            # 使用默認值
            top_k = top_k or self.top_k
            score_threshold = score_threshold or self.score_threshold

            # 生成查詢嵌入
            query_embedding = self.embedder.embed_query(query)

            # 搜索
            documents, scores, metadata = self.vector_store.search(
                query_embedding=query_embedding,
                k=top_k,
                score_threshold=score_threshold,
            )

            # 格式化結果
            results = []
            for doc, score, meta in zip(documents, scores, metadata):
                results.append({"text": doc, "score": float(score), "metadata": meta})

            logger.debug(f"檢索到 {len(results)} 個相關文檔")

            return results

        except Exception as e:
            logger.error(f"檢索失敗: {e}")
            raise RetrievalException(f"文檔檢索失敗: {str(e)}", query=query)

    def retrieve_context(
        self,
        query: str,
        top_k: Optional[int] = None,
        separator: str = "\n\n---\n\n",
    ) -> str:
        """
        檢索並組合上下文

        Args:
            query: 查詢文本
            top_k: 返回的文檔數量
            separator: 文檔分隔符

        Returns:
            組合的上下文文本
        """
        results = self.retrieve(query, top_k=top_k)

        if not results:
            logger.warning(f"未找到相關文檔: {query[:50]}")
            return ""

        # 組合文檔
        context_parts = []
        for i, result in enumerate(results, 1):
            doc_text = result["text"]
            score = result["score"]
            context_parts.append(f"[文檔 {i}, 相似度: {score:.3f}]\n{doc_text}")

        context = separator.join(context_parts)

        logger.info(f"組合上下文: {len(results)} 個文檔, {len(context)} 字符")

        return context

    def batch_retrieve(
        self,
        queries: List[str],
        top_k: Optional[int] = None,
    ) -> List[List[Dict[str, Any]]]:
        """
        批次檢索

        Args:
            queries: 查詢列表
            top_k: 每個查詢返回的文檔數量

        Returns:
            每個查詢的結果列表
        """
        results = []
        for query in queries:
            query_results = self.retrieve(query, top_k=top_k)
            results.append(query_results)

        return results

    def add_from_file(
        self, file_path: str, chunk_size: int = 512, overlap: int = 50
    ):
        """
        從文件添加文檔（分塊）

        Args:
            file_path: 文件路徑
            chunk_size: 分塊大小
            overlap: 重疊大小
        """
        try:
            file_path = Path(file_path)

            if not file_path.exists():
                raise RetrievalException(f"文件不存在: {file_path}")

            # 讀取文件
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # 分塊
            chunks = self._chunk_text(content, chunk_size, overlap)

            # 生成元數據
            metadata = [
                {"source": str(file_path), "chunk_id": i} for i in range(len(chunks))
            ]

            # 添加文檔
            self.add_documents(chunks, metadata)

            logger.info(f"從文件添加 {len(chunks)} 個文檔塊: {file_path}")

        except Exception as e:
            logger.error(f"從文件添加文檔失敗: {e}")
            raise RetrievalException(f"無法從文件添加文檔: {str(e)}")

    def add_from_directory(
        self,
        directory: str,
        file_pattern: str = "*.txt",
        chunk_size: int = 512,
        overlap: int = 50,
    ):
        """
        從目錄批次添加文檔

        Args:
            directory: 目錄路徑
            file_pattern: 文件匹配模式
            chunk_size: 分塊大小
            overlap: 重疊大小
        """
        try:
            directory = Path(directory)

            if not directory.exists():
                raise RetrievalException(f"目錄不存在: {directory}")

            # 獲取所有匹配的文件
            files = list(directory.glob(file_pattern))

            if not files:
                logger.warning(f"未找到匹配的文件: {file_pattern}")
                return

            logger.info(f"從目錄添加 {len(files)} 個文件...")

            # 批次添加
            for file_path in files:
                self.add_from_file(file_path, chunk_size, overlap)

            logger.info(f"成功從目錄添加所有文件")

        except Exception as e:
            logger.error(f"從目錄添加文檔失敗: {e}")
            raise RetrievalException(f"無法從目錄添加文檔: {str(e)}")

    @staticmethod
    def _chunk_text(text: str, chunk_size: int, overlap: int) -> List[str]:
        """
        將文本分塊

        Args:
            text: 原始文本
            chunk_size: 分塊大小
            overlap: 重疊大小

        Returns:
            文本塊列表
        """
        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]

            # 避免在單詞中間切割
            if end < len(text):
                # 尋找最後一個空格
                last_space = chunk.rfind(" ")
                if last_space > 0:
                    chunk = chunk[:last_space]
                    end = start + last_space

            chunks.append(chunk.strip())
            start = end - overlap

        return [c for c in chunks if c]  # 過濾空塊

    def save(self, save_path: str):
        """
        保存檢索器

        Args:
            save_path: 保存路徑
        """
        try:
            # 保存向量存儲
            self.vector_store.save(save_path)
            logger.info(f"檢索器已保存到: {save_path}")

        except Exception as e:
            logger.error(f"保存檢索器失敗: {e}")
            raise RetrievalException(f"保存失敗: {str(e)}")

    @classmethod
    def load(
        cls,
        load_path: str,
        embedder: Optional[MedicalEmbedder] = None,
        top_k: int = 5,
        score_threshold: float = 0.5,
    ) -> "MedicalRetriever":
        """
        載入檢索器

        Args:
            load_path: 載入路徑
            embedder: 嵌入器實例
            top_k: 默認返回文檔數量
            score_threshold: 相似度閾值

        Returns:
            MedicalRetriever 實例
        """
        try:
            # 載入向量存儲
            vector_store = MedicalVectorStore.load(load_path)

            # 創建檢索器
            retriever = cls(
                embedder=embedder,
                vector_store=vector_store,
                top_k=top_k,
                score_threshold=score_threshold,
            )

            logger.info(f"檢索器已載入: {len(vector_store)} 個文檔")

            return retriever

        except Exception as e:
            logger.error(f"載入檢索器失敗: {e}")
            raise RetrievalException(f"載入失敗: {str(e)}")

    def clear(self):
        """清空檢索器"""
        self.vector_store.clear()
        logger.info("檢索器已清空")

    def get_stats(self) -> Dict[str, Any]:
        """獲取統計信息"""
        stats = self.vector_store.get_stats()
        stats["top_k"] = self.top_k
        stats["score_threshold"] = self.score_threshold
        return stats
