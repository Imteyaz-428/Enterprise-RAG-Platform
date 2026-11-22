#!/usr/bin/env python3
"""
RAG Retrieval Evaluation Harness.

Computes:
- Hit@1: Ground-truth chunk ranked at position 1.
- Hit@3: Ground-truth chunk ranked in top 3.
- Hit@5: Ground-truth chunk ranked in top 5.
- MRR (Mean Reciprocal Rank): Average reciprocal rank of first relevant chunk.
- page_match: Fraction of retrieved citations with valid page numbers.
- dup_rate: Duplicate chunk rate across retrieved lists.

Usage:
  python eval/run_retrieval.py --org-id 1 --label before-<task>
  python eval/run_retrieval.py --org-id 1 --label after-<task>
"""

import os
import sys
import csv
import json
import argparse
from pathlib import Path

# Add backend directory to sys.path
repo_root = Path(__file__).resolve().parent.parent
backend_dir = repo_root / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
load_dotenv(backend_dir / ".env")

from database.database import SessionLocal
from services.chat.retrieval_service import RetrievalService


def is_relevant_chunk(chunk_obj, target_doc_id: int, expected_keywords: list[str]) -> bool:
    """Checks if a retrieved chunk matches ground truth document and semantic content."""
    doc_id = getattr(chunk_obj.document, "id", None)
    if doc_id != target_doc_id:
        return False
    
    text = (chunk_obj.chunk.chunk_text or "").lower()
    matches = sum(1 for kw in expected_keywords if kw.lower() in text)
    # Consider relevant if at least 1 significant keyword is present in matching document
    return matches >= 1


