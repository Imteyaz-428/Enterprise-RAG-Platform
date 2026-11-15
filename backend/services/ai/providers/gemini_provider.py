import os
from typing import Iterator

from google import genai
from services.ai.config import load_environment
from services.ai.providers.base_provider import BaseProvider

load_environment()


class GeminiProvider(BaseProvider):

    def __init__(self):
        # Support both GEMINI_API_KEY and GOOGLE_API_KEY, strip whitespace
        api_key = (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip()
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not configured")

        self.client = genai.Client(
            api_key=api_key
        )
        self.model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")



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
