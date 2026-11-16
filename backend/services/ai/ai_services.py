import concurrent.futures
import os
import re
from typing import Iterator, Any
from services.ai.config import RAG_PROVIDERS, load_environment
from services.ai.providers.base_provider import BaseProvider
from services.ai.providers.gemini_provider import GeminiProvider
from services.ai.providers.groq_provider import GroqProvider
from services.ai.providers.deepseek_provider import DeepSeekProvider

from utils.logger import logger
from utils.retry import retry_request

load_environment()


class AIProviderError(Exception):
    """Raised when all AI providers fail."""
    pass


def classify_provider_error(exc: Exception) -> str:
    """
    Classifies an exception into a standardized failure category:
    'authentication', 'billing', 'rate_limit', 'timeout', 'server_error', 'configuration'
    """
    status_code = getattr(exc, "status_code", getattr(exc, "code", None))
    if status_code is not None:
        try:
            code = int(status_code)
            if code in (401, 403):
                return "authentication"
            if code == 402:
                return "billing"
            if code == 429:
                return "rate_limit"
            if 500 <= code <= 599:
                return "server_error"
            if code in (400, 404, 422):
                return "configuration"
        except (ValueError, TypeError):
            pass

    class_name = exc.__class__.__name__.lower()
    msg = str(exc).lower()

    if any(w in msg for w in ("401", "unauthenticated", "invalid api key", "api key not valid", "access_token_type_unsupported", "invalid_api_key", "unauthorized")) or "auth" in class_name:
        return "authentication"
    if any(w in msg for w in ("402", "insufficient balance", "insufficient_balance", "billing", "payment required", "out of credits")) or "balance" in class_name:
        return "billing"
    if any(w in msg for w in ("429", "rate limit", "ratelimit", "resource_exhausted", "too many requests", "quota exceeded")) or "ratelimit" in class_name:
        return "rate_limit"
    if any(w in msg for w in ("timeout", "timed out", "deadline")) or "timeout" in class_name:
        return "timeout"
    if any(w in msg for w in ("500", "502", "503", "504", "connection reset", "connection error", "server error")) or "server" in class_name or "connection" in class_name:
        return "server_error"
    if any(w in msg for w in ("not configured", "missing", "empty", "unknown provider")):
        return "configuration"

    return "server_error"


