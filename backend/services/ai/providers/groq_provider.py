import os
from typing import Iterator
from dotenv import load_dotenv
from groq import Groq
from typing import Iterator

from services.ai.providers.base_provider import BaseProvider

load_dotenv()


class GroqProvider(BaseProvider):

    def __init__(self):

        self.client = Groq(
            api_key=os.getenv("GROQ_API_KEY")
        )

        self.model = "llama-3.3-70b-versatile"

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
                
    

class GeminiProvider(BaseProvider):

    ...

    def stream(

        self,

        prompt: str,

    ) -> Iterator[str]:

        response = self.client.models.generate_content_stream(

            model=self.model,

            contents=prompt,

        )

        for chunk in response:

            if chunk.text:

                yield chunk.text