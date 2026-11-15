import os
from typing import Iterator
from openai import OpenAI

from services.ai.providers.base_provider import BaseProvider
from services.ai.config import AI_REQUEST_TIMEOUT, load_environment

load_environment()


class DeepSeekProvider(BaseProvider):

    def __init__(self):
        api_key = (os.getenv("DEEPSEEK_API_KEY") or "").strip()
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY is not configured")


        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com",
            timeout=AI_REQUEST_TIMEOUT,
        )

        self.model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")


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
            raise ValueError("DeepSeek returned empty or null content")

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
