from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from rag.reranker import Reranker
from rag.retriever import Retriever
from rag.vector_store import VectorStore

from evaluate_retrieval import (
    DATASET_PATH,
    first_relevant_rank,
    format_pages,
    get_result_page,
    hit_at_k,
    load_dataset,
    resolve_document_id,
)


def empty_metrics():
    return {"hit1": 0, "hit3": 0, "hit5": 0, "rr": 0.0}


def update_metrics(metrics, results, expected_pages):
    if hit_at_k(results, expected_pages, 1):
        metrics["hit1"] += 1
    if hit_at_k(results, expected_pages, 3):
        metrics["hit3"] += 1
    if hit_at_k(results, expected_pages, 5):
        metrics["hit5"] += 1

    rank = first_relevant_rank(results, expected_pages)
    if rank is not None:
        metrics["rr"] += 1 / rank
    return rank


def format_reranked(results):
    if not results:
        return "-"

    parts = []
    for item in results:
        page = get_result_page(item)
        dense_rank = item.get("retrieval_rank", item.get("rank"))
        sim = item.get("similarity")
        score = item.get("rerank_score")

        sim_text = f"{sim:.3f}" if isinstance(sim, (int, float)) else "-"
        score_text = f"{score:.3f}" if isinstance(score, (int, float)) else "-"

        parts.append(
            f"{page}[D{dense_rank}, sim={sim_text}, rerank={score_text}]"
        )
    return ", ".join(parts)


def best_relevant_score(results, expected_pages):
    scores = [
        item["rerank_score"]
        for item in results
        if get_result_page(item) in expected_pages
        and isinstance(item.get("rerank_score"), (int, float))
    ]
    return max(scores) if scores else None


def rate(n, d):
    return n / d if d else 0.0


def print_metrics(label, metrics, positive_count):
    mrr = metrics["rr"] / positive_count if positive_count else 0.0
    print(
        f"{label:<10}"
        f"Hit@1={metrics['hit1']}/{positive_count} "
        f"({rate(metrics['hit1'], positive_count):.1%}) | "
        f"Hit@3={metrics['hit3']}/{positive_count} "
        f"({rate(metrics['hit3'], positive_count):.1%}) | "
        f"Hit@5={metrics['hit5']}/{positive_count} "
        f"({rate(metrics['hit5'], positive_count):.1%}) | "
        f"MRR={mrr:.3f}"
    )



def evaluate_evidence_thresholds(
    cases,
    thresholds,
    final_top_k,
):
    """
    模拟 Cross-Encoder Evidence Guard。

    对 rerank_score 应用阈值后，再取 Final Top-K：
    - Positive Accept: 正样本是否还保留至少一个候选
    - Positive Hit@5: 阈值过滤后是否仍命中正确页面
    - Negative Reject: 负样本是否被过滤为空
    """
    print()
    print("=" * 88)
    print("Evidence Threshold Sweep")
    print("=" * 88)
    print(
        f"{'Threshold':>10} | "
        f"{'Positive Accept':>17} | "
        f"{'Positive Hit@5':>16} | "
        f"{'Negative Reject':>17}"
    )
    print("-" * 88)

    for guard_threshold in thresholds:
        positive_count = 0
        negative_count = 0

        positive_accepted = 0
        positive_hit_5 = 0
        negative_rejected = 0

        for case in cases:
            filtered = [
                item
                for item in case["results"]
                if item["rerank_score"]
                >= guard_threshold
            ][:final_top_k]

            if case["should_reject"]:
                negative_count += 1

                if not filtered:
                    negative_rejected += 1

                continue

            positive_count += 1

            if filtered:
                positive_accepted += 1

            if hit_at_k(
                filtered,
                case["expected_pages"],
                5,
            ):
                positive_hit_5 += 1

        print(
            f"{guard_threshold:>10.2f} | "
            f"{positive_accepted:>2}/"
            f"{positive_count:<2} "
            f"({rate(positive_accepted, positive_count):>6.1%}) | "
            f"{positive_hit_5:>2}/"
            f"{positive_count:<2} "
            f"({rate(positive_hit_5, positive_count):>6.1%}) | "
            f"{negative_rejected:>2}/"
            f"{negative_count:<2} "
            f"({rate(negative_rejected, negative_count):>6.1%})"
        )

    print("-" * 88)
    print(
        "说明：该表只用于当前 Benchmark 的阈值分析，"
        "不能直接当作通用生产阈值。"
    )

