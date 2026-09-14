from collections import defaultdict

from rag.keyword_retriever import KeywordRetriever
from rag.retriever import Retriever


class HybridRetriever:
    """
    Dense Retrieval + BM25 + Weighted RRF。

    当前参数来自跨文档 Benchmark：

    Dense weight = 1.0
    BM25 weight = 2.0
    RRF k = 60

    主要用于“全部文档”检索场景，
    解决 Dense 对精确技术术语召回不足的问题。
    """

    def __init__(
        self,
        dense_retriever: Retriever | None = None,
        keyword_retriever: KeywordRetriever | None = None,
        dense_weight: float = 1.0,
        keyword_weight: float = 2.0,
        rrf_k: int = 60,
        candidate_k: int = 100,
    ):
        self.dense_retriever = (
            dense_retriever
            or Retriever()
        )

        self.keyword_retriever = (
            keyword_retriever
            or KeywordRetriever(
                vector_store=(
                    self.dense_retriever
                    .vector_store
                )
            )
        )

        self.dense_weight = (
            dense_weight
        )

        self.keyword_weight = (
            keyword_weight
        )

        self.rrf_k = rrf_k
        self.candidate_k = candidate_k

    @staticmethod
    def _make_key(
        item: dict,
    ) -> tuple:
        metadata = item.get(
            "metadata",
            {},
        )

        return (
            metadata.get("document_id"),
            metadata.get("chunk_index"),
        )

    def retrieve(
        self,
        query: str,
        top_k: int = 8,
        document_id: str | None = None,
    ) -> list[dict]:
        """
        执行 Hybrid Retrieval。

        1. Dense 获取候选
        2. BM25 获取候选
        3. Weighted RRF 融合
        4. 返回最终 Top-K
        """

        query = query.strip()

        if not query:
            raise ValueError(
                "query 不能为空"
            )

        if top_k <= 0:
            return []

        candidate_k = max(
            top_k,
            self.candidate_k,
        )

        # ---------------------------------------------
        # 1. Dense candidates
        # ---------------------------------------------

        dense_results = (
            self.dense_retriever.retrieve(
                query=query,
                top_k=candidate_k,
                document_id=document_id,

                # Hybrid 候选阶段不使用
                # Dense similarity threshold 过滤，
                # 避免提前丢掉可被 BM25 救回的证据。
                similarity_threshold=0.0,
            )
        )

        # ---------------------------------------------
        # 2. BM25 candidates
        # ---------------------------------------------

        keyword_results = (
            self.keyword_retriever.retrieve(
                query=query,
                top_k=candidate_k,
                document_id=document_id,
            )
        )

        # ---------------------------------------------
        # 3. Weighted RRF
        # ---------------------------------------------

        rrf_scores = defaultdict(float)

        item_map = {}

        dense_similarity_map = {}
        keyword_score_map = {}

        for rank, item in enumerate(
            dense_results,
            start=1,
        ):
            key = self._make_key(
                item
            )

            item_map[key] = item

            dense_similarity_map[
                key
            ] = item.get(
                "similarity"
            )

            rrf_scores[key] += (
                self.dense_weight
                / (
                    self.rrf_k
                    + rank
                )
            )

        for rank, item in enumerate(
            keyword_results,
            start=1,
        ):
            key = self._make_key(
                item
            )

            if key not in item_map:
                item_map[key] = item

            keyword_score_map[
                key
            ] = item.get(
                "keyword_score"
            )

            rrf_scores[key] += (
                self.keyword_weight
                / (
                    self.rrf_k
                    + rank
                )
            )

        # ---------------------------------------------
        # 4. Build final results
        # ---------------------------------------------

        hybrid_results = []

        for key, rrf_score in (
            rrf_scores.items()
        ):
            item = item_map[key]

            hybrid_results.append(
                {
                    "text":
                        item["text"],

                    "metadata":
                        item["metadata"],

                    # 保留 Dense similarity，
                    # 兼容现有 Context / Source 数据结构。
                    "similarity":
                        dense_similarity_map.get(
                            key,
                            0.0,
                        ),

                    "keyword_score":
                        keyword_score_map.get(
                            key,
                            0.0,
                        ),

                    "rrf_score":
                        rrf_score,
                }
            )

        hybrid_results.sort(
            key=lambda item:
            item["rrf_score"],
            reverse=True,
        )

        final_results = (
            hybrid_results[:top_k]
        )

        for rank, item in enumerate(
            final_results,
            start=1,
        ):
            item["rank"] = rank

        return final_results