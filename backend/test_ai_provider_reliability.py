import os
import json
import unittest
from unittest.mock import MagicMock, patch
import pytest

from services.ai.ai_services import AIService, AIProviderError, classify_provider_error
from services.ai.providers.base_provider import BaseProvider
from utils.retry import is_transient_error
from services.chat.chat_service import ChatService


class MockGeminiProvider(BaseProvider):
    def __init__(self):
        self.generate_mock = MagicMock()
        self.stream_mock = MagicMock()
        self.model = "gemini-2.5-flash"

    def generate(self, prompt: str) -> str:
        return self.generate_mock(prompt)

    def stream(self, prompt: str):
        return self.stream_mock(prompt)


class MockGroqProvider(BaseProvider):
    def __init__(self):
        self.generate_mock = MagicMock()
        self.stream_mock = MagicMock()
        self.model = "llama-3.3-70b-versatile"

    def generate(self, prompt: str) -> str:
        return self.generate_mock(prompt)

    def stream(self, prompt: str):
        return self.stream_mock(prompt)


class MockDeepSeekProvider(BaseProvider):
    def __init__(self):
        self.generate_mock = MagicMock()
        self.stream_mock = MagicMock()
        self.model = "deepseek-chat"

    def generate(self, prompt: str) -> str:
        return self.generate_mock(prompt)

    def stream(self, prompt: str):
        return self.stream_mock(prompt)


class CustomHTTPError(Exception):
    def __init__(self, status_code: int, message: str = "HTTP error"):
        super().__init__(message)
        self.status_code = status_code


