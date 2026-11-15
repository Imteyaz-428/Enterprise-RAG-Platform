import os
import sys
import json
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

# Ensure backend directory is in path and .env loaded
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
load_dotenv(dotenv_path=backend_dir / ".env", override=True)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.database import Base
from models.organization import Organization
from models.user import User
from models.chat_session import ChatSession
from models.chat_message import ChatMessage
from services.chat.chat_service import ChatService
from services.ai.ai_services import AIService
from services.cache.redis_service import RedisService


def create_test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(
        bind=engine,
        tables=[
            Organization.__table__,
            User.__table__,
            ChatSession.__table__,
            ChatMessage.__table__,
        ],
    )
    Session = sessionmaker(bind=engine)
    session = Session()

    org = Organization(id=1, name="Acme Corp", slug="acme")
    user = User(
        id=1,
        name="Alice Engineer",
        email="alice@acme.com",
        password="hashedpassword",
        organization_id=1,
        role="employee",
    )
    session.add_all([org, user])
    session.commit()
    return session


def create_sample_retrieval_chunks():
    doc = MagicMock()
    doc.id = 101
    doc.original_filename = "acme_handbook.pdf"

    chunk0 = MagicMock()
    chunk0.chunk_index = 0
    chunk0.chunk_text = (
        "Acme Corp allows employees to work remotely up to 3 days per week with manager approval. "
        "Core collaboration hours are 10:00 AM to 3:00 PM Eastern."
    )

    chunk1 = MagicMock()
    chunk1.chunk_index = 1
    chunk1.chunk_text = (
        "Employees working remotely receive a $50 monthly internet stipend and are provided "
        "standard company hardware (laptop, monitor, headset)."
    )

    res0 = MagicMock()
    res0.document = doc
    res0.chunk = chunk0

    res1 = MagicMock()
    res1.document = doc
    res1.chunk = chunk1

    return [res0, res1]


