import os
from dotenv import load_dotenv
import voyageai

load_dotenv()   # <-- Load .env first

client = voyageai.Client(
    api_key=os.getenv("VOYAGE_API_KEY")
)


def generate_embeddings(texts: list[str]) -> list[list[float]]:
    response = client.embed(
        texts,
        model="voyage-3-large"
    )
    return response.embeddings