class TestAIProviderReliability(unittest.TestCase):

    def setUp(self):
        self.ai_service = AIService()
        self.gemini_mock = MockGeminiProvider()
        self.groq_mock = MockGroqProvider()
        self.deepseek_mock = MockDeepSeekProvider()

        self.ai_service.provider_instances = {
            "gemini": self.gemini_mock,
            "groq": self.groq_mock,
            "deepseek": self.deepseek_mock,
        }

    # Requirement 1: Gemini failure -> Groq success
    def test_gemini_fails_groq_succeeds_normal(self):
        self.gemini_mock.generate_mock.side_effect = ConnectionError("Gemini network unreachable")
        self.groq_mock.generate_mock.return_value = "Groq fallback answer"

        result = self.ai_service.generate_answer("What is RAG?")
        self.assertEqual(result, "Groq fallback answer")
        self.assertTrue(self.gemini_mock.generate_mock.called)
        self.groq_mock.generate_mock.assert_called_once_with("What is RAG?")
        self.deepseek_mock.generate_mock.assert_not_called()

    # Requirement 2: Gemini and Groq failure -> DeepSeek success
    def test_gemini_and_groq_fail_deepseek_succeeds_normal(self):
        self.gemini_mock.generate_mock.side_effect = CustomHTTPError(503, "Gemini service unavailable")
        self.groq_mock.generate_mock.side_effect = ConnectionError("Groq timeout")
        self.deepseek_mock.generate_mock.return_value = "DeepSeek fallback answer"

        result = self.ai_service.generate_answer("What is RAG?")
        self.assertEqual(result, "DeepSeek fallback answer")
        self.assertTrue(self.gemini_mock.generate_mock.called)
        self.assertTrue(self.groq_mock.generate_mock.called)
        self.deepseek_mock.generate_mock.assert_called_once_with("What is RAG?")

    # Requirement 3: All providers fail
    def test_all_providers_fail_normal(self):
        self.gemini_mock.generate_mock.side_effect = ConnectionError("Gemini down")
        self.groq_mock.generate_mock.side_effect = ConnectionError("Groq down")
        self.deepseek_mock.generate_mock.side_effect = ConnectionError("DeepSeek down")

        with self.assertRaises(AIProviderError) as ctx:
            self.ai_service.generate_answer("What is RAG?")
        err_msg = str(ctx.exception)
        self.assertIn("All AI providers failed", err_msg)
        self.assertIn("gemini", err_msg)
        self.assertIn("groq", err_msg)
        self.assertIn("deepseek", err_msg)

    # Requirement 4: Invalid API key (fails fast, triggers next provider)
    def test_invalid_api_key_fails_fast_and_triggers_fallback(self):
        # Gemini fails with 401 UNAUTHENTICATED / ACCESS_TOKEN_TYPE_UNSUPPORTED
        self.gemini_mock.generate_mock.side_effect = CustomHTTPError(
            401, "UNAUTHENTICATED: ACCESS_TOKEN_TYPE_UNSUPPORTED: API key not valid"
        )
        self.groq_mock.generate_mock.return_value = "Groq recovered from invalid Gemini key"

        result = self.ai_service.generate_answer("What is RAG?")
        self.assertEqual(result, "Groq recovered from invalid Gemini key")
        # 401 is permanent, should only be called once without retry delay
        self.assertEqual(self.gemini_mock.generate_mock.call_count, 1)
        self.groq_mock.generate_mock.assert_called_once_with("What is RAG?")

    # Requirement 5: Insufficient balance (402 fails fast, triggers next provider)
    def test_insufficient_balance_fails_fast_and_triggers_fallback(self):
        # Gemini fails with 402 Insufficient Balance
        self.gemini_mock.generate_mock.side_effect = CustomHTTPError(
            402, "Insufficient Balance: please recharge your account"
        )
        self.groq_mock.generate_mock.return_value = "Groq recovered from Gemini balance error"

        result = self.ai_service.generate_answer("What is RAG?")
        self.assertEqual(result, "Groq recovered from Gemini balance error")
        # 402 is permanent billing, should only be called once without retry delay
        self.assertEqual(self.gemini_mock.generate_mock.call_count, 1)
        self.groq_mock.generate_mock.assert_called_once_with("What is RAG?")

    # Requirement 6: Timeout and connection errors (transient retry then fallback)
    def test_timeout_and_connection_errors_retry_then_fallback(self):
        self.gemini_mock.generate_mock.side_effect = TimeoutError("Connection to Gemini timed out")
        self.groq_mock.generate_mock.return_value = "Groq response after Gemini timeout"

        result = self.ai_service.generate_answer("What is RAG?")
        self.assertEqual(result, "Groq response after Gemini timeout")
        # Transient timeout error should have retried up to AI_MAX_RETRIES
        self.assertGreaterEqual(self.gemini_mock.generate_mock.call_count, 2)
        self.groq_mock.generate_mock.assert_called_once_with("What is RAG?")

    # Requirement 7: Streaming fallback before the first token
    def test_streaming_fallback_before_first_token(self):
        def failing_gemini(prompt):
            raise CustomHTTPError(401, "Invalid API key")
            yield "never"

        def groq_chunks(prompt):
            yield "Groq "
            yield "streamed "
            yield "successfully"

        self.gemini_mock.stream_mock.side_effect = failing_gemini
        self.groq_mock.stream_mock.side_effect = groq_chunks

        tokens = list(self.ai_service.stream_answer("What is RAG?"))
        self.assertEqual(tokens, ["Groq ", "streamed ", "successfully"])
        self.assertEqual(tokens[0], "Groq ")
        self.deepseek_mock.stream_mock.assert_not_called()

    # Requirement 8: Streaming error handling in chat_stream (no ASGI crash)
    def test_streaming_error_handling_in_chat_stream_prevents_asgi_crash(self):
        chat_service = ChatService()
        # Mock prepare_chat and redis to avoid full DB query
        mock_session = MagicMock()
        mock_session.id = 101
        chat_service._prepare_chat = MagicMock(return_value=(mock_session, "test prompt", []))
        chat_service.redis = MagicMock()
        chat_service.redis.get.return_value = None

        # Mock all providers failing in stream_answer
        chat_service.ai_service = MagicMock()
        chat_service.ai_service._sanitize_error = lambda x: x
        chat_service.ai_service.stream_answer.side_effect = AIProviderError(
            "All AI providers failed: gemini (authentication), groq (authentication), deepseek (billing)"
        )

        mock_db = MagicMock()
        stream = chat_service.chat_stream(
            db=mock_db,
            question="What is RAG?",
            organization_id=1,
            user_id=1,
        )

        events = list(stream)
        raw_output = "".join(events)

        # Must contain metadata event
        self.assertIn("event: metadata", raw_output)
        # Must contain error event
        self.assertIn("event: error", raw_output)
        # In accordance with Task 2, no token event is emitted after a terminal error event
        self.assertNotIn("event: token", raw_output)
        # Must contain done event to reset frontend UI state
        self.assertIn("event: done", raw_output)

    # Requirement 9: Non-streaming generation
    def test_non_streaming_gemini_succeeds(self):
        self.gemini_mock.generate_mock.return_value = "Direct Gemini generation"

        result = self.ai_service.generate_answer("Prompt")
        self.assertEqual(result, "Direct Gemini generation")
        self.gemini_mock.generate_mock.assert_called_once_with("Prompt")

    # Requirement 10: No duplicate output or incomplete responses (mid-stream failure protection)
    def test_streaming_midstream_failure_does_not_switch_providers(self):
        def gemini_midstream_drop(prompt):
            yield "Part 1 "
            yield "Part 2 "
            raise ConnectionError("Socket reset mid-stream")

        def groq_corrupted(prompt):
            yield "Corrupted "
            yield "continuation"

        self.gemini_mock.stream_mock.side_effect = gemini_midstream_drop
        self.groq_mock.stream_mock.side_effect = groq_corrupted

        stream = self.ai_service.stream_answer("Prompt")
        tokens = []
        with self.assertRaises(ConnectionError):
            for token in stream:
                tokens.append(token)

        # Partial tokens delivered before failure
        self.assertEqual(tokens, ["Part 1 ", "Part 2 "])
        # Verification: Groq was NOT called mid-stream
        self.groq_mock.stream_mock.assert_not_called()

    # Requirement Phase 4: Provider health diagnostics
    def test_provider_health_diagnostics_report(self):
        with patch.dict(os.environ, {
            "GEMINI_API_KEY": "dummy_gemini_key",
            "GROQ_API_KEY": "dummy_groq_key",
            "DEEPSEEK_API_KEY": "dummy_deepseek_key",
        }):
            self.gemini_mock.generate_mock.return_value = "pong"
            self.groq_mock.generate_mock.side_effect = CustomHTTPError(401, "Invalid API key")
            self.deepseek_mock.generate_mock.side_effect = CustomHTTPError(402, "Insufficient Balance")

            report = self.ai_service.check_providers_health()
            self.assertIn("overall_status", report)
            self.assertIn("providers", report)

            # Gemini should be healthy
            self.assertEqual(report["providers"]["gemini"]["status"], "healthy")
            self.assertEqual(report["providers"]["gemini"]["authentication"], "valid")
            self.assertEqual(report["providers"]["gemini"]["failure_category"], "none")

            # Groq should be marked authentication failure
            self.assertEqual(report["providers"]["groq"]["status"], "unhealthy")
            self.assertEqual(report["providers"]["groq"]["authentication"], "invalid")
            self.assertEqual(report["providers"]["groq"]["failure_category"], "authentication")

            # DeepSeek should be marked billing failure
            self.assertEqual(report["providers"]["deepseek"]["status"], "unhealthy")
            self.assertEqual(report["providers"]["deepseek"]["failure_category"], "billing")

    # Error classification tests
    def test_classify_provider_error_categories(self):
        self.assertEqual(
            classify_provider_error(CustomHTTPError(401, "ACCESS_TOKEN_TYPE_UNSUPPORTED")),
            "authentication",
        )
        self.assertEqual(
            classify_provider_error(CustomHTTPError(402, "Insufficient Balance")),
            "billing",
        )
        self.assertEqual(
            classify_provider_error(CustomHTTPError(429, "ResourceExhausted")),
            "rate_limit",
        )
        self.assertEqual(
            classify_provider_error(TimeoutError("Read timed out")),
            "timeout",
        )
        self.assertEqual(
            classify_provider_error(CustomHTTPError(500, "Internal Server Error")),
            "server_error",
        )
        self.assertEqual(
            classify_provider_error(ValueError("GEMINI_API_KEY is not configured")),
            "configuration",
        )


if __name__ == "__main__":
    unittest.main()
