import json
import os
from pathlib import Path
import sys
import time

# Ensure backend root is on sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from database.database import SessionLocal
from models.user import User
from services.chat.chat_service import ChatService
from services.chat.citation_validator import (
    extract_markers,
    is_not_found,
    validate_citations,
)


def main():
    db = SessionLocal()
    try:
        # Dynamically look up existing Org 1 user
        user = db.query(User).filter(User.organization_id == 1).first()
        if not user:
            print("Error: No Org 1 user found in DB.")
            return

        print(f"Loaded existing Org 1 User: ID={user.id}, Email={user.email}, Role={user.role}")

        bench_file = backend_dir / "eval" / "bench_org1.jsonl"
        target_ids = {"mba-02", "mba-09", "web-03", "none-01", "none-02", "none-03"}
        target_questions = []

        with open(bench_file, "r") as f:
            for line in f:
                if not line.strip():
                    continue
                item = json.loads(line)
                if item.get("id") in target_ids:
                    target_questions.append(item)

        order = {
            "mba-02": 1,
            "mba-09": 2,
            "web-03": 3,
            "none-01": 4,
            "none-02": 5,
            "none-03": 6,
        }
        target_questions.sort(key=lambda q: order.get(q.get("id"), 99))

        chat_service = ChatService()

        for idx, item in enumerate(target_questions):
            if idx > 0:
                print("\nWaiting 22s for Voyage AI rate limit (3 RPM)...")
                time.sleep(22)

            qid = item["id"]
            question = item["question"]
            expected_pages = item.get("pages", [])
            answerable = item.get("answerable", True)

            print("\n" + "=" * 80)
            print(f"Question ID: {qid}")
            print(f"Question:    {question}")
            print(f"Answerable:  {answerable} | Expected Pages: {expected_pages}")
            print("-" * 80)

            # Invalidate any old cache for clean live run
            cache_key = chat_service._get_cache_key(organization_id=1, question=question)
            try:
                chat_service.redis.delete(cache_key)
            except Exception:
                pass

            prep = chat_service._prepare_chat(
                db=db,
                question=question,
                organization_id=1,
                user_id=user.id,
            )
            session, prompt, citations, cache_key = prep
            chunk_texts = getattr(prep, "chunk_texts", {})

            # Generate response from AI provider
            raw_answer = chat_service.ai_service.generate_answer(prompt=prompt)

            # Validate citations with chunk_texts support check
            val_res = validate_citations(
                answer=raw_answer,
                citations=citations,
                chunk_texts=chunk_texts,
            )

            clean_answer = val_res.clean_answer
            final_citations = val_res.used_citations
            marker_actions = val_res.marker_actions
            initial_markers = extract_markers(raw_answer)
            final_markers = extract_markers(clean_answer)

            print(f"Raw Generated Answer:\n{raw_answer}\n")
            print(f"Clean Final Answer:\n{clean_answer}\n")
            print(f"Is 'Not Found' Answer: {is_not_found(clean_answer)}")
            print(f"Initial Markers Found: {initial_markers}")
            print(f"Surviving Markers:     {final_markers}")

            print("\nMarkers Kept or Removed (with Reason):")
            if marker_actions:
                for action in marker_actions:
                    m = action.get("marker", "N/A")
                    act = action.get("action", "").upper()
                    reason = action.get("reason", "")
                    print(f"  - [{act}] Marker [{m}]: {reason}")
            else:
                if is_not_found(clean_answer):
                    print("  - [NOT_FOUND] Answer indicates information not found in documents.")
                elif not initial_markers:
                    print("  - [NONE] No citation markers were present in the generated answer.")
                else:
                    print("  - [KEPT] All markers retained.")

            print(f"\nFinal Citations Returned ({len(final_citations)}):")
            if final_citations:
                for cit in final_citations:
                    cid = cit.get("id")
                    doc = cit.get("document")
                    page = cit.get("page_number")
                    snippet = cit.get("snippet")
                    print(f"  [{cid}] Document: {doc}")
                    print(f"      Page:     {page}")
                    print(f"      Snippet:  {snippet}")
            else:
                print("  (Empty citations list - no sources cited)")

    finally:
        db.close()


if __name__ == "__main__":
    main()
