import os
from typing import Iterator
from groq import Groq

from services.ai.providers.base_provider import BaseProvider
from services.ai.config import AI_REQUEST_TIMEOUT, load_environment

load_environment()


class GroqProvider(BaseProvider):

    def __init__(self, api_key: str | None = None, model: str | None = None):
        resolved_key = (api_key or os.getenv("GROQ_API_KEY") or "").strip()
        if not resolved_key:
            raise ValueError("GROQ_API_KEY is not configured")

        self.client = Groq(
            api_key=resolved_key,
            timeout=AI_REQUEST_TIMEOUT,
        )

        self.model = model or os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")


    def generate(self, prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        if not response or not response.choices or not response.choices[0].message.content or not response.choices[0].message.content.strip():
            raise ValueError("Groq returned empty or null content")

        return response.choices[0].message.content

    def stream(
        self,
        prompt: str,
    ) -> Iterator[str]:
        stream = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            stream=True,
        )

        for chunk in stream:
            if (
                chunk
                and chunk.choices
                and chunk.choices[0].delta
                and chunk.choices[0].delta.content
            ):
                yield chunk.choices[0].delta.content
