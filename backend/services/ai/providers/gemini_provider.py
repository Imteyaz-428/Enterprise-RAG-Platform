import os
from typing import Iterator

from google import genai
from services.ai.config import AI_REQUEST_TIMEOUT, load_environment
from services.ai.providers.base_provider import BaseProvider

load_environment()


class GeminiProvider(BaseProvider):

    def __init__(self, api_key: str | None = None, model: str | None = None):
        # Support both GEMINI_API_KEY and GOOGLE_API_KEY, strip whitespace
        resolved_key = (api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip()
        if not resolved_key:
            raise ValueError("GEMINI_API_KEY is not configured")

        self.client = genai.Client(
            api_key=resolved_key,
            http_options={"timeout": AI_REQUEST_TIMEOUT * 1000},
        )
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")



    def generate(
        self,
        prompt: str,
    ) -> str:
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
        )

        if not response or not response.text or not response.text.strip():
            raise ValueError("Gemini returned empty or null content")

        return response.text

    def stream(
        self,
        prompt: str,
    ) -> Iterator[str]:
        response = self.client.models.generate_content_stream(
            model=self.model,
            contents=prompt,
        )

        for chunk in response:
            if chunk and chunk.text:
                yield chunk.text
