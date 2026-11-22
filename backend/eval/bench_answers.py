"""Answer-level benchmark: refusal rate, answered-with-citation rate,
fraction of citations containing anchor, and not-found rate for unanswerables.

Run from backend/ directory:
    python eval/bench_answers.py --org-id 1 --dataset eval/bench_org1.jsonl --label answers-before-prompt
"""
import argparse
import csv
from datetime import datetime
import json
from pathlib import Path
import re
import sys
import time
import unicodedata

EVAL_DIR = Path(__file__).resolve().parent
ROOT = EVAL_DIR.parent
RESULTS_DIR = EVAL_DIR / "results"
sys.path.insert(0, str(ROOT))

CSV_FIELDS = [
    "timestamp",
    "label",
    "org_id",
    "n_total",
    "n_answerable",
    "n_unanswerable",
    "n_errors",
    "refusal_rate",
    "answered_with_citation_rate",
    "citation_anchor_rate",
    "not_found_rate",
    "latency_ms_mean",
    "latency_ms_p95",
]


def norm(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "").lower()
    return re.sub(r"\s+", " ", text).strip()


def load_dataset(path: Path) -> list[dict]:
    p = Path(path)
    if not p.exists():
        if (EVAL_DIR / p.name).exists():
            p = EVAL_DIR / p.name
        elif (ROOT / p).exists():
            p = ROOT / p
        elif (EVAL_DIR / p).exists():
            p = EVAL_DIR / p
    items = []
    with open(p, encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                items.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise SystemExit(f"{p}:{line_no}: invalid JSON ({e})")
    return items


def build_citations_and_chunk_texts(results) -> tuple[list[dict], dict[int, str], list]:
    vis = set()
    unique_results = []
    for result in results:
        doc_id = getattr(getattr(result, "document", None), "id", None)
        chunk_idx = getattr(getattr(result, "chunk", None), "chunk_index", None)
        key = (doc_id, chunk_idx)
        if key in vis:
            continue
        vis.add(key)
        unique_results.append(result)

    citations = []
    chunk_texts = {}
    for index, result in enumerate(unique_results, start=1):
        raw_text = getattr(result.chunk, "chunk_text", None)
        if isinstance(raw_text, str):
            full_chunk_text = raw_text
            snippet = " ".join(raw_text.split())[:200]
        elif hasattr(result, "text") and isinstance(result.text, str):
            full_chunk_text = result.text
            snippet = " ".join(result.text.split())[:200]
        elif raw_text is not None and type(raw_text).__name__ != "MagicMock":
            full_chunk_text = str(raw_text)
            snippet = " ".join(str(raw_text).split())[:200]
        else:
            full_chunk_text = ""
            snippet = None

        chunk_texts[index] = full_chunk_text

        page_no = getattr(result.chunk, "page_number", None)
        page_number = page_no if isinstance(page_no, int) else None

        doc_id = getattr(result.document, "id", None)
        document_id = doc_id if isinstance(doc_id, int) else None

        chunk_idx = getattr(result.chunk, "chunk_index", 0)
        chunk_index = chunk_idx if isinstance(chunk_idx, int) else 0

        doc_filename = getattr(result.document, "original_filename", "")
        document = doc_filename if isinstance(doc_filename, str) else str(doc_filename)

        citations.append(
            {
                "id": index,
                "document": document,
                "chunk_index": chunk_index,
                "document_id": document_id,
                "page_number": page_number,
                "snippet": snippet,
            }
        )
    return citations, chunk_texts, unique_results


def evaluate_single_answer(
    item: dict,
    raw_answer: str,
    citations: list[dict],
    chunk_texts: dict[int, str],
    latency_ms: float = 0.0,
    trial: int = 1,
) -> dict:
    from services.chat.citation_validator import is_not_found, validate_citations

    val_res = validate_citations(
        answer=raw_answer,
        citations=citations,
        chunk_texts=chunk_texts,
    )
    clean_answer = val_res.clean_answer
    used_citations = val_res.used_citations

    answerable = item.get("answerable", True) is not False
    is_not_found_ans = is_not_found(clean_answer)

    row = {
        "id": item["id"],
        "trial": trial,
        "source": item.get("source", ""),
        "question": item["question"],
        "answerable": answerable,
        "raw_answer": raw_answer,
        "clean_answer": clean_answer,
        "latency_ms": round(latency_ms, 1),
        "status": "success",
        "marker_actions": getattr(val_res, "marker_actions", []),
        "invalid_markers": getattr(val_res, "invalid_markers", []),
    }

    if answerable:
        row["is_refusal"] = is_not_found_ans
        row["answered_with_citation"] = (not is_not_found_ans) and (len(used_citations) > 0)
        row["total_citations"] = len(used_citations)

        anchors = [norm(a) for a in item.get("must_contain_any", [])]
        supported = 0
        citation_details = []
        for cit in used_citations:
            cid = cit.get("id")
            ctext = norm(chunk_texts.get(cid, ""))
            has_anchor = any(a in ctext for a in anchors) if anchors else False
            if has_anchor:
                supported += 1
            citation_details.append(
                {
                    "id": cid,
                    "document": cit.get("document"),
                    "page_number": cit.get("page_number"),
                    "snippet": cit.get("snippet", ""),
                    "has_anchor": has_anchor,
                }
            )
        row["supported_citations"] = supported
        row["citation_details"] = citation_details
        row["final_citations"] = used_citations
    else:
        row["is_not_found"] = is_not_found_ans
        row["final_citations"] = used_citations

    return row


def summarize_answers(rows: list[dict]) -> dict:
    answerable_rows = [r for r in rows if r.get("answerable") is True and r.get("status") == "success"]
    unanswerable_rows = [r for r in rows if r.get("answerable") is False and r.get("status") == "success"]
    error_rows = [r for r in rows if r.get("status") == "error"]

    n_ans = len(answerable_rows)
    n_unans = len(unanswerable_rows)

    summary = {
        "n_total": len(rows),
        "n_answerable": n_ans,
        "n_unanswerable": n_unans,
        "n_errors": len(error_rows),
    }

    if n_ans > 0:
        summary["refusal_rate"] = round(
            sum(1 for r in answerable_rows if r.get("is_refusal")) / n_ans, 3
        )
        summary["answered_with_citation_rate"] = round(
            sum(1 for r in answerable_rows if r.get("answered_with_citation")) / n_ans, 3
        )
        total_cits = sum(r.get("total_citations", 0) for r in answerable_rows)
        supported_cits = sum(r.get("supported_citations", 0) for r in answerable_rows)
        summary["citation_anchor_rate"] = (
            round(supported_cits / total_cits, 3) if total_cits > 0 else 0.0
        )
        summary["total_citations"] = total_cits
        summary["supported_citations"] = supported_cits
    else:
        summary["refusal_rate"] = 0.0
        summary["answered_with_citation_rate"] = 0.0
        summary["citation_anchor_rate"] = 0.0
        summary["total_citations"] = 0
        summary["supported_citations"] = 0

    if n_unans > 0:
        summary["not_found_rate"] = round(
            sum(1 for r in unanswerable_rows if r.get("is_not_found")) / n_unans, 3
        )
    else:
        summary["not_found_rate"] = 0.0

    lat = sorted(
        r["latency_ms"]
        for r in rows
        if "latency_ms" in r and r.get("status") == "success"
    )
    if lat:
        summary["latency_ms_mean"] = round(sum(lat) / len(lat), 1)
        summary["latency_ms_p95"] = lat[min(len(lat) - 1, int(0.95 * len(lat)))]
    else:
        summary["latency_ms_mean"] = 0.0
        summary["latency_ms_p95"] = 0.0

    return summary


def print_report(label: str, summary: dict, rows: list[dict]):
    print(f"\n=== Answers benchmark: {label} ===")
    for key, value in summary.items():
        print(f"  {key:<28} {value}")

    unanswerable = [r for r in rows if r.get("answerable") is False and r.get("status") == "success"]
    if unanswerable:
        print(f"\n--- Unanswerable Trials Overview ({len(unanswerable)}) ---")
        for r in unanswerable:
            trial_str = f" [trial {r['trial']}]" if "trial" in r else ""
            print(f"  [{r['id']}]{trial_str} {r['question']}")
            print(f"      Clean Answer: {r.get('clean_answer')}")
            print(f"      Not Found:    {r.get('is_not_found')} (target: True)")
            print(f"      Citations:    {len(r.get('final_citations', []))}")

    non_refusing = [
        r for r in rows
        if r.get("answerable") is False
        and not r.get("is_not_found")
        and r.get("status") == "success"
    ]
    print(f"\n--- Unanswerable Trials That Did NOT Refuse ({len(non_refusing)}) ---")
    if non_refusing:
        for r in non_refusing:
            trial_str = f" [trial {r['trial']}]" if "trial" in r else ""
            print(f"  [{r['id']}]{trial_str} {r['question']}")
            print(f"      Answer: {r.get('clean_answer')}")
            if r.get("raw_answer") != r.get("clean_answer"):
                print(f"      Raw Answer: {r.get('raw_answer')}")
    else:
        print("  None (all unanswerable trials refused)")

    unsupported_cits = []
    for r in rows:
        if r.get("answerable") is True and r.get("status") == "success":
            for cd in r.get("citation_details", []):
                if not cd.get("has_anchor"):
                    unsupported_cits.append(
                        {
                            "qid": r["id"],
                            "document": cd.get("document"),
                            "page_number": cd.get("page_number"),
                            "snippet": (cd.get("snippet") or "")[:100],
                        }
                    )
    print(f"\n--- Unsupported Final Citations (Anchor Missing) ({len(unsupported_cits)}) ---")
    if unsupported_cits:
        for uc in unsupported_cits:
            print(f"  [{uc['qid']}] Document: {uc['document']}, Page: {uc['page_number']}")
            print(f"      Snippet (first 100 chars): {uc['snippet']}")
    else:
        print("  None (0 unsupported citations)")

    refusals = [r for r in rows if r.get("answerable") is True and r.get("is_refusal")]
    print(f"\n--- Refusals on Answerable Questions ({len(refusals)}) ---")
    if refusals:
        for r in refusals:
            print(f"  [{r['id']}] {r['question']}")
            print(f"      Clean Answer: {r.get('clean_answer')}")
    else:
        print("  None (0 refusals)")

    targets = [r for r in rows if r.get("id") in {"mba-02", "web-03"}]
    if targets:
        print(f"\n--- Target Inspection (mba-02 and web-03) ---")
        for r in targets:
            print(f"  [{r['id']}] {r['question']}")
            print(f"      Final Answer:    {r.get('clean_answer')}")
            print(f"      Marker Actions:  {r.get('marker_actions')}")
            print(f"      Final Citations: {r.get('final_citations')}")


def run_benchmark(
    db,
    retrieval_service,
    prompt_service,
    ai_service,
    items: list[dict],
    org_id: int,
    k: int = 5,
    repeat: int = 1,
) -> tuple[dict, list[dict]]:
    rows = []
    total = len(items)
    for idx, item in enumerate(items, 1):
        qid = item.get("id")
        question = item.get("question")
        answerable = item.get("answerable", True) is not False
        num_trials = repeat if not answerable else 1

        t_ret_0 = time.perf_counter()
        try:
            retrieved_results = retrieval_service.retrieve(
                db=db,
                question=question,
                organization_id=org_id,
                top_k=k,
            )
            citations, chunk_texts, unique_results = build_citations_and_chunk_texts(
                retrieved_results
            )
            prompt = prompt_service.build_prompt(
                history=[],
                chunks=unique_results,
                question=question,
            )
        except Exception as e:
            db.rollback()
            latency_ms = (time.perf_counter() - t_ret_0) * 1000
            print(f"[{idx}/{total}] [{qid}] Retrieval ERROR: {e}", flush=True)
            for trial in range(1, num_trials + 1):
                rows.append(
                    {
                        "id": qid,
                        "trial": trial,
                        "question": question,
                        "answerable": answerable,
                        "status": "error",
                        "error": str(e),
                        "latency_ms": round(latency_ms, 1),
                    }
                )
            continue

        for trial in range(1, num_trials + 1):
            trial_str = f" [trial {trial}/{num_trials}]" if num_trials > 1 else ""
            print(f"[{idx}/{total}] [{qid}]{trial_str} Processing: {question[:60]}...", flush=True)

            t0 = time.perf_counter()
            try:
                raw_answer = ai_service.generate_answer(prompt=prompt)
                latency_ms = (time.perf_counter() - t0) * 1000

                row = evaluate_single_answer(
                    item=item,
                    raw_answer=raw_answer,
                    citations=citations,
                    chunk_texts=chunk_texts,
                    latency_ms=latency_ms,
                    trial=trial,
                )
                rows.append(row)
                status_desc = (
                    "refusal"
                    if row.get("is_refusal")
                    else (
                        "not-found"
                        if row.get("is_not_found")
                        else f"{row.get('total_citations', 0)} cits"
                    )
                )
                print(f"      -> Done in {row['latency_ms']}ms ({status_desc})", flush=True)

            except Exception as e:
                latency_ms = (time.perf_counter() - t0) * 1000
                print(f"      -> ERROR: {e}", flush=True)
                rows.append(
                    {
                        "id": qid,
                        "trial": trial,
                        "question": question,
                        "answerable": answerable,
                        "status": "error",
                        "error": str(e),
                        "latency_ms": round(latency_ms, 1),
                    }
                )

    summary = summarize_answers(rows)
    return summary, rows


def save_results(args, summary: dict, rows: list[dict]):
    RESULTS_DIR.mkdir(exist_ok=True)
    now = datetime.now()
    stamp = now.strftime("%Y%m%d-%H%M%S")

    path = RESULTS_DIR / f"{args.label}_{stamp}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "label": args.label,
                "timestamp": now.isoformat(timespec="seconds"),
                "org_id": args.org_id,
                "dataset": str(args.dataset),
                "summary": summary,
                "rows": rows,
            },
            f,
            indent=2,
            ensure_ascii=False,
        )

    csv_path = RESULTS_DIR / "answers_summary.csv"
    is_new = not csv_path.exists()
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, restval="", extrasaction="ignore")
        if is_new:
            writer.writeheader()
        writer.writerow(
            {
                "timestamp": now.isoformat(timespec="seconds"),
                "label": args.label,
                "org_id": args.org_id,
                **summary,
            }
        )
    print(f"\n  Saved: {path.relative_to(ROOT)} and eval/results/answers_summary.csv")


