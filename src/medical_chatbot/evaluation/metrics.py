"""
評估指標

提供各種文本評估指標的計算。
"""
from typing import List, Dict, Any, Optional
import re
import math
from collections import Counter
import numpy as np
from loguru import logger


class EvaluationMetrics:
    """評估指標計算器"""

    @staticmethod
    def bleu_score(
        reference: str,
        candidate: str,
        n_gram: int = 4,
        weights: Optional[List[float]] = None,
    ) -> float:
        """
        計算 BLEU 分數

        Args:
            reference: 參考文本
            candidate: 候選文本
            n_gram: N-gram 最大值
            weights: 權重列表

        Returns:
            BLEU 分數 (0-1)
        """
        if not weights:
            weights = [1.0 / n_gram] * n_gram

        # 分詞（簡單按字符分割）
        ref_tokens = list(reference)
        cand_tokens = list(candidate)

        # 計算各 N-gram 精確度
        precisions = []
        for n in range(1, n_gram + 1):
            ref_ngrams = EvaluationMetrics._get_ngrams(ref_tokens, n)
            cand_ngrams = EvaluationMetrics._get_ngrams(cand_tokens, n)

            if not cand_ngrams:
                precisions.append(0.0)
                continue

            # 計算匹配數
            matches = 0
            for ngram in cand_ngrams:
                if ngram in ref_ngrams:
                    matches += min(cand_ngrams[ngram], ref_ngrams[ngram])

            precision = matches / sum(cand_ngrams.values())
            precisions.append(precision)

        # 計算簡短懲罰
        brevity_penalty = EvaluationMetrics._brevity_penalty(
            len(ref_tokens), len(cand_tokens)
        )

        # 計算加權幾何平均
        if min(precisions) > 0:
            log_precisions = [w * math.log(p) for w, p in zip(weights, precisions)]
            geo_mean = math.exp(sum(log_precisions))
        else:
            geo_mean = 0.0

        return brevity_penalty * geo_mean

    @staticmethod
    def rouge_score(
        reference: str,
        candidate: str,
        rouge_type: str = "rouge-1",
    ) -> Dict[str, float]:
        """
        計算 ROUGE 分數

        Args:
            reference: 參考文本
            candidate: 候選文本
            rouge_type: ROUGE 類型 (rouge-1, rouge-2, rouge-l)

        Returns:
            包含 precision, recall, f1 的字典
        """
        # 分詞
        ref_tokens = list(reference)
        cand_tokens = list(candidate)

        if rouge_type == "rouge-1":
            ref_ngrams = Counter(ref_tokens)
            cand_ngrams = Counter(cand_tokens)
        elif rouge_type == "rouge-2":
            ref_ngrams = EvaluationMetrics._get_ngrams(ref_tokens, 2)
            cand_ngrams = EvaluationMetrics._get_ngrams(cand_tokens, 2)
        elif rouge_type == "rouge-l":
            # ROUGE-L 使用最長公共子序列
            lcs_length = EvaluationMetrics._lcs_length(ref_tokens, cand_tokens)

            if len(ref_tokens) == 0 or len(cand_tokens) == 0:
                return {"precision": 0.0, "recall": 0.0, "f1": 0.0}

            precision = lcs_length / len(cand_tokens) if cand_tokens else 0.0
            recall = lcs_length / len(ref_tokens) if ref_tokens else 0.0
            f1 = (
                2 * precision * recall / (precision + recall)
                if (precision + recall) > 0
                else 0.0
            )

            return {"precision": precision, "recall": recall, "f1": f1}
        else:
            raise ValueError(f"不支援的 ROUGE 類型: {rouge_type}")

        # 計算匹配數
        matches = sum(
            min(ref_ngrams[ng], cand_ngrams[ng]) for ng in cand_ngrams if ng in ref_ngrams
        )

        # 計算精確率和召回率
        precision = matches / sum(cand_ngrams.values()) if cand_ngrams else 0.0
        recall = matches / sum(ref_ngrams.values()) if ref_ngrams else 0.0
        f1 = (
            2 * precision * recall / (precision + recall)
            if (precision + recall) > 0
            else 0.0
        )

        return {"precision": precision, "recall": recall, "f1": f1}

    @staticmethod
    def perplexity(log_probs: List[float]) -> float:
        """
        計算困惑度

        Args:
            log_probs: 對數機率列表

        Returns:
            困惑度
        """
        if not log_probs:
            return float("inf")

        avg_log_prob = sum(log_probs) / len(log_probs)
        return math.exp(-avg_log_prob)

    @staticmethod
    def exact_match(reference: str, candidate: str) -> float:
        """
        計算精確匹配率

        Args:
            reference: 參考文本
            candidate: 候選文本

        Returns:
            1.0 (匹配) 或 0.0 (不匹配)
        """
        # 去除空白後比較
        ref_normalized = "".join(reference.split())
        cand_normalized = "".join(candidate.split())

        return 1.0 if ref_normalized == cand_normalized else 0.0

    @staticmethod
    def f1_score(reference: str, candidate: str) -> float:
        """
        計算 Token 級別的 F1 分數

        Args:
            reference: 參考文本
            candidate: 候選文本

        Returns:
            F1 分數
        """
        ref_tokens = set(reference)
        cand_tokens = set(candidate)

        if not cand_tokens or not ref_tokens:
            return 0.0

        common = ref_tokens & cand_tokens
        precision = len(common) / len(cand_tokens)
        recall = len(common) / len(ref_tokens)

        if precision + recall == 0:
            return 0.0

        return 2 * precision * recall / (precision + recall)

    @staticmethod
    def edit_distance(reference: str, candidate: str) -> int:
        """
        計算編輯距離（Levenshtein 距離）

        Args:
            reference: 參考文本
            candidate: 候選文本

        Returns:
            編輯距離
        """
        m, n = len(reference), len(candidate)

        # 創建 DP 表
        dp = [[0] * (n + 1) for _ in range(m + 1)]

        # 初始化
        for i in range(m + 1):
            dp[i][0] = i
        for j in range(n + 1):
            dp[0][j] = j

        # 填充 DP 表
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if reference[i - 1] == candidate[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1]
                else:
                    dp[i][j] = min(
                        dp[i - 1][j] + 1,  # 刪除
                        dp[i][j - 1] + 1,  # 插入
                        dp[i - 1][j - 1] + 1,  # 替換
                    )

        return dp[m][n]

    @staticmethod
    def semantic_similarity(
        reference: str,
        candidate: str,
        embedder=None,
    ) -> float:
        """
        計算語義相似度（使用嵌入向量）

        Args:
            reference: 參考文本
            candidate: 候選文本
            embedder: 嵌入器實例

        Returns:
            餘弦相似度 (0-1)
        """
        if not embedder:
            logger.warning("未提供嵌入器，使用簡單字符重疊作為相似度")
            return EvaluationMetrics.f1_score(reference, candidate)

        try:
            # 生成嵌入
            ref_embedding = embedder.embed_text(reference)
            cand_embedding = embedder.embed_text(candidate)

            # 計算餘弦相似度
            similarity = np.dot(ref_embedding, cand_embedding) / (
                np.linalg.norm(ref_embedding) * np.linalg.norm(cand_embedding)
            )

            return float(similarity)

        except Exception as e:
            logger.error(f"計算語義相似度失敗: {e}")
            return 0.0

    @staticmethod
    def length_ratio(reference: str, candidate: str) -> float:
        """
        計算長度比率

        Args:
            reference: 參考文本
            candidate: 候選文本

        Returns:
            長度比率
        """
        ref_len = len(reference)
        cand_len = len(candidate)

        if ref_len == 0:
            return 0.0

        return cand_len / ref_len

    @staticmethod
    def diversity_score(texts: List[str]) -> Dict[str, float]:
        """
        計算多樣性分數

        Args:
            texts: 文本列表

        Returns:
            多樣性指標字典
        """
        if not texts:
            return {
                "unique_unigrams": 0.0,
                "unique_bigrams": 0.0,
                "unique_trigrams": 0.0,
            }

        all_unigrams = []
        all_bigrams = []
        all_trigrams = []

        for text in texts:
            tokens = list(text)
            all_unigrams.extend(tokens)
            all_bigrams.extend(
                [tuple(tokens[i : i + 2]) for i in range(len(tokens) - 1)]
            )
            all_trigrams.extend(
                [tuple(tokens[i : i + 3]) for i in range(len(tokens) - 2)]
            )

        return {
            "unique_unigrams": len(set(all_unigrams)) / len(all_unigrams)
            if all_unigrams
            else 0.0,
            "unique_bigrams": len(set(all_bigrams)) / len(all_bigrams)
            if all_bigrams
            else 0.0,
            "unique_trigrams": len(set(all_trigrams)) / len(all_trigrams)
            if all_trigrams
            else 0.0,
        }

    # ========================================================================
    # 工具方法
    # ========================================================================

    @staticmethod
    def _get_ngrams(tokens: List[str], n: int) -> Counter:
        """生成 N-grams"""
        ngrams = []
        for i in range(len(tokens) - n + 1):
            ngrams.append(tuple(tokens[i : i + n]))
        return Counter(ngrams)

    @staticmethod
    def _brevity_penalty(ref_len: int, cand_len: int) -> float:
        """計算 BLEU 簡短懲罰"""
        if cand_len > ref_len:
            return 1.0
        elif cand_len == 0:
            return 0.0
        else:
            return math.exp(1 - ref_len / cand_len)

    @staticmethod
    def _lcs_length(seq1: List, seq2: List) -> int:
        """計算最長公共子序列長度"""
        m, n = len(seq1), len(seq2)

        # 創建 DP 表
        dp = [[0] * (n + 1) for _ in range(m + 1)]

        # 填充 DP 表
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if seq1[i - 1] == seq2[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1] + 1
                else:
                    dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])

        return dp[m][n]

    # ========================================================================
    # 批次評估
    # ========================================================================

    @staticmethod
    def evaluate_batch(
        references: List[str],
        candidates: List[str],
        metrics: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        批次評估

        Args:
            references: 參考文本列表
            candidates: 候選文本列表
            metrics: 要計算的指標列表

        Returns:
            評估結果字典
        """
        if len(references) != len(candidates):
            raise ValueError("參考文本和候選文本數量不匹配")

        if not metrics:
            metrics = ["bleu", "rouge-1", "rouge-2", "rouge-l", "f1", "exact_match"]

        results = {metric: [] for metric in metrics}

        for ref, cand in zip(references, candidates):
            for metric in metrics:
                if metric == "bleu":
                    score = EvaluationMetrics.bleu_score(ref, cand)
                    results[metric].append(score)

                elif metric.startswith("rouge"):
                    rouge_result = EvaluationMetrics.rouge_score(ref, cand, metric)
                    results[metric].append(rouge_result["f1"])

                elif metric == "f1":
                    score = EvaluationMetrics.f1_score(ref, cand)
                    results[metric].append(score)

                elif metric == "exact_match":
                    score = EvaluationMetrics.exact_match(ref, cand)
                    results[metric].append(score)

                elif metric == "edit_distance":
                    distance = EvaluationMetrics.edit_distance(ref, cand)
                    results[metric].append(distance)

        # 計算平均值
        aggregated = {}
        for metric, scores in results.items():
            if metric == "edit_distance":
                aggregated[metric] = {
                    "mean": sum(scores) / len(scores),
                    "min": min(scores),
                    "max": max(scores),
                }
            else:
                aggregated[metric] = {
                    "mean": sum(scores) / len(scores),
                    "std": np.std(scores),
                    "min": min(scores),
                    "max": max(scores),
                }

        return aggregated
