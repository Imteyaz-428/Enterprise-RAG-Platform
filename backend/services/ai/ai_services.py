from config import RAG_PROVIDERS

from services.ai.providers.gemini_provider import GeminiProvider
from services.ai.providers.groq_provider import GroqProvider
from services.ai.providers.deepseek_provider import DeepSeekProvider

from utils.logger import logger
from utils.retry import retry_request


class AIProviderError(Exception):
    """Raised when all AI providers fail."""
    pass


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

    def _get_provider(self, provider_name: str):

        # Return cached instance if already created
        if provider_name in self.provider_instances:
            return self.provider_instances[provider_name]

        provider_class = self.provider_classes.get(provider_name)

        if provider_class is None:
            raise ValueError(
                f"Unknown provider: {provider_name}"
            )

        # Create provider instance
        provider = provider_class()

        # Cache it for future requests
        self.provider_instances[provider_name] = provider

        return provider

    def _generate_with_fallback(
        self,
        providers: list[str],
        prompt: str
    ) -> str:

        for provider_name in providers:

            try:

                provider = self._get_provider(provider_name)

                logger.info(
                    f"Using AI Provider: {provider_name}"
                )

                response = retry_request(
                    provider.generate,
                    prompt
                )

                logger.info(
                    f"{provider_name} generated response successfully."
                )

                return response

            except Exception as e:

                logger.warning(
                    f"{provider_name} failed: {e}"
                )

        logger.error("All AI providers failed.")

        raise AIProviderError(
            "All AI providers failed."
        )

    def generate_answer(
        self,
        prompt: str
    ) -> str:

        return self._generate_with_fallback(
            RAG_PROVIDERS,
            prompt
        )