import os
from typing import Iterator
from dotenv import load_dotenv
from openai import OpenAI

from services.ai.providers.base_provider import BaseProvider

load_dotenv()


class DeepSeekProvider(BaseProvider):

    def __init__(self):

        self.client = OpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com"
        )

        self.model = "deepseek-chat"

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

                chunk.choices

                and chunk.choices[0].delta.content

            ):

                yield chunk.choices[0].delta.content