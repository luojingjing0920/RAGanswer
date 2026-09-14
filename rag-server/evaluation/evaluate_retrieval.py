from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


# 让脚本可以直接：
# python evaluation/evaluate_retrieval.py
ROOT_DIR = Path(__file__).resolve().parents[1]

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(
        0,
        str(ROOT_DIR),
    )


from rag.retriever import Retriever
from rag.vector_store import VectorStore


DATASET_PATH = (
    Path(__file__)
    .resolve()
    .with_name("dataset.json")
)


def load_dataset() -> list[dict]:
    """
    读取人工标注的 Retrieval Benchmark。
    """

    with DATASET_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        dataset = json.load(file)

    if not isinstance(dataset, list):
        raise ValueError(
            "dataset.json 顶层必须是数组"
        )

    return dataset


def resolve_document_id(
    vector_store: VectorStore,
    file_name: str,
) -> str:
    """
    根据稳定的 file_name，
    从 Chroma metadata 中解析当前 document_id。

    不把 document_id 写死在 Benchmark 中，
    避免文档重新上传后测试集失效。
    """

    result = vector_store.collection.get(
        where={
            "file_name": file_name,
        },
        include=[
            "metadatas",
        ],
    )

    metadatas = (
        result.get("metadatas")
        or []
    )

    document_ids = {
        metadata.get("document_id")
        for metadata in metadatas
        if metadata
        and metadata.get("document_id")
    }

    if not document_ids:
        raise ValueError(
            f"ChromaDB 中没有找到文档："
            f"{file_name}"
        )

    if len(document_ids) > 1:
        raise ValueError(
            f"检测到同名文档存在多个 "
            f"document_id：{file_name}，"
            f"请先清理重复文档。"
        )

    return next(
        iter(document_ids)
    )


def get_result_page(
    result: dict,
) -> int | None:
    metadata = (
        result.get("metadata")
        or {}
    )

    return metadata.get("page")


def first_relevant_rank(
    results: list[dict],
    expected_pages: set[int],
) -> int | None:
    """
    返回第一个命中 Ground Truth Page 的排名。
    没命中则返回 None。
    """

    for index, result in enumerate(
        results,
        start=1,
    ):
        page = get_result_page(
            result
        )

        if page in expected_pages:
            return index

    return None


def hit_at_k(
    results: list[dict],
    expected_pages: set[int],
    k: int,
) -> bool:
    """
    Top-K 中是否至少存在一个正确页面。
    """

    top_results = results[:k]

    return any(
        get_result_page(result)
        in expected_pages
        for result in top_results
    )


def format_pages(
    results: list[dict],
) -> str:
    if not results:
        return "-"

    parts = []

    for result in results:
        page = get_result_page(
            result
        )

        similarity = result.get(
            "similarity"
        )

        if (
            isinstance(
                similarity,
                (int, float),
            )
        ):
            similarity_text = (
                f"{similarity:.3f}"
            )
        else:
            similarity_text = "-"

        parts.append(
            f"{page}"
            f"({similarity_text})"
        )

    return ", ".join(parts)


