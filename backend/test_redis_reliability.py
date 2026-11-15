import os
import time
import json
import pytest
from unittest.mock import MagicMock, patch

from services.cache.redis_service import RedisService
import redis.exceptions


class TestRedisReliability:
    """
    Comprehensive tests for Redis reliability:
    - GET, SET, DELETE, TTL, EXISTS, PING
    - Fail-open behavior under timeouts and connection errors
    - Cache miss handling
    - Custom TTL handling
    - Circuit breaker cooldown behavior
    """

    @pytest.fixture(autouse=True)
    def setup_mock_redis(self):
        self.mock_client = MagicMock()
        self.redis_service = RedisService(client=self.mock_client)

    def test_get_and_set_success(self):
        """Tests successful SET and GET with JSON serialization."""
        test_data = {"answer": "RAG combines search with generation", "citations": [1, 2]}
        self.mock_client.get.return_value = json.dumps(test_data)

        # SET
        success = self.redis_service.set("cache:test_key", test_data, ttl=300)
        assert success is True
        self.mock_client.setex.assert_called_once_with(
            "cache:test_key", 300, json.dumps(test_data)
        )

        # GET
        retrieved = self.redis_service.get("cache:test_key")
        assert retrieved == test_data
        self.mock_client.get.assert_called_once_with("cache:test_key")

    def test_get_cache_miss(self):
        """Tests that a cache miss returns None cleanly without error."""
        self.mock_client.get.return_value = None

        result = self.redis_service.get("cache:nonexistent_key")
        assert result is None
        self.mock_client.get.assert_called_once_with("cache:nonexistent_key")

    def test_set_default_ttl(self):
        """Tests that setting a key without explicit TTL uses default_expire."""
        self.redis_service.default_expire = 1800
        success = self.redis_service.set("cache:default_ttl", {"key": "val"})
        assert success is True
        self.mock_client.setex.assert_called_once_with(
            "cache:default_ttl", 1800, json.dumps({"key": "val"})
        )

    def test_set_zero_ttl_uses_standard_set(self):
        """Tests that TTL <= 0 calls standard set without expiration."""
        success = self.redis_service.set("cache:no_ttl", "plain_string", ttl=0)
        assert success is True
        self.mock_client.set.assert_called_once_with("cache:no_ttl", "plain_string")

    def test_ttl_query(self):
        """Tests querying remaining TTL for keys."""
        self.mock_client.ttl.return_value = 245
        assert self.redis_service.ttl("cache:active_key") == 245

        self.mock_client.ttl.return_value = -1  # No expiration
        assert self.redis_service.ttl("cache:persistent_key") == -1

        self.mock_client.ttl.return_value = -2  # Key does not exist
        assert self.redis_service.ttl("cache:missing_key") == -2

    def test_delete_single_and_multi_key(self):
        """Tests single and multi-key deletion."""
        # Single key
        assert self.redis_service.delete("cache:key1") is True
        self.mock_client.delete.assert_called_with("cache:key1")

        # Multi key
        assert self.redis_service.delete("cache:key1", "cache:key2", "cache:key3") is True
        self.mock_client.delete.assert_called_with("cache:key1", "cache:key2", "cache:key3")

        # Empty delete returns True immediately
        assert self.redis_service.delete() is True

    def test_exists_check(self):
        """Tests key existence check."""
        self.mock_client.exists.return_value = 1
        assert self.redis_service.exists("cache:existing") is True

        self.mock_client.exists.return_value = 0
        assert self.redis_service.exists("cache:missing") is False

    def test_ping_success_and_failure(self):
        """Tests that ping returns True when connected and False without crashing on failure."""
        self.mock_client.ping.return_value = True
        assert self.redis_service.ping() is True

        # Simulate network drop or IP allowlist rejection
        self.mock_client.ping.side_effect = redis.exceptions.ResponseError("Client IP address is not in the allowlist.")
        assert self.redis_service.ping() is False

    def test_fail_open_on_connection_error(self):
        """Verifies fail-open behavior: operations return None / False without raising exceptions."""
        self.mock_client.get.side_effect = redis.exceptions.ConnectionError("Connection refused")
        self.mock_client.setex.side_effect = redis.exceptions.ConnectionError("Connection refused")
        self.mock_client.delete.side_effect = redis.exceptions.ConnectionError("Connection refused")
        self.mock_client.ttl.side_effect = redis.exceptions.ConnectionError("Connection refused")
        self.mock_client.exists.side_effect = redis.exceptions.ConnectionError("Connection refused")

        # None of these must raise an exception
        assert self.redis_service.get("cache:key") is None
        assert self.redis_service.set("cache:key", "value") is False
        assert self.redis_service.delete("cache:key") is False
        assert self.redis_service.ttl("cache:key") is None
        assert self.redis_service.exists("cache:key") is False

    def test_fail_open_on_timeout_error(self):
        """Verifies fail-open behavior on socket / connect timeouts."""
        self.mock_client.get.side_effect = redis.exceptions.TimeoutError("Socket timeout")

        result = self.redis_service.get("cache:slow_key")
        assert result is None

    def test_circuit_breaker_prevents_network_hangs(self):
        """
        Tests that when an operation fails, the circuit opens for failure_cooldown seconds,
        immediately returning fail-open values without invoking the underlying client.
        """
        self.redis_service.failure_cooldown = 10.0
        self.mock_client.get.side_effect = redis.exceptions.ConnectionError("Server down")

        # First call fails and trips breaker
        assert self.redis_service.get("cache:key1") is None
        assert self.mock_client.get.call_count == 1
        assert self.redis_service._is_available is False

        # Subsequent call within cooldown fails immediately without calling mock_client
        assert self.redis_service.get("cache:key2") is None
        assert self.mock_client.get.call_count == 1  # Not incremented!
        assert self.redis_service.set("cache:key3", "val") is False
        assert self.mock_client.setex.call_count == 0

    def test_get_non_json_string_fallback(self):
        """Tests that if a plain non-JSON string is in Redis, it is returned as a string."""
        self.mock_client.get.return_value = "plain_unformatted_string"
        result = self.redis_service.get("cache:plain")
        assert result == "plain_unformatted_string"