class AIService:

    def __init__(self):
        # Register provider classes
        self.provider_classes = {
            "gemini": GeminiProvider,
            "groq": GroqProvider,
            "deepseek": DeepSeekProvider,
        }

        # Cache provider instances
        self.provider_instances = {}

    @staticmethod
    def _sanitize_error(err_msg: str) -> str:
        """Removes API keys, bearer tokens or sensitive credentials from error strings."""
        if not err_msg:
            return ""
        for env_key in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "GROQ_API_KEY", "DEEPSEEK_API_KEY", "VOYAGE_API_KEY", "SECRET_KEY"):
            val = os.getenv(env_key)
            if val and len(val) > 4:
                err_msg = err_msg.replace(val, "[REDACTED]")
        err_msg = re.sub(
            r'(api[_-]?key|token|bearer|authorization)[=:\s]+([a-zA-Z0-9_\-\.]{8,})',
            r'\1=[REDACTED]',
            err_msg,
            flags=re.IGNORECASE,
        )
        return err_msg

    def _get_provider(self, provider_name: str) -> BaseProvider:
        # Return cached instance if already created
        if provider_name in self.provider_instances:
            return self.provider_instances[provider_name]

        provider_class = self.provider_classes.get(provider_name)
        if provider_class is None:
            raise ValueError(f"Unknown provider: {provider_name}")

        # Create provider instance
        provider = provider_class()

        # Cache it for future requests
        self.provider_instances[provider_name] = provider
        return provider

    def _execute_with_fallback(
        self,
        providers: list[str],
        prompt: str,
        timeout_seconds: float | None = None,
        max_attempts: int | None = None,
        max_fallbacks: int | None = None,
    ) -> str:
        if not providers:
            raise AIProviderError("All AI providers failed. Details: No providers configured.")

        candidate_providers = providers
        if max_fallbacks is not None:
            candidate_providers = providers[: max(0, max_fallbacks + 1)]

        if not candidate_providers:
            raise AIProviderError("All AI providers failed. Details: No providers configured.")

        provider_errors = {}
        for provider_name in candidate_providers:
            try:
                logger.info(f"Using AI Provider: {provider_name}")
                provider = self._get_provider(provider_name)

                def _call_provider():
                    if timeout_seconds is not None and timeout_seconds > 0:
                        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
                        try:
                            future = executor.submit(provider.generate, prompt)
                            return future.result(timeout=timeout_seconds)
                        finally:
                            executor.shutdown(wait=False, cancel_futures=True)
                    return provider.generate(prompt)

                # Execute generation with retry for transient errors
                response = retry_request(
                    _call_provider,
                    max_attempts=max_attempts,
                )

                # Validate response is non-empty
                if not response or not str(response).strip():
                    raise ValueError(f"{provider_name} returned empty or invalid response")

                logger.info(f"AI Provider [{provider_name}] generated response successfully.")
                return str(response)

            except Exception as e:
                category = classify_provider_error(e)
                safe_err = self._sanitize_error(str(e))
                logger.warning(
                    f"AI Provider [{provider_name}] failed (category: {category}): {safe_err}"
                )
                provider_errors[provider_name] = f"{category}: {safe_err}"

        error_summary = "; ".join(f"{p} ({err})" for p, err in provider_errors.items())
        logger.error(f"All AI providers failed. Summary: {error_summary}")
        raise AIProviderError(f"All AI providers failed. Details: {error_summary}")

    def generate_answer(
        self,
        prompt: str,
        providers: list[str] | None = None,
        timeout_seconds: float | None = None,
        max_attempts: int | None = None,
        max_fallbacks: int | None = None,
    ) -> str:
        target_providers = providers if providers is not None else RAG_PROVIDERS
        return self._execute_with_fallback(
            providers=target_providers,
            prompt=prompt,
            timeout_seconds=timeout_seconds,
            max_attempts=max_attempts,
            max_fallbacks=max_fallbacks,
        )

    def stream_answer(
        self,
        prompt: str,
        providers: list[str] | None = None,
    ) -> Iterator[str]:
        """
        Streams answer with reliable provider fallback before the first token is emitted.
        Buffers the initial token so that the active provider is committed safely.
        Once the first token is emitted to the client, the provider cannot be switched.
        """
        target_providers = providers if providers is not None else RAG_PROVIDERS
        if not target_providers:
            raise AIProviderError("All AI providers failed to generate stream. Details: No providers configured.")

        active_provider = None
        first_token = None
        token_iterator = None
        provider_errors = {}

        for provider_name in target_providers:
            try:
                logger.info(f"Attempting AI Provider (stream): {provider_name}")
                provider = self._get_provider(provider_name)

                # Initialize provider stream with retry for transient errors
                def _init_stream():
                    s = provider.stream(prompt)
                    it = iter(s)
                    first = None
                    for token in it:
                        if token and str(token).strip():
                            first = token
                            break
                    if first is None:
                        raise ValueError(f"{provider_name} returned an empty stream")
                    return first, it

                first_token, token_iterator = retry_request(_init_stream)
                active_provider = provider_name
                logger.info(f"Active streaming provider committed: {provider_name}")
                break

            except Exception as e:
                category = classify_provider_error(e)
                safe_err = self._sanitize_error(str(e))
                logger.warning(
                    f"AI Provider [{provider_name}] stream initialization failed (category: {category}): {safe_err}"
                )
                provider_errors[provider_name] = f"{category}: {safe_err}"

        if active_provider is None or token_iterator is None:
            error_summary = "; ".join(f"{p} ({err})" for p, err in provider_errors.items())
            logger.error(f"All AI providers failed for streaming: {error_summary}")
            raise AIProviderError(f"All AI providers failed to generate stream. Details: {error_summary}")

        # Fallback phase completed. Emit first token from the committed active provider.
        yield first_token

        # Stream subsequent tokens. Never switch providers after partial output has been sent.
        try:
            for chunk in token_iterator:
                if chunk:
                    yield chunk
        except Exception as mid_stream_err:
            category = classify_provider_error(mid_stream_err)
            safe_err = self._sanitize_error(str(mid_stream_err))
            logger.error(f"{active_provider} stream interrupted mid-stream (category: {category}): {safe_err}")
            raise

    def check_providers_health(self) -> dict[str, Any]:
        """
        Independently checks health and configuration for all configured AI providers.
        Does not consume heavy API credits (runs lightweight single-token probe).
        Never exposes API keys or secrets in responses.
        """
        results = {}
        for provider_name in ["gemini", "groq", "deepseek"]:
            status: dict[str, Any] = {
                "provider": provider_name,
                "configured": False,
                "status": "unhealthy",
                "authentication": "missing",
                "model": "unknown",
                "generation_test": "skipped",
                "failure_category": "none",
                "message": "",
            }

            env_key_map = {
                "gemini": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
                "groq": ["GROQ_API_KEY"],
                "deepseek": ["DEEPSEEK_API_KEY"],
            }
            keys = env_key_map.get(provider_name, [])
            has_key = any(bool(os.getenv(k) and os.getenv(k).strip()) for k in keys)

            if not has_key:
                status["status"] = "not_configured"
                status["authentication"] = "missing"
                status["failure_category"] = "configuration"
                status["message"] = f"Missing environment variable: {' or '.join(keys)}"
                results[provider_name] = status
                continue

            status["configured"] = True

            try:
                provider = self._get_provider(provider_name)
                status["model"] = getattr(provider, "model", "unknown")

                # Minimal probe: 'ping' prompt
                response = provider.generate("ping")
                if response and str(response).strip():
                    status["status"] = "healthy"
                    status["authentication"] = "valid"
                    status["generation_test"] = "passed"
                    status["failure_category"] = "none"
                    status["message"] = "Provider is operational."
                else:
                    status["status"] = "unhealthy"
                    status["generation_test"] = "failed"
                    status["failure_category"] = "configuration"
                    status["message"] = "Provider returned empty response to ping test."

            except Exception as e:
                cat = classify_provider_error(e)
                safe_msg = self._sanitize_error(str(e))
                status["status"] = "unhealthy"
                status["generation_test"] = "failed"
                status["failure_category"] = cat
                status["authentication"] = "invalid" if cat == "authentication" else "valid_or_untested"
                status["message"] = safe_msg

            results[provider_name] = status

        overall_healthy = any(r["status"] == "healthy" for r in results.values())
        return {
            "overall_status": "healthy" if overall_healthy else "degraded",
            "active_providers": RAG_PROVIDERS,
            "providers": results,
        }


if __name__ == "__main__":
    import json
    service = AIService()
    print(json.dumps(service.check_providers_health(), indent=2))

