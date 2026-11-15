"""Embedding cache + pacing for the benchmark (works with Voyage free-tier limits)."""
import json
import time
from pathlib import Path

CACHE_PATH = Path(__file__).resolve().parent / ".embed_cache.json"


def install_embedding_cache(min_interval: float = 21.0, max_retries: int = 6):
    import services.chat.retrieval_service as rs

    original = rs.generate_embedding
    cache = json.loads(CACHE_PATH.read_text()) if CACHE_PATH.exists() else {}
    state = {"last_call": 0.0}

    def cached(text):
        if text in cache:
            return cache[text]
        for attempt in range(1, max_retries + 1):
            wait = min_interval - (time.monotonic() - state["last_call"])
            if wait > 0:
                time.sleep(wait)
            state["last_call"] = time.monotonic()
            try:
                vector = original(text)
                break
            except Exception as e:  # noqa: BLE001
                if "ratelimit" not in type(e).__name__.lower() or attempt == max_retries:
                    raise
                print(f"  rate limited, waiting 30s (attempt {attempt}/{max_retries})...")
                time.sleep(30)
        cache[text] = vector
        CACHE_PATH.write_text(json.dumps(cache))
        return vector

    rs.generate_embedding = cached