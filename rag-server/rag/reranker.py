from fastembed.rerank.cross_encoder import (
    TextCrossEncoder,
)


DEFAULT_RERANKER_MODEL = (
    "BAAI/bge-reranker-base"
)


class Reranker:
    """
    Cross-Encoder 精排服务。

    工作流程：

    Semantic Retriever
        ↓
    Candidate Chunks
        ↓
    Cross-Encoder
        ↓
    Relevance Score
        ↓
    Re-ranked Top-N
    """

    def __init__(
        self,
        model_name: str = DEFAULT_RERANKER_MODEL,
        model: TextCrossEncoder | None = None,
    ):
        self.model_name = model_name

        self.model = (
            model
            or TextCrossEncoder(
                model_name=model_name
            )
        )

    def rerank(
        self,
        query: str,
        candidates: list[dict],
        top_n: int = 4,
    ) -> list[dict]:
        """
        对 Retriever 返回的候选 Chunk 重新排序。
        """

        query = query.strip()

        if not query:
            raise ValueError(
                "query 不能为空"
            )

        if not candidates:
            return []

        if top_n <= 0:
            raise ValueError(
                "top_n 必须大于 0"
            )

        documents = [
            item["text"]
            for item in candidates
        ]

        scores = list(
            self.model.rerank(
                query,
                documents,
            )
        )

        if len(scores) != len(candidates):
            raise RuntimeError(
                "Reranker 返回的分数数量"
                "与候选文档数量不一致"
            )

        reranked_results = []

        for index, (
            candidate,
            score,
        ) in enumerate(
            zip(
                candidates,
                scores,
            ),
            start=1,
        ):
            item = candidate.copy()

            # 保留 Dense Retrieval 原始排名，
            # 便于 Evaluation 对比。
            item["retrieval_rank"] = (
                candidate.get(
                    "rank",
                    index,
                )
            )

            item["rerank_score"] = float(
                score
            )

            reranked_results.append(
                item
            )

        reranked_results.sort(
            key=lambda item: (
                item["rerank_score"]
            ),
            reverse=True,
        )

        for rerank_rank, item in enumerate(
            reranked_results,
            start=1,
        ):
            item["rerank_rank"] = (
                rerank_rank
            )

        return reranked_results[:top_n]