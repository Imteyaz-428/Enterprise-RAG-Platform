"""Retrieval benchmark: Hit@K, MRR, page match, duplicate rate, latency.

Run from the backend/ folder (Postgres must be up and documents processed):

    python eval/bench_retrieval.py --org-id 1 --label baseline
    python eval/bench_retrieval.py --org-id 1 --label no-rerank --no-rerank

A question counts as a HIT when one of the top-K retrieved chunks contains any
string from "must_contain_any" (case/whitespace-insensitive). Matching on text
instead of document ids keeps the benchmark valid when the same PDF has been
uploaded several times.
"""
import argparse
import csv
import json
import re
import sys
import time
import unicodedata
from datetime import datetime
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent
ROOT = EVAL_DIR.parent
RESULTS_DIR = EVAL_DIR / "results"
sys.path.insert(0, str(ROOT))

CSV_FIELDS = [
    "timestamp", "label", "k", "no_rerank", "n_scored", "n_errors",
    "hit@1", "hit@3", "hit@5", "mrr", "page_match", "dup_rate",
    "latency_ms_mean", "latency_ms_p95",
]


def norm(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "").lower()
    return re.sub(r"\s+", " ", text).strip()


def load_dataset(path: Path) -> list[dict]:
    items = []
    with open(path, encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                items.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise SystemExit(f"{path}:{line_no}: invalid JSON ({e})")
    return items


def evaluate(items, retrieve_fn, corpus, k):
    """Pure logic: retrieve_fn(question) -> list of results with
    .chunk.chunk_text, .chunk.page_number and .document.original_filename."""
    rows = []
    for item in items:
        row = {
            "id": item["id"],
            "source": item.get("source", ""),
            "question": item["question"],
        }

        if item.get("answerable", True) is False:
            row["status"] = "skipped_unanswerable"
            rows.append(row)
            continue

        anchors = [norm(a) for a in item["must_contain_any"]]
        if not any(a in text for text in corpus for a in anchors):
            # The evidence is not in the ingested corpus: a dataset problem,
            # not a retrieval problem.
            row["status"] = "dataset_error"
            rows.append(row)
            continue

        started = time.perf_counter()
        try:
            results = retrieve_fn(item["question"], item.get("history"))
        except Exception as e:  # noqa: BLE001
            row["status"] = "error"
            row["error"] = f"{type(e).__name__}: {e}"
            rows.append(row)
            continue
        latency_ms = (time.perf_counter() - started) * 1000

        top = results[:k]
        rank, page_ok = None, None
        for pos, r in enumerate(top, 1):
            text = norm(r.chunk.chunk_text)
            if any(a in text for a in anchors):
                rank = pos
                pages = item.get("pages")
                page_ok = None if not pages else r.chunk.page_number in pages
                break

        texts = [norm(r.chunk.chunk_text) for r in top]
        dup_rate = 1 - len(set(texts)) / len(texts) if texts else 0.0

        row.update(
            status="hit" if rank else "miss",
            rank=rank,
            page_ok=page_ok,
            dup_rate=round(dup_rate, 3),
            latency_ms=round(latency_ms, 1),
            top1_doc=top[0].document.original_filename if top else None,
            top1_page=top[0].chunk.page_number if top else None,
            top1_text=(top[0].chunk.chunk_text[:140].replace("\n", " ") if top else None),
        )
        rows.append(row)
    return rows


def summarize(rows, k):
    scored = [r for r in rows if r["status"] in ("hit", "miss")]
    n = len(scored)
    out = {
        "n_scored": n,
        "n_errors": sum(r["status"] == "error" for r in rows),
        "n_dataset_errors": sum(r["status"] == "dataset_error" for r in rows),
        "n_unanswerable_skipped": sum(r["status"] == "skipped_unanswerable" for r in rows),
    }
    if n == 0:
        return out

    for cutoff in (1, 3, 5):
        if cutoff <= k:
            out[f"hit@{cutoff}"] = round(
                sum(1 for r in scored if r["rank"] and r["rank"] <= cutoff) / n, 3
            )
    out["mrr"] = round(sum(1 / r["rank"] for r in scored if r["rank"]) / n, 3)

    with_pages = [r for r in scored if r["rank"] and r["page_ok"] is not None]
    out["page_match"] = (
        round(sum(bool(r["page_ok"]) for r in with_pages) / len(with_pages), 3)
        if with_pages else None
    )
    out["dup_rate"] = round(sum(r["dup_rate"] for r in scored) / n, 3)

    lat = sorted(r["latency_ms"] for r in scored)
    out["latency_ms_mean"] = round(sum(lat) / n, 1)
    out["latency_ms_p95"] = lat[min(n - 1, int(0.95 * n))]
    return out


def print_report(label, k, summary, rows):
    print(f"\n=== Retrieval benchmark: {label} (K={k}) ===")
    for key, value in summary.items():
        print(f"  {key:<24} {value}")

    by_source: dict[str, list] = {}
    for r in rows:
        if r["status"] in ("hit", "miss"):
            by_source.setdefault(r["source"], []).append(r)
    if by_source:
        print("\n  By source (hits / questions):")
        for source, group in sorted(by_source.items()):
            hits = sum(r["status"] == "hit" for r in group)
            print(f"    {source:<16} {hits}/{len(group)}")

    misses = [r for r in rows if r["status"] == "miss"]
    if misses:
        print("\n  Misses (what was ranked first instead):")
        for r in misses:
            print(f"    [{r['id']}] {r['question']}")
            print(f"        top1: {r['top1_doc']} p.{r['top1_page']}: {r['top1_text']}")

    for status, title in (
        ("dataset_error", "Evidence not found in the ingested corpus (fix dataset or upload the PDF)"),
        ("error", "Retrieval raised an error"),
    ):
        bad = [r for r in rows if r["status"] == status]
        if bad:
            print(f"\n  WARNING - {title}:")
            for r in bad:
                print(f"    [{r['id']}] {r.get('error', '')}")


def save_results(args, k, summary, rows):
    RESULTS_DIR.mkdir(exist_ok=True)
    now = datetime.now()
    stamp = now.strftime("%Y%m%d-%H%M%S")

    path = RESULTS_DIR / f"{args.label}_{stamp}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(
            {"label": args.label, "timestamp": now.isoformat(timespec="seconds"),
             "k": k, "org_id": args.org_id, "no_rerank": args.no_rerank,
             "summary": summary, "rows": rows},
            f, indent=2, ensure_ascii=False,
        )

    csv_path = RESULTS_DIR / "summary.csv"
    is_new = not csv_path.exists()
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, restval="", extrasaction="ignore")
        if is_new:
            writer.writeheader()
        writer.writerow({
            "timestamp": now.isoformat(timespec="seconds"),
            "label": args.label, "k": k, "no_rerank": args.no_rerank, **summary,
        })
    print(f"\n  Saved: {path.relative_to(ROOT)} and eval/results/summary.csv")


