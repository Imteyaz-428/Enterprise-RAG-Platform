import json
import os
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
import redis

# Load backend environment variables
backend_env = Path(__file__).resolve().parent.parent.parent / ".env"
if backend_env.exists():
    load_dotenv(backend_env, override=False)
else:
    load_dotenv()

from utils.logger import logger


class RedisService:
    """
    Reliable, fail-open Redis service for caching chat sessions, query results,
    and metadata in Enterprise RAG Platform.

    Guarantees:
    1. Fail-open: Never crashes the application if Redis is unavailable, timed out, or misconfigured.
    2. Fast timeouts: Prevents blocking chat/streaming requests on network failures.
    3. Circuit breaker cooldown: Skips network attempts during sustained outages to minimize latency.
    4. Flexible TTL: Supports per-key TTL as well as global default TTL.
    """

    def __init__(self, client: redis.Redis | None = None):
        self.default_expire = int(os.getenv("REDIS_EXPIRE", "3600"))
        self.connect_timeout = float(os.getenv("REDIS_CONNECT_TIMEOUT", "2.0"))
        self.socket_timeout = float(os.getenv("REDIS_SOCKET_TIMEOUT", "2.0"))
        self.failure_cooldown = float(os.getenv("REDIS_CIRCUIT_COOLDOWN", "30.0"))

        self._is_available = True
        self._last_failure_time = 0.0

        if client is not None:
            self.client = client
            return

        redis_url = os.getenv("REDIS_URL")
        try:
            if redis_url:
                self.client = redis.Redis.from_url(
                    redis_url,
                    decode_responses=True,
                    socket_connect_timeout=self.connect_timeout,
                    socket_timeout=self.socket_timeout,
                    health_check_interval=30,
                )
            else:
                self.client = redis.Redis(
                    host=os.getenv("REDIS_HOST", "localhost"),
                    port=int(os.getenv("REDIS_PORT", "6379")),
                    db=int(os.getenv("REDIS_DB", "0")),
                    password=os.getenv("REDIS_PASSWORD") or None,
                    decode_responses=True,
                    socket_connect_timeout=self.connect_timeout,
                    socket_timeout=self.socket_timeout,
                )
        except Exception as e:
            self._record_failure(e, "INITIALIZATION")

    def _record_failure(self, error: Exception, operation: str) -> None:
        """Records an operation failure and trips the circuit breaker cooldown."""
        self._is_available = False
        self._last_failure_time = time.time()
        logger.warning(
            f"Redis {operation} failed (circuit opened for {self.failure_cooldown:.0f}s): {error}"
        )

    def _record_success(self) -> None:
        """Resets the circuit breaker on a successful operation."""
        self._is_available = True

    def _check_availability(self) -> bool:
        """
        Determines whether a Redis operation should be attempted.
        Returns False during the circuit cooldown to prevent latency spikes.
        """
        if not self._is_available:
            if time.time() - self._last_failure_time < self.failure_cooldown:
                return False
            # Cooldown elapsed, allow a single probe attempt through
        return True

    def get(self, key: str) -> Any | None:
        """
        Retrieves and JSON-deserializes a cached value.
        Returns None on cache miss, deserialization failure, or Redis outage.
        """
        if not self._check_availability():
            return None

        try:
            value = self.client.get(key)
            if value is None:
                return None

            self._record_success()
            try:
                return json.loads(value)
            except (ValueError, TypeError):
                # Return raw string if not JSON
                return value

        except Exception as error:
            self._record_failure(error, "GET")
            return None

    def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        """
        JSON-serializes and stores a key-value pair with an optional TTL in seconds.
        Returns True on success, False on failure (fail-open).
        """
        if not self._check_availability():
            return False

        try:
            if isinstance(value, (dict, list, int, float, bool)):
                serialized = json.dumps(value)
            elif isinstance(value, str):
                serialized = value
            else:
                serialized = json.dumps(value)

            expire_seconds = ttl if ttl is not None else self.default_expire

            if expire_seconds and expire_seconds > 0:
                self.client.setex(key, int(expire_seconds), serialized)
            else:
                self.client.set(key, serialized)

            self._record_success()
            return True

        except Exception as error:
            self._record_failure(error, "SET")
            return False

    def delete(self, *keys: str) -> bool:
        """
        Deletes one or more keys from Redis.
        Returns True on success or empty keys, False on failure.
        """
        if not keys:
            return True

        if not self._check_availability():
            return False

        try:
            self.client.delete(*keys)
            self._record_success()
            return True
        except Exception as error:
            self._record_failure(error, "DELETE")
            return False

    def ttl(self, key: str) -> int | None:
        """
        Returns the remaining time to live (TTL) in seconds for a key.
        - > 0: remaining seconds
        - -1: key exists but has no expiration
        - -2: key does not exist
        - None: Redis unavailable (fail-open)
        """
        if not self._check_availability():
            return None

        try:
            result = self.client.ttl(key)
            self._record_success()
            return result
        except Exception as error:
            self._record_failure(error, "TTL")
            return None

    def exists(self, key: str) -> bool:
        """
        Checks whether a key exists in Redis.
        Returns False if not found or if Redis is unavailable.
        """
        if not self._check_availability():
            return False

        try:
            result = bool(self.client.exists(key))
            self._record_success()
            return result
        except Exception as error:
            self._record_failure(error, "EXISTS")
            return False

    def ping(self) -> bool:
        """
        Tests Redis connectivity without raising exceptions.
        Returns True if connected and responsive, False otherwise.
        """
        try:
            result = bool(self.client.ping())
            if result:
                self._record_success()
            return result
        except Exception as error:
            self._record_failure(error, "PING")
            return False

    def clear(self, pattern: str = "cache:*") -> int:
        """
        Deletes all keys matching the specified pattern.
        Returns count of keys deleted, or 0 on failure.
        """
        if not self._check_availability():
            return 0

        try:
            keys = list(self.client.scan_iter(match=pattern))
            if keys:
                deleted = self.client.delete(*keys)
                self._record_success()
                return int(deleted)
            return 0
        except Exception as error:
            self._record_failure(error, "CLEAR")
            return 0