def run_evaluation(org_id: int, label: str, dataset_path: Path, results_dir: Path):
    if not dataset_path.exists():
        print(f"Error: Dataset not found at {dataset_path}")
        sys.exit(1)

    with open(dataset_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    # Load pre-computed embedding cache if present to respect rate limits
    cache_file = dataset_path.parent / ".cache" / "query_embeddings.json"
    embedding_cache = {}
    if cache_file.exists():
        with open(cache_file, "r", encoding="utf-8") as f:
            embedding_cache = json.load(f)

    db = SessionLocal()
    retrieval_service = RetrievalService()

    total_queries = len(dataset)
    hit_1 = 0
    hit_3 = 0
    hit_5 = 0
    reciprocal_ranks = []
    
    total_retrieved = 0
    total_duplicates = 0
    valid_page_matches = 0
    relevant_retrieved = 0

    print(f"\n=======================================================")
    print(f"  Running Retrieval Evaluation: [{label}] (Org ID: {org_id})")
    print(f"=======================================================")

    for item in dataset:
        query = item["query"]
        target_doc = item["document_id"]
        expected_keywords = item.get("expected_keywords", [])
        q_emb = embedding_cache.get(query)

        # Retrieve top 5
        results = retrieval_service.retrieve(
            db=db,
            question=query,
            organization_id=org_id,
            top_k=5,
            query_embedding=q_emb,
        )

        seen_chunks = set()
        first_relevant_rank = None

        for rank, res in enumerate(results, start=1):
            total_retrieved += 1
            chunk_id = getattr(res.chunk, "id", f"{res.document.id}-{res.chunk.chunk_index}")
            
            if chunk_id in seen_chunks:
                total_duplicates += 1
            else:
                seen_chunks.add(chunk_id)

            if is_relevant_chunk(res, target_doc, expected_keywords):
                relevant_retrieved += 1
                if getattr(res.chunk, "page_number", None) is not None:
                    valid_page_matches += 1
                if first_relevant_rank is None:
                    first_relevant_rank = rank

        if first_relevant_rank == 1:
            hit_1 += 1
        if first_relevant_rank is not None and first_relevant_rank <= 3:
            hit_3 += 1
        if first_relevant_rank is not None and first_relevant_rank <= 5:
            hit_5 += 1

        reciprocal_ranks.append(1.0 / first_relevant_rank if first_relevant_rank else 0.0)

    db.close()

    metrics = {
        "label": label,
        "org_id": org_id,
        "total_queries": total_queries,
        "hit_at_1": round(hit_1 / total_queries, 4),
        "hit_at_3": round(hit_3 / total_queries, 4),
        "hit_at_5": round(hit_5 / total_queries, 4),
        "mrr": round(sum(reciprocal_ranks) / total_queries, 4),
        "page_match": round(valid_page_matches / relevant_retrieved, 4) if relevant_retrieved > 0 else 0.0,
        "dup_rate": round(total_duplicates / total_retrieved, 4) if total_retrieved > 0 else 0.0,
    }

    # Save results
    results_dir.mkdir(parents=True, exist_ok=True)
    out_file = results_dir / f"{label}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    # Append to summary.csv
    summary_file = results_dir / "summary.csv"
    summary_exists = summary_file.exists()
    with open(summary_file, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(metrics.keys()))
        if not summary_exists:
            writer.writeheader()
        writer.writerow(metrics)

    # Check for comparative 'before-' file if current is 'after-'
    before_file = None
    if label.startswith("after-"):
        base_name = label[len("after-"):]
        candidate = results_dir / f"before-{base_name}.json"
        if candidate.exists():
            before_file = candidate

    display_results(metrics, before_file)


def display_results(after_metrics: dict, before_file: Path | None):
    print("\n------------------- Evaluation Results -------------------")
    if before_file is not None and before_file.exists():
        with open(before_file, "r", encoding="utf-8") as f:
            before_metrics = json.load(f)

        print(f"{'Metric':<14} | {'Before (' + before_metrics['label'] + ')':<20} | {'After (' + after_metrics['label'] + ')':<20} | {'Delta':<10}")
        print("-" * 72)
        
        for k, name in [
            ("hit_at_1", "Hit@1"),
            ("hit_at_3", "Hit@3"),
            ("hit_at_5", "Hit@5"),
            ("mrr", "MRR"),
            ("page_match", "page_match"),
            ("dup_rate", "dup_rate"),
        ]:
            b_val = before_metrics.get(k, 0.0)
            a_val = after_metrics.get(k, 0.0)
            delta = a_val - b_val
            delta_str = f"{delta:+.4f}"
            print(f"{name:<14} | {b_val:<20.4f} | {a_val:<20.4f} | {delta_str:<10}")

        print("-" * 72)

        # Regressions check
        h5_diff = after_metrics["hit_at_5"] - before_metrics["hit_at_5"]
        mrr_diff = after_metrics["mrr"] - before_metrics["mrr"]

        if h5_diff < -1e-5 or mrr_diff < -1e-5:
            print("\n🚨 REGRESSION DETECTED: Hit@5 or MRR dropped below baseline!")
            print("Recommendation: Propose a revert instead of adding more changes.")
        else:
            print("\n✅ Quality maintained or improved.")
    else:
        print(f"Label: {after_metrics['label']}")
        print(f"Hit@1:      {after_metrics['hit_at_1']:.4f}")
        print(f"Hit@3:      {after_metrics['hit_at_3']:.4f}")
        print(f"Hit@5:      {after_metrics['hit_at_5']:.4f}")
        print(f"MRR:        {after_metrics['mrr']:.4f}")
        print(f"page_match: {after_metrics['page_match']:.4f}")
        print(f"dup_rate:   {after_metrics['dup_rate']:.4f}")
        print(f"\nSaved metrics to eval/results/{after_metrics['label']}.json")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate RAG Retrieval Quality")
    parser.add_argument("--org-id", type=int, default=1, help="Organization ID to evaluate")
    parser.add_argument("--label", type=str, required=True, help="Evaluation label (e.g. before-step7, after-step7)")
    args = parser.parse_args()

    eval_dir = Path(__file__).resolve().parent
    dataset_file = eval_dir / "dataset.json"
    results_dir = eval_dir / "results"

    run_evaluation(
        org_id=args.org_id,
        label=args.label,
        dataset_path=dataset_file,
        results_dir=results_dir,
    )
