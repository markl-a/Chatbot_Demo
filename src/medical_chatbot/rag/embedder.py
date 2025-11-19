"""
醫療文本嵌入器

使用預訓練模型生成文本的向量嵌入。
"""
from typing import List, Union, Optional
import torch
import numpy as np
from transformers import AutoModel, AutoTokenizer
from loguru import logger

from ..utils.exceptions import EmbeddingException
from ..utils.error_handler import handle_errors


class MedicalEmbedder:
    """醫療文本嵌入器"""

    def __init__(
        self,
        model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        device: Optional[str] = None,
        max_length: int = 512,
        normalize: bool = True,
    ):
        """
        初始化嵌入器

        Args:
            model_name: 嵌入模型名稱
            device: 設備 (cuda/cpu/auto)
            max_length: 最大序列長度
            normalize: 是否歸一化向量
        """
        self.model_name = model_name
        self.max_length = max_length
        self.normalize = normalize

        # 確定設備
        if device == "auto" or device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

        logger.info(f"初始化嵌入器: {model_name} on {self.device}")

        # 載入模型和 tokenizer
        self.tokenizer = None
        self.model = None
        self._load_model()

    @handle_errors(default_message="載入嵌入模型失敗", reraise=True)
    def _load_model(self):
        """載入嵌入模型"""
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModel.from_pretrained(self.model_name)
            self.model.to(self.device)
            self.model.eval()
            logger.info(f"嵌入模型載入成功: {self.model_name}")

        except Exception as e:
            logger.error(f"載入嵌入模型失敗: {e}")
            raise EmbeddingException(f"無法載入嵌入模型: {self.model_name}")

    def embed_text(
        self,
        text: Union[str, List[str]],
        batch_size: int = 32,
    ) -> np.ndarray:
        """
        生成文本嵌入

        Args:
            text: 單個文本或文本列表
            batch_size: 批次大小

        Returns:
            嵌入向量 (shape: [num_texts, embedding_dim])
        """
        if isinstance(text, str):
            text = [text]

        if not text:
            raise EmbeddingException("輸入文本不能為空")

        embeddings = []

        # 批次處理
        for i in range(0, len(text), batch_size):
            batch = text[i : i + batch_size]
            batch_embeddings = self._embed_batch(batch)
            embeddings.append(batch_embeddings)

        # 合併所有批次
        all_embeddings = np.vstack(embeddings)

        logger.debug(f"生成嵌入: {len(text)} 個文本, 維度: {all_embeddings.shape}")

        return all_embeddings

    @handle_errors(default_message="生成嵌入失敗", reraise=True)
    def _embed_batch(self, texts: List[str]) -> np.ndarray:
        """
        批次生成嵌入

        Args:
            texts: 文本列表

        Returns:
            嵌入向量
        """
        try:
            # Tokenize
            inputs = self.tokenizer(
                texts,
                padding=True,
                truncation=True,
                max_length=self.max_length,
                return_tensors="pt",
            )

            # 移到設備
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            # 生成嵌入
            with torch.no_grad():
                outputs = self.model(**inputs)

                # 使用 [CLS] token 的嵌入或池化
                if hasattr(outputs, "pooler_output") and outputs.pooler_output is not None:
                    embeddings = outputs.pooler_output
                else:
                    # 使用平均池化
                    embeddings = self._mean_pooling(
                        outputs.last_hidden_state, inputs["attention_mask"]
                    )

            # 轉換為 numpy
            embeddings = embeddings.cpu().numpy()

            # 歸一化
            if self.normalize:
                embeddings = embeddings / np.linalg.norm(
                    embeddings, axis=1, keepdims=True
                )

            return embeddings

        except Exception as e:
            logger.error(f"生成嵌入失敗: {e}")
            raise EmbeddingException(f"批次嵌入生成失敗: {str(e)}")

    @staticmethod
    def _mean_pooling(
        last_hidden_state: torch.Tensor, attention_mask: torch.Tensor
    ) -> torch.Tensor:
        """
        平均池化

        Args:
            last_hidden_state: 最後隱藏層狀態
            attention_mask: 注意力遮罩

        Returns:
            池化後的嵌入
        """
        input_mask_expanded = (
            attention_mask.unsqueeze(-1).expand(last_hidden_state.size()).float()
        )
        sum_embeddings = torch.sum(last_hidden_state * input_mask_expanded, 1)
        sum_mask = torch.clamp(input_mask_expanded.sum(1), min=1e-9)
        return sum_embeddings / sum_mask

    def embed_query(self, query: str) -> np.ndarray:
        """
        生成查詢嵌入 (單個向量)

        Args:
            query: 查詢文本

        Returns:
            嵌入向量 (shape: [embedding_dim,])
        """
        embedding = self.embed_text(query)
        return embedding[0]  # 返回第一個向量

    def embed_documents(self, documents: List[str]) -> np.ndarray:
        """
        生成文檔嵌入

        Args:
            documents: 文檔列表

        Returns:
            嵌入向量矩陣
        """
        return self.embed_text(documents)

    def get_embedding_dimension(self) -> int:
        """
        獲取嵌入維度

        Returns:
            嵌入向量的維度
        """
        # 測試嵌入以獲取維度
        test_embedding = self.embed_text("test")
        return test_embedding.shape[1]

    def similarity(
        self, text1: Union[str, np.ndarray], text2: Union[str, np.ndarray]
    ) -> float:
        """
        計算兩個文本的相似度 (餘弦相似度)

        Args:
            text1: 文本1 或嵌入向量1
            text2: 文本2 或嵌入向量2

        Returns:
            相似度分數 (0-1)
        """
        # 如果是文本，先生成嵌入
        if isinstance(text1, str):
            emb1 = self.embed_query(text1)
        else:
            emb1 = text1

        if isinstance(text2, str):
            emb2 = self.embed_query(text2)
        else:
            emb2 = text2

        # 計算餘弦相似度
        similarity = np.dot(emb1, emb2)

        # 如果已經歸一化，點積就是餘弦相似度
        # 否則需要除以範數
        if not self.normalize:
            similarity = similarity / (np.linalg.norm(emb1) * np.linalg.norm(emb2))

        return float(similarity)

    def batch_similarity(
        self, query: Union[str, np.ndarray], documents: Union[List[str], np.ndarray]
    ) -> np.ndarray:
        """
        計算查詢與多個文檔的相似度

        Args:
            query: 查詢文本或嵌入
            documents: 文檔列表或嵌入矩陣

        Returns:
            相似度分數數組
        """
        # 生成嵌入
        if isinstance(query, str):
            query_emb = self.embed_query(query)
        else:
            query_emb = query

        if isinstance(documents, list):
            doc_embs = self.embed_documents(documents)
        else:
            doc_embs = documents

        # 計算相似度
        similarities = np.dot(doc_embs, query_emb)

        # 如果未歸一化，需要標準化
        if not self.normalize:
            query_norm = np.linalg.norm(query_emb)
            doc_norms = np.linalg.norm(doc_embs, axis=1)
            similarities = similarities / (query_norm * doc_norms)

        return similarities

    def unload(self):
        """卸載模型釋放記憶體"""
        if self.model is not None:
            del self.model
            self.model = None

        if self.tokenizer is not None:
            del self.tokenizer
            self.tokenizer = None

        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        logger.info("嵌入模型已卸載")
