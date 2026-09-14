import math
import re
from collections import Counter, defaultdict

from rag.embeddings import EmbeddingService
from rag.vector_store import VectorStore


# =========================================================
# Config
# =========================================================

QUERY = (
    "\u8fd9\u4e2a JSON Schema Builder "
    "\u9879\u76ee\u4e2d\uff0c\u4ece\u70b9\u51fb "
    "Add Field \u5230 Form Preview "
    "\u66f4\u65b0\uff0c\u5b8c\u6574\u7684"
    "\u6570\u636e\u6d41\u7ecf\u8fc7"
    "\u54ea\u4e9b\u6b65\u9aa4\uff1f"
)

TARGET_FILE = (
    "JSON-Schema-Builder_10\u5929\u5b66\u4e60"
    "\u4e0eAI\u6539\u9020\u8ba1\u5212.docx"
)

TARGET_CHUNK_INDEX = 8

DENSE_TOP_N = 50
BM25_TOP_N = 50
RRF_K = 60


# =========================================================
# Tokenizer
# =========================================================

def tokenize(text: str) -> list[str]:
    """
    轻量级实验 tokenizer。

    英文：
        Add Field -> add, field

    中文：
        数据流 -> 数据, 据流

    当前目的不是做完整中文分词，
    而是验证 lexical retrieval
    是否能弥补 Dense 对精确术语的召回不足。
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
            # 单字保底
            if len(part) == 1:
                tokens.append(part)
                continue

            # 中文 bigram
            tokens.extend(
                part[index:index + 2]
                for index in range(
                    len(part) - 1
                )
            )
        else:
            tokens.append(part)

    return tokens


# =========================================================
# BM25
# =========================================================

def calculate_bm25(
    query: str,
    documents: list[str],
    k1: float = 1.5,
    b: float = 0.75,
) -> list[float]:

    tokenized_documents = [
        tokenize(document)
        for document in documents
    ]

    query_tokens = tokenize(query)

    document_count = len(
        tokenized_documents
    )

    if document_count == 0:
        return []

    document_lengths = [
        len(tokens)
        for tokens in tokenized_documents
    ]

    average_document_length = (
        sum(document_lengths)
        / document_count
    )

    document_frequency = defaultdict(int)

    for tokens in tokenized_documents:
        for token in set(tokens):
            document_frequency[token] += 1

    scores = []

    for tokens, document_length in zip(
        tokenized_documents,
        document_lengths,
    ):
        frequencies = Counter(tokens)

        score = 0.0

        for token in query_tokens:
            tf = frequencies.get(
                token,
                0,
            )

            if tf == 0:
                continue

            df = document_frequency[
                token
            ]

            idf = math.log(
                1
                + (
                    document_count
                    - df
                    + 0.5
                )
                / (
                    df
                    + 0.5
                )
            )

            denominator = (
                tf
                + k1
                * (
                    1
                    - b
                    + b
                    * document_length
                    / average_document_length
                )
            )

            score += (
                idf
                * tf
                * (k1 + 1)
                / denominator
            )

        scores.append(score)

    return scores


# =========================================================
# Helpers
# =========================================================

def make_key(
    metadata: dict,
) -> tuple:
    return (
        metadata.get("document_id"),
        metadata.get("chunk_index"),
    )


def find_target_rank(
    results: list[dict],
):
    for rank, item in enumerate(
        results,
        start=1,
    ):
        metadata = item["metadata"]

        if (
            metadata.get("file_name")
            == TARGET_FILE
            and metadata.get(
                "chunk_index"
            )
            == TARGET_CHUNK_INDEX
        ):
            return rank, item

    return None, None


# =========================================================
# Main
# =========================================================

def main():

    embedding_service = (
        EmbeddingService()
    )

    vector_store = VectorStore()

    # -----------------------------------------------------
    # 1. Dense Retrieval
    # -----------------------------------------------------

    query_embedding = (
        embedding_service.embed_query(
            QUERY
        )
    )

    dense_results = (
        vector_store.search(
            query_embedding=query_embedding,
            top_k=DENSE_TOP_N,
            document_id=None,
        )
    )

    # -----------------------------------------------------
    # 2. Load all chunks
    # -----------------------------------------------------

    raw = vector_store.collection.get(
        include=[
            "documents",
            "metadatas",
        ]
    )

    documents = (
        raw.get("documents")
        or []
    )

    metadatas = (
        raw.get("metadatas")
        or []
    )

    # -----------------------------------------------------
    # 3. BM25
    # -----------------------------------------------------

    bm25_scores = calculate_bm25(
        QUERY,
        documents,
    )

    bm25_results = []

    for document, metadata, score in zip(
        documents,
        metadatas,
        bm25_scores,
    ):
        bm25_results.append(
            {
                "text": document,
                "metadata": metadata,
                "bm25_score": score,
            }
        )

    bm25_results.sort(
        key=lambda item:
        item["bm25_score"],
        reverse=True,
    )

    # -----------------------------------------------------
    # 4. RRF
    # -----------------------------------------------------

    rrf_scores = defaultdict(float)
    item_map = {}

    for rank, item in enumerate(
        dense_results[
            :DENSE_TOP_N
        ],
        start=1,
    ):
        key = make_key(
            item["metadata"]
        )

        item_map[key] = item

        rrf_scores[key] += (
            1
            / (RRF_K + rank)
        )

    for rank, item in enumerate(
        bm25_results[
            :BM25_TOP_N
        ],
        start=1,
    ):
        key = make_key(
            item["metadata"]
        )

        item_map[key] = item

        rrf_scores[key] += (
            1
            / (RRF_K + rank)
        )

    hybrid_results = []

    for key, score in rrf_scores.items():
        item = item_map[key]

        hybrid_results.append(
            {
                "text": item["text"],
                "metadata":
                    item["metadata"],
                "rrf_score": score,
            }
        )

    hybrid_results.sort(
        key=lambda item:
        item["rrf_score"],
        reverse=True,
    )

    # -----------------------------------------------------
    # 5. Evaluation
    # -----------------------------------------------------

    dense_rank, dense_target = (
        find_target_rank(
            dense_results
        )
    )

    bm25_rank, bm25_target = (
        find_target_rank(
            bm25_results
        )
    )

    hybrid_rank, hybrid_target = (
        find_target_rank(
            hybrid_results
        )
    )

    print()
    print("=" * 80)
    print("TARGET RANK COMPARISON")
    print("=" * 80)

    print(
        "Dense Rank:",
        dense_rank,
    )

    print(
        "BM25 Rank:",
        bm25_rank,
    )

    print(
        "Hybrid RRF Rank:",
        hybrid_rank,
    )

    print()

    if dense_target:
        print(
            "Dense similarity:",
            dense_target.get(
                "similarity"
            ),
        )

    if bm25_target:
        print(
            "BM25 score:",
            bm25_target.get(
                "bm25_score"
            ),
        )

    if hybrid_target:
        print(
            "Hybrid RRF score:",
            hybrid_target.get(
                "rrf_score"
            ),
        )

    # -----------------------------------------------------
    # 6. Hybrid Top 10
    # -----------------------------------------------------

    print()
    print("=" * 80)
    print("HYBRID TOP 10")
    print("=" * 80)

    for rank, item in enumerate(
        hybrid_results[:10],
        start=1,
    ):
        metadata = item[
            "metadata"
        ]

        print(
            f"Rank {rank} | "
            f"RRF "
            f"{item['rrf_score']:.6f} | "
            f"File "
            f"{metadata.get('file_name')} | "
            f"Chunk "
            f"{metadata.get('chunk_index')}"
        )

        if (
            metadata.get("file_name")
            == TARGET_FILE
            and metadata.get(
                "chunk_index"
            )
            == TARGET_CHUNK_INDEX
        ):
            print(
                ">>> TARGET CHUNK <<<"
            )

    # -----------------------------------------------------
    # 7. Weighted RRF experiment
    # -----------------------------------------------------

    print()
    print("=" * 80)
    print("WEIGHTED RRF EXPERIMENT")
    print("=" * 80)

    bm25_weights = [
        1.0,
        1.25,
        1.5,
        2.0,
        3.0,
    ]

    for bm25_weight in bm25_weights:
        weighted_scores = defaultdict(
            float
        )

        weighted_item_map = {}

        # Dense weight = 1.0
        for rank, item in enumerate(
            dense_results[
                :DENSE_TOP_N
            ],
            start=1,
        ):
            key = make_key(
                item["metadata"]
            )

            weighted_item_map[
                key
            ] = item

            weighted_scores[
                key
            ] += (
                1.0
                / (
                    RRF_K
                    + rank
                )
            )

        # BM25 weighted
        for rank, item in enumerate(
            bm25_results[
                :BM25_TOP_N
            ],
            start=1,
        ):
            key = make_key(
                item["metadata"]
            )

            weighted_item_map[
                key
            ] = item

            weighted_scores[
                key
            ] += (
                bm25_weight
                / (
                    RRF_K
                    + rank
                )
            )

        weighted_results = []

        for key, score in (
            weighted_scores.items()
        ):
            item = (
                weighted_item_map[
                    key
                ]
            )

            weighted_results.append(
                {
                    "text":
                        item["text"],

                    "metadata":
                        item["metadata"],

                    "rrf_score":
                        score,
                }
            )

        weighted_results.sort(
            key=lambda item:
            item["rrf_score"],
            reverse=True,
        )

        target_rank, _ = (
            find_target_rank(
                weighted_results
            )
        )

        print(
            f"Dense=1.0 | "
            f"BM25={bm25_weight:.2f} "
            f"-> Target Rank: "
            f"{target_rank}"
        )

if __name__ == "__main__":
    main()