def main():
    parser = argparse.ArgumentParser(description="Answer-level benchmark")
    parser.add_argument("--org-id", type=int, required=True)
    parser.add_argument("--dataset", type=Path, default=EVAL_DIR / "bench_org1.jsonl")
    parser.add_argument("--label", default="answers")
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument(
        "--min-interval",
        type=float,
        default=21.0,
        help="seconds between live embedding calls",
    )
    parser.add_argument(
        "--repeat",
        type=int,
        default=1,
        help="Number of trials for unanswerable questions",
    )
    args = parser.parse_args()

    from database.database import SessionLocal
    from services.chat.retrieval_service import RetrievalService
    from services.chat.prompt_service import PromptService
    from services.ai.ai_services import AIService
    from embed_cache import install_embedding_cache

    install_embedding_cache(min_interval=args.min_interval)

    items = load_dataset(args.dataset)
    db = SessionLocal()
    retrieval_service = RetrievalService()
    prompt_service = PromptService()
    ai_service = AIService()

    try:
        summary, rows = run_benchmark(
            db=db,
            retrieval_service=retrieval_service,
            prompt_service=prompt_service,
            ai_service=ai_service,
            items=items,
            org_id=args.org_id,
            k=args.k,
            repeat=args.repeat,
        )
    finally:
        db.close()

    print_report(args.label, summary, rows)
    save_results(args, summary, rows)


if __name__ == "__main__":
    main()
