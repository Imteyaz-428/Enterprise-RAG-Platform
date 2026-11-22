import threading
import time
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from app import app
from services.ai.ai_services import AIService, AIProviderError
from services.ai.providers.base_provider import BaseProvider


# ============================================================================
# C. Health Endpoint Tests
# ============================================================================

def test_health_liveness_always_200():
    """GET /health returns 200 without checking external dependencies."""
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_ready_healthy_when_db_and_redis_up():
    """GET /health/ready returns 200 and healthy when DB and Redis are operational."""
    client = TestClient(app)
    with patch("app.engine.connect") as mock_connect, \
         patch("app.RedisService") as mock_redis_cls:
        # Mock DB SELECT 1
        mock_conn = MagicMock()
        mock_connect.return_value.__enter__.return_value = mock_conn

        # Mock Redis ping
        mock_redis_instance = MagicMock()
        mock_redis_instance.ping.return_value = True
        mock_redis_cls.return_value = mock_redis_instance

        response = client.get("/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"] == "healthy"
        assert data["redis"] == "healthy"


def test_health_ready_degraded_when_redis_down():
    """GET /health/ready returns 200 with redis='degraded' when Redis is unavailable."""
    client = TestClient(app)
    with patch("app.engine.connect") as mock_connect, \
         patch("app.RedisService") as mock_redis_cls:
        # DB is healthy
        mock_conn = MagicMock()
        mock_connect.return_value.__enter__.return_value = mock_conn

        # Redis ping fails
        mock_redis_instance = MagicMock()
        mock_redis_instance.ping.return_value = False
        mock_redis_cls.return_value = mock_redis_instance

        response = client.get("/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["database"] == "healthy"
        assert data["redis"] == "degraded"


def test_health_ready_503_when_db_down():
    """GET /health/ready returns 503 when the database connection fails."""
    client = TestClient(app)
    with patch("app.engine.connect", side_effect=Exception("Database unreachable")), \
         patch("app.RedisService") as mock_redis_cls:
        mock_redis_instance = MagicMock()
        mock_redis_instance.ping.return_value = True
        mock_redis_cls.return_value = mock_redis_instance

        response = client.get("/health/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["database"] == "unhealthy"


# ============================================================================
# D. Provider Cooldown Tests (with Mocks and Fake Clock)
# ============================================================================

class FakeClock:
    def __init__(self, initial_time: float = 1000.0):
        self._current_time = initial_time

    def time(self) -> float:
        return self._current_time

    def advance(self, seconds: float):
        self._current_time += seconds


class DummyMockProvider(BaseProvider):
    def __init__(self, name: str):
        self.name = name
        self.call_count = 0
        self.generate_side_effect = None
        self.return_value = f"Response from {name}"

    def generate(self, prompt: str) -> str:
        self.call_count += 1
        if self.generate_side_effect:
            if isinstance(self.generate_side_effect, Exception):
                raise self.generate_side_effect
            if callable(self.generate_side_effect):
                return self.generate_side_effect(prompt)
        return self.return_value

    def stream(self, prompt: str):
        self.call_count += 1
        if self.generate_side_effect:
            if isinstance(self.generate_side_effect, Exception):
                raise self.generate_side_effect
            if callable(self.generate_side_effect):
                for tok in self.generate_side_effect(prompt):
                    yield tok
                return
        yield self.return_value


def test_cooldown_delay_parsing():
    """Verifies delay parsing: attributes, regex, caps at 15 minutes, defaults to 60s."""
    service = AIService()

    # 1. Attribute on exception
    exc1 = Exception("429 Rate Limit")
    exc1.retry_after = 45
    assert service._parse_retry_delay(exc1) == 45.0

    # 2. Response header
    class MockResp:
        headers = {"Retry-After": "75"}
    exc2 = Exception("Rate limit")
    exc2.response = MockResp()
    assert service._parse_retry_delay(exc2) == 75.0

    # 3. Text in message: seconds
    exc3 = Exception("Rate limit reached. Please retry after 120s.")
    assert service._parse_retry_delay(exc3) == 120.0

    # 4. Text in message: minutes
    exc4 = Exception("Resource exhausted. Try again in 5 minutes.")
    assert service._parse_retry_delay(exc4) == 300.0

    # 5. Gemini API style: retryDelay
    exc5 = Exception("RESOURCE_EXHAUSTED. details: [{'retryDelay': '50747s'}]")
    # Capped at 15 minutes (900 seconds)
    assert service._parse_retry_delay(exc5) == 900.0

    # 6. Default fallback when no time specified
    exc6 = Exception("429 Too Many Requests: quota exceeded")
    assert service._parse_retry_delay(exc6) == 60.0


def test_rate_limit_initiates_cooldown_and_skips_on_next_call():
    """
    When primary provider (gemini) fails with rate_limit, it enters cooldown.
    Next provider (groq) succeeds immediately.
    On a subsequent call before cooldown expires, gemini is skipped immediately.
    """
    fake_clock = FakeClock(1000.0)
    service = AIService(clock=fake_clock.time)

    gemini = DummyMockProvider("gemini")
    groq = DummyMockProvider("groq")
    deepseek = DummyMockProvider("deepseek")

    service.provider_instances = {
        "gemini": gemini,
        "groq": groq,
        "deepseek": deepseek,
    }

    # Gemini fails with rate limit specifying 120s cooldown
    rate_err = Exception("429 RESOURCE_EXHAUSTED. Please retry in 120s.")
    gemini.generate_side_effect = rate_err

    # First call at t=1000: gemini fails -> enters cooldown until 1120 -> groq succeeds
    res1 = service.generate_answer("Prompt 1", providers=["gemini", "groq", "deepseek"])
    assert res1 == "Response from groq"
    assert gemini.call_count == 1
    assert groq.call_count == 1
    assert service.is_cooling_down("gemini") is True

    # Advance fake clock by 30 seconds (t=1030 < 1120)
    fake_clock.advance(30.0)

    # Second call: gemini is in cooldown, so it must be SKIPPED! Groq is called directly.
    res2 = service.generate_answer("Prompt 2", providers=["gemini", "groq", "deepseek"])
    assert res2 == "Response from groq"
    assert gemini.call_count == 1  # Not incremented!
    assert groq.call_count == 2

    # Advance fake clock past cooldown (advance 100s -> t=1130 > 1120)
    fake_clock.advance(100.0)
    assert service.is_cooling_down("gemini") is False

    # Gemini is now recovered
    gemini.generate_side_effect = None
    gemini.return_value = "Recovered response from gemini"

    # Third call: gemini is tried again and succeeds
    res3 = service.generate_answer("Prompt 3", providers=["gemini", "groq", "deepseek"])
    assert res3 == "Recovered response from gemini"
    assert gemini.call_count == 2
    assert groq.call_count == 2


def test_all_providers_cooling_down_still_tries_in_order():
    """
    If ALL providers are cooling down, still try them in order
    (never return nothing without trying).
    """
    fake_clock = FakeClock(2000.0)
    service = AIService(clock=fake_clock.time)

    gemini = DummyMockProvider("gemini")
    groq = DummyMockProvider("groq")

    service.provider_instances = {
        "gemini": gemini,
        "groq": groq,
    }

    # Set both in cooldown until t=2100
    service.set_cooldown("gemini", 100.0)
    service.set_cooldown("groq", 100.0)

    assert service.is_cooling_down("gemini") is True
    assert service.is_cooling_down("groq") is True

    # Call at t=2000 while BOTH are cooling down
    res = service.generate_answer("Hello", providers=["gemini", "groq"])
    # Gemini is tried first (in order) and succeeds
    assert res == "Response from gemini"
    assert gemini.call_count == 1
    assert groq.call_count == 0


def test_cooldown_thread_safety():
    """Verifies that cooldown reads and writes are thread-safe under concurrent load."""
    fake_clock = FakeClock(5000.0)
    service = AIService(clock=fake_clock.time)

    def worker(provider: str, delay: float):
        for _ in range(50):
            service.set_cooldown(provider, delay)
            _ = service.is_cooling_down(provider)
            service.reset_cooldown(provider)

    threads = [
        threading.Thread(target=worker, args=(f"provider_{i % 3}", 30.0 + i))
        for i in range(20)
    ]

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # No deadlocks or corruptions occurred
    assert isinstance(service._provider_cooldowns, dict)


def test_streaming_cooldown_skips_cooling_provider():
    """Verifies streaming also obeys provider cooldown."""
    fake_clock = FakeClock(3000.0)
    service = AIService(clock=fake_clock.time)

    gemini = DummyMockProvider("gemini")
    groq = DummyMockProvider("groq")

    service.provider_instances = {
        "gemini": gemini,
        "groq": groq,
    }

    # Gemini in cooldown
    service.set_cooldown("gemini", 60.0)

    stream = list(service.stream_answer("Prompt", providers=["gemini", "groq"]))
    assert "".join(stream) == "Response from groq"
    assert gemini.call_count == 0
    assert groq.call_count == 1