def evaluate(candidate_top_k=8, final_top_k=5, threshold=0.45):
    if candidate_top_k <= 0 or final_top_k <= 0:
        raise ValueError("Top-K 必须大于 0")
    if final_top_k > candidate_top_k:
        raise ValueError("final_top_k 不能大于 candidate_top_k")

    dataset = load_dataset()
    vector_store = VectorStore()
    retriever = Retriever(vector_store=vector_store)

    print()
    print("=" * 88)
    print("Dense vs Dense + Cross-Encoder Reranker Evaluation")
    print("=" * 88)
    print(f"Dataset         : {DATASET_PATH.name}")
    print(f"Candidate Top-K : {candidate_top_k}")
    print(f"Final Top-K     : {final_top_k}")
    print(f"Threshold       : {threshold:.2f}")
    print("=" * 88)
    print("Loading Cross-Encoder...")

    load_start = time.perf_counter()
    reranker = Reranker()
    model_load_seconds = time.perf_counter() - load_start
    print(f"Cross-Encoder loaded in {model_load_seconds:.2f}s")

    document_id_cache = {}
    dense_metrics = empty_metrics()
    rerank_metrics = empty_metrics()

    positive_count = 0
    negative_count = 0
    dense_negative_rejected = 0
    rerank_negative_rejected = 0

    positive_scores = []
    negative_scores = []
    latencies = []
    threshold_cases = []

    for item in dataset:
        case_id = item["id"]
        category = item.get("category", "unknown")
        question = item["question"]
        file_name = item["file_name"]
        expected_pages = set(item.get("expected_pages", []))
        should_reject = bool(item.get("should_reject", False))

        if file_name not in document_id_cache:
            document_id_cache[file_name] = resolve_document_id(
                vector_store,
                file_name,
            )
        document_id = document_id_cache[file_name]

        dense_candidates = retriever.retrieve(
            query=question,
            top_k=candidate_top_k,
            document_id=document_id,
            similarity_threshold=threshold,
        )

        dense_results = dense_candidates[:final_top_k]

        start = time.perf_counter()
        reranked_all = reranker.rerank(
            query=question,
            candidates=dense_candidates,
            top_n=len(dense_candidates),
        )
        latency_ms = (time.perf_counter() - start) * 1000
        latencies.append(latency_ms)

        reranked_results = reranked_all[:final_top_k]

        threshold_cases.append(
            {
                "id": case_id,
                "should_reject": should_reject,
                "expected_pages": expected_pages,
                "results": reranked_all,
            }
        )

        print()
        print(f"[{case_id}] {category}")
        print(f"Q: {question}")
        print(f"Dense    : {format_pages(dense_results)}")
        print(f"Reranked : {format_reranked(reranked_results)}")
        print(f"Latency  : {latency_ms:.1f} ms")

        if should_reject:
            negative_count += 1

            dense_rejected = len(dense_results) == 0
            rerank_rejected = len(reranked_results) == 0

            dense_negative_rejected += int(dense_rejected)
            rerank_negative_rejected += int(rerank_rejected)

            top_score = (
                reranked_all[0]["rerank_score"]
                if reranked_all
                else None
            )
            negative_scores.append((case_id, top_score))

            print("Expected : REJECT")
            print(f"Dense    : {'PASS' if dense_rejected else 'FAIL'}")
            print(f"Reranker : {'PASS' if rerank_rejected else 'FAIL'}")
            if top_score is not None:
                print(f"Top Rerank Score: {top_score:.4f}")
            continue

        positive_count += 1

        dense_rank = update_metrics(
            dense_metrics,
            dense_results,
            expected_pages,
        )
        rerank_rank = update_metrics(
            rerank_metrics,
            reranked_results,
            expected_pages,
        )

        relevant_score = best_relevant_score(
            reranked_all,
            expected_pages,
        )
        positive_scores.append((case_id, relevant_score))

        expected_text = ", ".join(
            str(page) for page in sorted(expected_pages)
        )

        print(f"Expected : page {expected_text}")
        print(f"Dense First Hit  : {dense_rank or '-'}")
        print(f"Rerank First Hit : {rerank_rank or '-'}")
        if relevant_score is not None:
            print(f"Best Relevant Rerank Score: {relevant_score:.4f}")

    print()
    print("=" * 88)
    print("A/B Summary")
    print("=" * 88)
    print(f"Positive Questions : {positive_count}")
    print(f"Negative Questions : {negative_count}")
    print()

    print_metrics("Dense", dense_metrics, positive_count)
    print_metrics("Reranker", rerank_metrics, positive_count)

    print()
    print(
        "Dense Negative Rejection    : "
        f"{dense_negative_rejected}/{negative_count} "
        f"({rate(dense_negative_rejected, negative_count):.1%})"
    )
    print(
        "Reranker Negative Rejection : "
        f"{rerank_negative_rejected}/{negative_count} "
        f"({rate(rerank_negative_rejected, negative_count):.1%})"
    )

    print()
    print("注意：当前未设置 rerank_score 拒答阈值，Reranker 只负责重新排序。")

    print()
    print("=" * 88)
    print("Rerank Score Diagnostics")
    print("=" * 88)
    print("Positive: best score on a relevant page")
    for case_id, score in positive_scores:
        print(f"  {case_id}: {score:.4f}" if score is not None else f"  {case_id}: -")

    print()
    print("Negative: highest score among retrieved candidates")
    for case_id, score in negative_scores:
        print(f"  {case_id}: {score:.4f}" if score is not None else f"  {case_id}: -")

    evaluate_evidence_thresholds(
        cases=threshold_cases,
        thresholds=[
            -4.0,
            -3.0,
            -2.0,
            -1.0,
            -0.5,
            0.0,
        ],
        final_top_k=final_top_k,
    )

    if latencies:
        print()
        print("=" * 88)
        print("Reranker Cost")
        print("=" * 88)
        print(f"Model Load Time : {model_load_seconds:.2f} s")
        print(f"Average Latency : {sum(latencies) / len(latencies):.1f} ms/query")
        print(f"Max Latency     : {max(latencies):.1f} ms/query")

    print("=" * 88)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Compare Dense Retrieval with Dense + Cross-Encoder Reranking."
    )
    parser.add_argument("--candidate-top-k", type=int, default=8)
    parser.add_argument("--final-top-k", type=int, default=5)
    parser.add_argument("--threshold", type=float, default=0.45)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    evaluate(
        candidate_top_k=args.candidate_top_k,
        final_top_k=args.final_top_k,
        threshold=args.threshold,
    )