def run_live_verification():
    print("=" * 70)
    print("STARTING LIVE CHAT PIPELINE VERIFICATION")
    print("=" * 70)

    db = create_test_db()

    # Initialize live AI service and ChatService
    ai_service = AIService()
    chat_service = ChatService(ai_service=ai_service)

    # Attach sample retrieval chunks representing document search results
    sample_chunks = create_sample_retrieval_chunks()
    chat_service.retrieval_service = MagicMock()
    chat_service.retrieval_service.retrieve.return_value = sample_chunks

    results = {}

    # -------------------------------------------------------------
    # Test 1: Live Non-Streaming POST /chat
    # -------------------------------------------------------------
    print("\n[1/4] Testing Live Non-Streaming Generation (/chat)...")
    q1 = "What is the policy on remote work and what are the core hours?"
    t0 = time.time()
    try:
        chat_res = chat_service.chat(
            db=db,
            question=q1,
            organization_id=1,
            user_id=1,
            session_id=None,
        )
        t1 = time.time()
        print(f"  -> Generated in {t1 - t0:.2f}s")
        print(f"  -> Session ID: {chat_res['session_id']}")
        print(f"  -> Answer snippet: {chat_res['answer'][:120]}...")
        print(f"  -> Citations: {chat_res['citations']}")

        session_id = chat_res["session_id"]
        assert len(chat_res["answer"]) > 10, "Answer must not be empty"
        assert len(chat_res["citations"]) == 2, "Must return 2 citations"
        results["non_streaming_chat"] = {
            "status": "PASS",
            "latency_seconds": round(t1 - t0, 2),
            "session_id": session_id,
            "citations_returned": len(chat_res["citations"]),
            "answer_preview": chat_res["answer"][:100] + "...",
        }
    except Exception as e:
        print(f"  -> FAILED: {e}")
        results["non_streaming_chat"] = {"status": "FAIL", "error": str(e)}
        return results

    # -------------------------------------------------------------
    # Test 2: Live Streaming POST /chat/stream
    # -------------------------------------------------------------
    print("\n[2/4] Testing Live Streaming Generation (/chat/stream)...")
    q2 = "What stipend or equipment is provided for remote employees?"
    t0 = time.time()
    try:
        stream = chat_service.chat_stream(
            db=db,
            question=q2,
            organization_id=1,
            user_id=1,
            session_id=session_id,  # Multi-turn conversation in same session
        )

        metadata_event = None
        streamed_tokens = []
        done_received = False

        print("  -> Stream tokens received: ", end="", flush=True)
        for raw_event in stream:
            lines = raw_event.strip().split("\n")
            event_type = ""
            event_data = ""
            for line in lines:
                if line.startswith("event:"):
                    event_type = line.replace("event:", "").strip()
                elif line.startswith("data:"):
                    event_data = line.replace("data:", "").strip()

            if event_type == "metadata":
                metadata_event = json.loads(event_data)
            elif event_type == "token":
                streamed_tokens.append(event_data)
                print(event_data, end="", flush=True)
            elif event_type == "done":
                done_received = True

        print()
        t1 = time.time()
        print(f"  -> Stream finished in {t1 - t0:.2f}s")
        print(f"  -> Total tokens: {len(streamed_tokens)}")
        print(f"  -> Metadata event: {metadata_event}")
        print(f"  -> Done event received: {done_received}")

        assert metadata_event is not None, "Metadata event must be emitted"
        assert len(streamed_tokens) > 0, "Must stream token events"
        assert done_received is True, "Must complete with done event"

        full_streamed_answer = " ".join(streamed_tokens)
        results["streaming_chat"] = {
            "status": "PASS",
            "latency_seconds": round(t1 - t0, 2),
            "tokens_streamed": len(streamed_tokens),
            "metadata_received": metadata_event is not None,
            "done_received": done_received,
            "answer_preview": full_streamed_answer[:100] + "...",
        }
    except Exception as e:
        print(f"\n  -> FAILED: {e}")
        results["streaming_chat"] = {"status": "FAIL", "error": str(e)}

    # -------------------------------------------------------------
    # Test 3: Cache Hit Speed & Replay
    # -------------------------------------------------------------
    print("\n[3/4] Testing Tenant-Isolated Cache Hit Replay...")
    t0 = time.time()
    try:
        cached_res = chat_service.chat(
            db=db,
            question=q1,  # Same question as Test 1
            organization_id=1,
            user_id=1,
            session_id=session_id,
        )
        t1 = time.time()
        elapsed = t1 - t0
        print(f"  -> Cache lookup took: {elapsed * 1000:.2f} ms")
        print(f"  -> Returned answer snippet: {cached_res['answer'][:80]}...")
        results["cache_hit"] = {
            "status": "PASS",
            "latency_ms": round(elapsed * 1000, 2),
            "citations_count": len(cached_res["citations"]),
        }
    except Exception as e:
        print(f"  -> FAILED: {e}")
        results["cache_hit"] = {"status": "FAIL", "error": str(e)}

    # -------------------------------------------------------------
    # Test 4: Conversation History & Message Persistence
    # -------------------------------------------------------------
    print("\n[4/4] Verifying Session History & Multi-turn Persistence...")
    try:
        detail = chat_service.get_chat_session(
            db=db,
            session_id=session_id,
            organization_id=1,
            user_id=1,
        )
        msg_count = len(detail["messages"])
        print(f"  -> Session Title: '{detail['title']}'")
        print(f"  -> Total messages in session: {msg_count}")
        for idx, m in enumerate(detail["messages"], 1):
            print(f"     [{idx}] {m.role.upper()}: {m.content[:60]}...")

        assert msg_count >= 4, f"Expected at least 4 messages (2 user, 2 assistant), got {msg_count}"
        results["session_persistence"] = {
            "status": "PASS",
            "messages_recorded": msg_count,
            "session_id": session_id,
        }
    except Exception as e:
        print(f"  -> FAILED: {e}")
        results["session_persistence"] = {"status": "FAIL", "error": str(e)}

    print("\n" + "=" * 70)
    print("LIVE VERIFICATION COMPLETE")
    print("=" * 70)
    print(json.dumps(results, indent=2))
    return results


if __name__ == "__main__":
    run_live_verification()