def main():
    parser = argparse.ArgumentParser(description="Retrieval benchmark")
    parser.add_argument("--org-id", type=int, required=True)
    parser.add_argument("--rewrite", action="store_true",
                        help="rewrite follow-up questions with the query rewriter (Stage 2.3)")
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--dataset", type=Path, default=EVAL_DIR / "bench_dataset.jsonl")
    parser.add_argument("--label", default="run")
    parser.add_argument("--no-rerank", action="store_true",
                        help="skip the cross-encoder to measure its contribution")
    parser.add_argument("--min-interval", type=float, default=21.0,
                        help="seconds between live embedding calls (21 = free tier; 0 once billing is on)")
    args = parser.parse_args()

    # Imported here so the pure functions above can be tested without a DB.
    from database.database import SessionLocal
    from models.document import Document
    from models.document_chunk import DocumentChunk
    from services.chat.retrieval_service import RetrievalService

    items = load_dataset(args.dataset)
    db = SessionLocal()
    try:
        rows_db = (
            db.query(DocumentChunk.chunk_text)
            .join(Document, Document.id == DocumentChunk.document_id)
            .filter(Document.organization_id == args.org_id)
            .all()
        )
        corpus = [norm(r[0]) for r in rows_db]
        if not corpus:
            raise SystemExit(
                f"No chunks found for organization {args.org_id}. "
                "Upload documents and wait for status 'completed' first."
            )

        service = RetrievalService()
        from embed_cache import install_embedding_cache
        install_embedding_cache(min_interval=args.min_interval)
        if args.no_rerank:
            service.reranking_service.rerank = (
                lambda query, results, top_k=5: results[:top_k]
            )

        def retrieve_fn(question, history=None):
            if history and args.rewrite:
                from services.chat.query_rewriter import rewrite_query
                original = question
                question = rewrite_query(history=history, question=question)
                print(f"  [rewrite] {original!r} -> {question!r}")
            try:
                return service.retrieve(
                    db=db, question=question,
                    organization_id=args.org_id, top_k=args.k,
                )
            except Exception:
                db.rollback()  # keep the session usable after a failed query
                raise

        rows = evaluate(items, retrieve_fn, corpus, args.k)
    finally:
        db.close()

    summary = summarize(rows, args.k)
    print_report(args.label, args.k, summary, rows)
    save_results(args, args.k, summary, rows)

    if summary["n_scored"] == 0 and summary["n_errors"]:
        sys.exit(1)


if __name__ == "__main__":
    main()