import os

from dotenv import load_dotenv
from google import genai

from services.ai.providers.base_provider import BaseProvider

load_dotenv()


class GeminiProvider(BaseProvider):

    def __init__(self):

        self.client = genai.Client(
            api_key=os.getenv("GEMINI_API_KEY")
        )

        self.model = "gemini-2.5-flash"

    def generate(self, prompt: str) -> str:

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt
        )

        return response.text