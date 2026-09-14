import math
import re
from collections import Counter, defaultdict

from rag.vector_store import VectorStore


class KeywordRetriever:
    """
    基于 BM25 的关键词检索器。

    用于补充 Dense Retrieval 对：
    - 精确技术术语
    - 文件名 / 类名 / 函数名
    - Add Field / Form Preview 等关键词

    召回不足的问题。

    当前实现保持与 evaluation 中的
    BM25 实验逻辑一致，避免生产实现
    与 Benchmark 使用不同算法。
    """

    def __init__(
        self,
        vector_store: VectorStore | None = None,
        k1: float = 1.5,
        b: float = 0.75,
    ):
        self.vector_store = (
            vector_store
            or VectorStore()
        )

        self.k1 = k1
        self.b = b

    @staticmethod
    def _tokenize(
        text: str,
    ) -> list[str]:
        """
        轻量级中英文 tokenizer。

        英文：
        Add Field
        -> add, field

        中文：
        数据流
        -> 数据, 据流

        当前主要目标是提升技术术语和
        中英混合文本的 lexical recall。
        """

        text = text.lower()

        parts = re.findall(
            r"[a-z0-9_./+-]+|[\u4e00-\u9fff]+",
            text,
        )

        tokens = []

        for part in parts:
            if re.fullmatch(
                r"[\u4e00-\u9fff]+",
                part,
            ):
                if len(part) == 1:
                    tokens.append(part)
                    continue

                tokens.extend(
                    part[index:index + 2]
                    for index in range(
                        len(part) - 1
                    )
                )

            else:
                tokens.append(part)

        return tokens

    def retrieve(
        self,
        query: str,
        top_k: int = 8,
        document_id: str | None = None,
    ) -> list[dict]:
        """
        使用 BM25 对 Chroma 中的原始 chunks
        执行关键词检索。
        """

        query = query.strip()

        if not query:
            raise ValueError(
                "query 不能为空"
            )

        if top_k <= 0:
            return []

        chunks = (
            self.vector_store.get_chunks(
                document_id=document_id
            )
        )

        if not chunks:
            return []

        query_tokens = self._tokenize(
            query
        )

        if not query_tokens:
            return []

        tokenized_documents = [
            self._tokenize(
                item["text"]
            )
            for item in chunks
        ]

        document_count = len(
            tokenized_documents
        )

        document_lengths = [
            len(tokens)
            for tokens in tokenized_documents
        ]

        average_document_length = (
            sum(document_lengths)
            / document_count
        )

        document_frequency = (
            defaultdict(int)
        )

        for tokens in tokenized_documents:
            for token in set(tokens):
                document_frequency[
                    token
                ] += 1

        results = []

        for (
            chunk,
            tokens,
            document_length,
        ) in zip(
            chunks,
            tokenized_documents,
            document_lengths,
        ):
            frequencies = Counter(
                tokens
            )

            score = 0.0

            for token in query_tokens:
                term_frequency = (
                    frequencies.get(
                        token,
                        0,
                    )
                )

                if term_frequency == 0:
                    continue

                doc_frequency = (
                    document_frequency[
                        token
                    ]
                )

                inverse_document_frequency = (
                    math.log(
                        1
                        + (
                            document_count
                            - doc_frequency
                            + 0.5
                        )
                        / (
                            doc_frequency
                            + 0.5
                        )
                    )
                )

                denominator = (
                    term_frequency
                    + self.k1
                    * (
                        1
                        - self.b
                        + self.b
                        * document_length
                        / average_document_length
                    )
                )

                score += (
                    inverse_document_frequency
                    * term_frequency
                    * (self.k1 + 1)
                    / denominator
                )

            results.append(
                {
                    "text":
                        chunk["text"],

                    "metadata":
                        chunk["metadata"],

                    "keyword_score":
                        score,
                }
            )

        results.sort(
            key=lambda item:
            item["keyword_score"],
            reverse=True,
        )

        top_results = results[
            :top_k
        ]

        for rank, item in enumerate(
            top_results,
            start=1,
        ):
            item["rank"] = rank

        return top_results