def evaluate(
    top_k: int,
    threshold: float,
) -> None:
    dataset = load_dataset()

    vector_store = VectorStore()

    retriever = Retriever(
        vector_store=vector_store
    )

    document_id_cache = {}

    positive_count = 0
    negative_count = 0

    hit_1_count = 0
    hit_3_count = 0
    hit_5_count = 0

    reciprocal_rank_sum = 0.0

    negative_rejected_count = 0

    print()
    print(
        "=" * 72
    )
    print(
        "Retrieval Evaluation"
    )
    print(
        "=" * 72
    )
    print(
        f"Dataset   : "
        f"{DATASET_PATH.name}"
    )
    print(
        f"Top-K     : {top_k}"
    )
    print(
        f"Threshold : "
        f"{threshold:.2f}"
    )
    print(
        "=" * 72
    )

    for item in dataset:
        case_id = item["id"]

        category = item.get(
            "category",
            "unknown",
        )

        question = item[
            "question"
        ]

        file_name = item[
            "file_name"
        ]

        expected_pages = set(
            item.get(
                "expected_pages",
                [],
            )
        )

        should_reject = bool(
            item.get(
                "should_reject",
                False,
            )
        )

        if (
            file_name
            not in document_id_cache
        ):
            document_id_cache[
                file_name
            ] = resolve_document_id(
                vector_store,
                file_name,
            )

        document_id = (
            document_id_cache[
                file_name
            ]
        )

        results = retriever.retrieve(
            query=question,
            top_k=top_k,
            document_id=document_id,
            similarity_threshold=(
                threshold
            ),
        )

        print()
        print(
            f"[{case_id}] "
            f"{category}"
        )
        print(
            f"Q: {question}"
        )
        print(
            "Retrieved: "
            f"{format_pages(results)}"
        )

        if should_reject:
            negative_count += 1

            rejected = (
                len(results) == 0
            )

            if rejected:
                negative_rejected_count += 1

            status = (
                "PASS"
                if rejected
                else "FAIL"
            )

            print(
                "Expected : REJECT"
            )
            print(
                f"Result   : {status}"
            )

            continue

        positive_count += 1

        hit_1 = hit_at_k(
            results,
            expected_pages,
            1,
        )

        hit_3 = hit_at_k(
            results,
            expected_pages,
            3,
        )

        hit_5 = hit_at_k(
            results,
            expected_pages,
            5,
        )

        if hit_1:
            hit_1_count += 1

        if hit_3:
            hit_3_count += 1

        if hit_5:
            hit_5_count += 1

        rank = first_relevant_rank(
            results,
            expected_pages,
        )

        if rank is not None:
            reciprocal_rank_sum += (
                1 / rank
            )

        status = (
            "PASS"
            if hit_5
            else "FAIL"
        )

        expected_text = ", ".join(
            str(page)
            for page
            in sorted(expected_pages)
        )

        print(
            "Expected : "
            f"page {expected_text}"
        )

        print(
            "First Hit: "
            f"{rank or '-'}"
        )

        print(
            f"Result   : {status}"
        )

    hit_1_rate = (
        hit_1_count
        / positive_count
        if positive_count
        else 0
    )

    hit_3_rate = (
        hit_3_count
        / positive_count
        if positive_count
        else 0
    )

    hit_5_rate = (
        hit_5_count
        / positive_count
        if positive_count
        else 0
    )

    mrr = (
        reciprocal_rank_sum
        / positive_count
        if positive_count
        else 0
    )

    negative_rejection_rate = (
        negative_rejected_count
        / negative_count
        if negative_count
        else 0
    )

    print()
    print(
        "=" * 72
    )
    print(
        "Summary"
    )
    print(
        "=" * 72
    )

    print(
        f"Total Questions     : "
        f"{len(dataset)}"
    )

    print(
        f"Positive Questions  : "
        f"{positive_count}"
    )

    print(
        f"Negative Questions  : "
        f"{negative_count}"
    )

    print()

    print(
        f"Hit@1               : "
        f"{hit_1_count}/"
        f"{positive_count} "
        f"({hit_1_rate:.1%})"
    )

    print(
        f"Hit@3               : "
        f"{hit_3_count}/"
        f"{positive_count} "
        f"({hit_3_rate:.1%})"
    )

    print(
        f"Hit@5               : "
        f"{hit_5_count}/"
        f"{positive_count} "
        f"({hit_5_rate:.1%})"
    )

    print(
        f"MRR                  : "
        f"{mrr:.3f}"
    )

    print()

    print(
        "Negative Rejection  : "
        f"{negative_rejected_count}/"
        f"{negative_count} "
        f"("
        f"{negative_rejection_rate:.1%}"
        f")"
    )

    print(
        "=" * 72
    )


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate RAG retrieval "
            "with manually labeled "
            "ground truth."
        )
    )

    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Retriever Top-K",
    )

    parser.add_argument(
        "--threshold",
        type=float,
        default=0.4,
        help=(
            "Similarity threshold"
        ),
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    evaluate(
        top_k=args.top_k,
        threshold=args.threshold,
    )