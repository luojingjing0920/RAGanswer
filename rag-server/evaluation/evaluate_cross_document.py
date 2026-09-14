import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

from rag.embeddings import EmbeddingService
from rag.vector_store import VectorStore


TOP_K_VALUES = [1, 3, 5, 8]

HYBRID_WEIGHTS = [
    1.25,
    1.50,
    2.00,
]

RRF_K = 60

MAX_CANDIDATES = 100


# =========================================================
# Tokenizer
# =========================================================

def tokenize(text: str) -> list[str]:
    """
    Lightweight tokenizer for BM25 experiment.

    English:
        Add Field -> add, field

    Chinese:
        数据流 -> 数据, 据流
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
# Result helpers
# =========================================================

def make_key(
    metadata: dict,
) -> tuple:
    return (
        metadata.get("document_id"),
        metadata.get("chunk_index"),
    )


def normalize_text(
    text: str,
) -> str:
    return (
        text.lower()
        .replace(" ", "")
        .replace("\n", "")
        .replace("\r", "")
    )


def is_expected_document(
    item: dict,
    case: dict,
) -> bool:
    expected_files = (
        case.get("expected_file_names")
        or []
    )

    if not expected_files:
        return False

    metadata = item.get(
        "metadata",
        {},
    )

    return (
        metadata.get("file_name")
        in expected_files
    )


def is_expected_evidence(
    item: dict,
    case: dict,
) -> bool:

    if not is_expected_document(
        item,
        case,
    ):
        return False

    metadata = item.get(
        "metadata",
        {},
    )

    expected_pages = (
        case.get("expected_pages")
        or []
    )

    if expected_pages:
        page = metadata.get("page")

        if page not in expected_pages:
            return False

    keywords = (
        case.get("evidence_keywords")
        or []
    )

    min_keyword_matches = (
        case.get(
            "min_keyword_matches",
            0,
        )
    )

    if not keywords:
        return True

    text = normalize_text(
        item.get("text", "")
    )

    matches = 0

    for keyword in keywords:
        normalized_keyword = (
            normalize_text(keyword)
        )

        if normalized_keyword in text:
            matches += 1

    return (
        matches
        >= min_keyword_matches
    )


def first_rank(
    results: list[dict],
    matcher,
) -> int | None:

    for rank, item in enumerate(
        results,
        start=1,
    ):
        if matcher(item):
            return rank

    return None


# =========================================================
# Hybrid RRF
# =========================================================

def build_hybrid_results(
    dense_results: list[dict],
    bm25_results: list[dict],
    bm25_weight: float,
) -> list[dict]:

    scores = defaultdict(float)

    item_map = {}

    for rank, item in enumerate(
        dense_results,
        start=1,
    ):
        key = make_key(
            item["metadata"]
        )

        item_map[key] = item

        scores[key] += (
            1.0
            / (
                RRF_K
                + rank
            )
        )

    for rank, item in enumerate(
        bm25_results,
        start=1,
    ):
        key = make_key(
            item["metadata"]
        )

        item_map[key] = item

        scores[key] += (
            bm25_weight
            / (
                RRF_K
                + rank
            )
        )

    results = []

    for key, score in scores.items():
        item = item_map[key]

        results.append(
            {
                "text":
                    item["text"],

                "metadata":
                    item["metadata"],

                "rrf_score":
                    score,
            }
        )

    results.sort(
        key=lambda item:
        item["rrf_score"],
        reverse=True,
    )

    return results


# =========================================================
# Metrics
# =========================================================

def create_metric_bucket():
    return {
        "count": 0,
        "document_hits": {
            k: 0
            for k in TOP_K_VALUES
        },
        "evidence_hits": {
            k: 0
            for k in TOP_K_VALUES
        },
        "mrr_sum": 0.0,
    }


def update_metrics(
    bucket: dict,
    document_rank: int | None,
    evidence_rank: int | None,
):
    bucket["count"] += 1

    for k in TOP_K_VALUES:
        if (
            document_rank is not None
            and document_rank <= k
        ):
            bucket[
                "document_hits"
            ][k] += 1

        if (
            evidence_rank is not None
            and evidence_rank <= k
        ):
            bucket[
                "evidence_hits"
            ][k] += 1

    if evidence_rank is not None:
        bucket["mrr_sum"] += (
            1.0
            / evidence_rank
        )


def print_metrics(
    name: str,
    bucket: dict,
):
    count = bucket["count"]

    print()
    print("-" * 80)
    print(name)
    print("-" * 80)

    if count == 0:
        print("No positive cases")
        return

    for k in TOP_K_VALUES:
        document_hits = (
            bucket[
                "document_hits"
            ][k]
        )

        evidence_hits = (
            bucket[
                "evidence_hits"
            ][k]
        )

        document_rate = (
            document_hits
            / count
        )

        evidence_rate = (
            evidence_hits
            / count
        )

        print(
            f"Document Hit@{k}: "
            f"{document_hits}/{count} "
            f"({document_rate:.1%})"
        )

        print(
            f"Evidence Hit@{k}: "
            f"{evidence_hits}/{count} "
            f"({evidence_rate:.1%})"
        )

    mrr = (
        bucket["mrr_sum"]
        / count
    )

    print(
        f"Evidence MRR: "
        f"{mrr:.3f}"
    )


# =========================================================
# Main
# =========================================================

def main():

    if len(sys.argv) < 2:
        raise SystemExit(
            "Dataset path is required"
        )

    dataset_path = Path(
        sys.argv[1]
    )

    with dataset_path.open(
        "r",
        encoding="utf-8",
    ) as file:
        cases = json.load(file)

    embedding_service = (
        EmbeddingService()
    )

    vector_store = VectorStore()

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

    corpus_size = len(documents)

    candidate_limit = min(
        corpus_size,
        MAX_CANDIDATES,
    )

    print("=" * 80)
    print("CROSS-DOCUMENT RETRIEVAL BENCHMARK")
    print("=" * 80)

    print(
        "Corpus chunks:",
        corpus_size,
    )

    print(
        "Evaluation cases:",
        len(cases),
    )

    print(
        "Candidate limit:",
        candidate_limit,
    )

    metric_buckets = {
        "Dense":
            create_metric_bucket(),

        "BM25":
            create_metric_bucket(),
    }

    for weight in HYBRID_WEIGHTS:
        metric_buckets[
            f"Hybrid-{weight:.2f}"
        ] = create_metric_bucket()

    negative_diagnostics = []

    # =====================================================
    # Evaluate each case
    # =====================================================

    for case in cases:
        question = case["question"]

        should_reject = (
            case.get(
                "should_reject",
                False,
            )
        )

        query_embedding = (
            embedding_service.embed_query(
                question
            )
        )

        dense_results = (
            vector_store.search(
                query_embedding=query_embedding,
                top_k=candidate_limit,
                document_id=None,
            )
        )

        bm25_scores = calculate_bm25(
            question,
            documents,
        )

        bm25_results = []

        for (
            document,
            metadata,
            score,
        ) in zip(
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

        bm25_results = (
            bm25_results[
                :candidate_limit
            ]
        )

        result_sets = {
            "Dense":
                dense_results,

            "BM25":
                bm25_results,
        }

        for weight in HYBRID_WEIGHTS:
            name = (
                f"Hybrid-{weight:.2f}"
            )

            result_sets[name] = (
                build_hybrid_results(
                    dense_results,
                    bm25_results,
                    bm25_weight=weight,
                )
            )

        # -------------------------------------------------
        # Negative cases:
        # Do not pretend RRF/BM25 have calibrated
        # rejection thresholds yet.
        # Only collect diagnostics here.
        # -------------------------------------------------

        if should_reject:
            diagnostic = {
                "id":
                    case["id"],

                "question":
                    question,

                "dense_top1":
                    None,

                "bm25_top1":
                    None,

                "hybrid_top1":
                    {},
            }

            if dense_results:
                diagnostic[
                    "dense_top1"
                ] = {
                    "score":
                        dense_results[
                            0
                        ].get(
                            "similarity"
                        ),

                    "file":
                        dense_results[
                            0
                        ][
                            "metadata"
                        ].get(
                            "file_name"
                        ),
                }

            if bm25_results:
                diagnostic[
                    "bm25_top1"
                ] = {
                    "score":
                        bm25_results[
                            0
                        ].get(
                            "bm25_score"
                        ),

                    "file":
                        bm25_results[
                            0
                        ][
                            "metadata"
                        ].get(
                            "file_name"
                        ),
                }

            for weight in HYBRID_WEIGHTS:
                name = (
                    f"Hybrid-{weight:.2f}"
                )

                hybrid_results = (
                    result_sets[name]
                )

                if hybrid_results:
                    diagnostic[
                        "hybrid_top1"
                    ][name] = {
                        "score":
                            hybrid_results[
                                0
                            ].get(
                                "rrf_score"
                            ),

                        "file":
                            hybrid_results[
                                0
                            ][
                                "metadata"
                            ].get(
                                "file_name"
                            ),
                    }

            negative_diagnostics.append(
                diagnostic
            )

            continue

        # -------------------------------------------------
        # Positive cases
        # -------------------------------------------------

        print()
        print(
            f"[{case['id']}] "
            f"{case['category']}"
        )

        print(
            question
        )

        for (
            method_name,
            results,
        ) in result_sets.items():

            document_rank = first_rank(
                results,
                lambda item:
                    is_expected_document(
                        item,
                        case,
                    ),
            )

            evidence_rank = first_rank(
                results,
                lambda item:
                    is_expected_evidence(
                        item,
                        case,
                    ),
            )

            update_metrics(
                metric_buckets[
                    method_name
                ],
                document_rank,
                evidence_rank,
            )

            print(
                f"  {method_name:<12} "
                f"DocRank="
                f"{document_rank} | "
                f"EvidenceRank="
                f"{evidence_rank}"
            )

    # =====================================================
    # Summary
    # =====================================================

    print()
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)

    for (
        method_name,
        bucket,
    ) in metric_buckets.items():
        print_metrics(
            method_name,
            bucket,
        )

    # =====================================================
    # Negative diagnostics
    # =====================================================

    print()
    print()
    print("=" * 80)
    print("NEGATIVE CASE DIAGNOSTICS")
    print("=" * 80)

    print(
        "No rejection accuracy is reported yet."
    )

    print(
        "BM25 and RRF scores are not calibrated "
        "as answerability thresholds."
    )

    for item in negative_diagnostics:
        print()
        print(
            f"[{item['id']}] "
            f"{item['question']}"
        )

        print(
            "  Dense Top1:",
            item["dense_top1"],
        )

        print(
            "  BM25 Top1:",
            item["bm25_top1"],
        )

        for (
            name,
            value,
        ) in (
            item[
                "hybrid_top1"
            ].items()
        ):
            print(
                f"  {name} Top1:",
                value,
            )


if __name__ == "__main__":
    main()