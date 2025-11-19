"""
醫療知識向量存儲

使用 FAISS 實現高效的向量檢索。
"""
from typing import List, Tuple, Optional, Dict, Any
import numpy as np
import pickle
from pathlib import Path
import faiss
from loguru import logger

from ..utils.exceptions import VectorStoreException
from ..utils.error_handler import handle_errors


class MedicalVectorStore:
    """醫療知識向量存儲"""

    def __init__(
        self,
        embedding_dim: int,
        index_type: str = "IVF",
        nlist: int = 100,
        metric: str = "cosine",
    ):
        """
        初始化向量存儲

        Args:
            embedding_dim: 嵌入向量維度
            index_type: 索引類型 (Flat/IVF/HNSW)
            nlist: IVF 索引的聚類數量
            metric: 距離度量 (cosine/l2/ip)
        """
        self.embedding_dim = embedding_dim
        self.index_type = index_type
        self.nlist = nlist
        self.metric = metric

        # 初始化索引
        self.index = None
        self._init_index()

        # 儲存文檔
        self.documents: List[str] = []
        self.metadata: List[Dict[str, Any]] = []

        logger.info(
            f"初始化向量存儲: dim={embedding_dim}, type={index_type}, metric={metric}"
        )

    def _init_index(self):
        """初始化 FAISS 索引"""
        try:
            if self.metric == "cosine":
                # 餘弦相似度 = 內積 (歸一化向量)
                # 使用 IndexFlatIP
                quantizer = faiss.IndexFlatIP(self.embedding_dim)
                metric_type = faiss.METRIC_INNER_PRODUCT
            elif self.metric == "l2":
                quantizer = faiss.IndexFlatL2(self.embedding_dim)
                metric_type = faiss.METRIC_L2
            elif self.metric == "ip":
                quantizer = faiss.IndexFlatIP(self.embedding_dim)
                metric_type = faiss.METRIC_INNER_PRODUCT
            else:
                raise VectorStoreException(f"不支援的度量類型: {self.metric}")

            # 根據索引類型創建索引
            if self.index_type == "Flat":
                self.index = quantizer

            elif self.index_type == "IVF":
                self.index = faiss.IndexIVFFlat(
                    quantizer, self.embedding_dim, self.nlist, metric_type
                )
                self.is_trained = False

            elif self.index_type == "HNSW":
                self.index = faiss.IndexHNSWFlat(self.embedding_dim, 32, metric_type)

            else:
                raise VectorStoreException(f"不支援的索引類型: {self.index_type}")

            logger.info(f"FAISS 索引初始化完成: {self.index_type}")

        except Exception as e:
            logger.error(f"初始化 FAISS 索引失敗: {e}")
            raise VectorStoreException(f"無法初始化向量索引: {str(e)}")

    @handle_errors(default_message="添加向量失敗", reraise=True)
    def add(
        self,
        embeddings: np.ndarray,
        documents: List[str],
        metadata: Optional[List[Dict[str, Any]]] = None,
    ):
        """
        添加向量到存儲

        Args:
            embeddings: 嵌入向量矩陣 (shape: [n, embedding_dim])
            documents: 對應的文檔列表
            metadata: 可選的元數據列表
        """
        if embeddings.shape[0] != len(documents):
            raise VectorStoreException("嵌入向量數量與文檔數量不匹配")

        if embeddings.shape[1] != self.embedding_dim:
            raise VectorStoreException(
                f"嵌入維度不匹配: 期望 {self.embedding_dim}, 實際 {embeddings.shape[1]}"
            )

        try:
            # 歸一化 (如果使用餘弦相似度)
            if self.metric == "cosine":
                embeddings = embeddings / np.linalg.norm(
                    embeddings, axis=1, keepdims=True
                )

            # 轉換為 float32
            embeddings = embeddings.astype(np.float32)

            # 訓練索引 (IVF)
            if self.index_type == "IVF" and not self.is_trained:
                if len(self.documents) + len(documents) >= self.nlist:
                    logger.info(f"訓練 IVF 索引...")
                    self.index.train(embeddings)
                    self.is_trained = True

            # 添加到索引
            if self.index_type == "IVF":
                if self.is_trained:
                    self.index.add(embeddings)
                else:
                    logger.warning("IVF 索引尚未訓練，跳過添加")
                    return
            else:
                self.index.add(embeddings)

            # 儲存文檔和元數據
            self.documents.extend(documents)

            if metadata is None:
                metadata = [{} for _ in range(len(documents))]
            self.metadata.extend(metadata)

            logger.info(f"添加 {len(documents)} 個文檔到向量存儲")

        except Exception as e:
            logger.error(f"添加向量失敗: {e}")
            raise VectorStoreException(f"添加向量到存儲失敗: {str(e)}")

    @handle_errors(default_message="搜索向量失敗", reraise=True)
    def search(
        self,
        query_embedding: np.ndarray,
        k: int = 5,
        score_threshold: Optional[float] = None,
    ) -> Tuple[List[str], List[float], List[Dict[str, Any]]]:
        """
        搜索相似向量

        Args:
            query_embedding: 查詢嵌入向量
            k: 返回的結果數量
            score_threshold: 最低分數閾值

        Returns:
            (文檔列表, 分數列表, 元數據列表)
        """
        if self.index.ntotal == 0:
            logger.warning("向量存儲為空")
            return [], [], []

        try:
            # 歸一化
            if self.metric == "cosine":
                query_embedding = query_embedding / np.linalg.norm(query_embedding)

            # 轉換為 float32 並調整形狀
            query_embedding = query_embedding.astype(np.float32).reshape(1, -1)

            # 搜索
            scores, indices = self.index.search(query_embedding, k)

            # 處理結果
            scores = scores[0]
            indices = indices[0]

            # 過濾有效結果
            valid_mask = indices >= 0
            scores = scores[valid_mask]
            indices = indices[valid_mask]

            # 應用分數閾值
            if score_threshold is not None:
                threshold_mask = scores >= score_threshold
                scores = scores[threshold_mask]
                indices = indices[threshold_mask]

            # 獲取文檔和元數據
            results_docs = [self.documents[i] for i in indices]
            results_metadata = [self.metadata[i] for i in indices]
            results_scores = scores.tolist()

            logger.debug(f"搜索返回 {len(results_docs)} 個結果")

            return results_docs, results_scores, results_metadata

        except Exception as e:
            logger.error(f"搜索失敗: {e}")
            raise VectorStoreException(f"向量搜索失敗: {str(e)}")

    def save(self, save_path: str):
        """
        保存向量存儲到文件

        Args:
            save_path: 保存路徑
        """
        try:
            save_path = Path(save_path)
            save_path.parent.mkdir(parents=True, exist_ok=True)

            # 保存 FAISS 索引
            index_path = save_path.with_suffix(".faiss")
            faiss.write_index(self.index, str(index_path))

            # 保存文檔和元數據
            data_path = save_path.with_suffix(".pkl")
            data = {
                "documents": self.documents,
                "metadata": self.metadata,
                "embedding_dim": self.embedding_dim,
                "index_type": self.index_type,
                "metric": self.metric,
                "nlist": self.nlist,
            }

            with open(data_path, "wb") as f:
                pickle.dump(data, f)

            logger.info(f"向量存儲已保存到: {save_path}")

        except Exception as e:
            logger.error(f"保存向量存儲失敗: {e}")
            raise VectorStoreException(f"保存失敗: {str(e)}")

    @classmethod
    def load(cls, load_path: str) -> "MedicalVectorStore":
        """
        從文件載入向量存儲

        Args:
            load_path: 載入路徑

        Returns:
            MedicalVectorStore 實例
        """
        try:
            load_path = Path(load_path)

            # 載入文檔和元數據
            data_path = load_path.with_suffix(".pkl")
            with open(data_path, "rb") as f:
                data = pickle.load(f)

            # 創建實例
            store = cls(
                embedding_dim=data["embedding_dim"],
                index_type=data["index_type"],
                nlist=data["nlist"],
                metric=data["metric"],
            )

            # 載入 FAISS 索引
            index_path = load_path.with_suffix(".faiss")
            store.index = faiss.read_index(str(index_path))

            # 載入文檔和元數據
            store.documents = data["documents"]
            store.metadata = data["metadata"]

            logger.info(f"向量存儲已載入: {len(store.documents)} 個文檔")

            return store

        except Exception as e:
            logger.error(f"載入向量存儲失敗: {e}")
            raise VectorStoreException(f"載入失敗: {str(e)}")

    def clear(self):
        """清空向量存儲"""
        self._init_index()
        self.documents = []
        self.metadata = []
        logger.info("向量存儲已清空")

    def __len__(self) -> int:
        """返回存儲的文檔數量"""
        return len(self.documents)

    def get_stats(self) -> Dict[str, Any]:
        """獲取統計信息"""
        return {
            "num_documents": len(self.documents),
            "embedding_dim": self.embedding_dim,
            "index_type": self.index_type,
            "metric": self.metric,
            "index_size": self.index.ntotal if self.index else 0,
        }
