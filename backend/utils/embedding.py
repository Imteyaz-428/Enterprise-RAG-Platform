import os
from dotenv import load_dotenv
import voyageai

load_dotenv()

client = voyageai.Client(
    api_key=os.getenv("VOYAGE_API_KEY")
)


def generate_embeddings(texts: list[str]) -> list[list[float]]:
    """
    Generate embeddings for multiple texts.
    Used during document upload.
    """
    response = client.embed(
        texts,
        model="voyage-3-large"
    )
    return response.embeddings


def generate_embedding(text: str) -> list[float]:
    """
    Generate embedding for a single query.
    Used during semantic search.
    """
    response = client.embed(
        [text],
        model="voyage-3-large"
    )

    return response.embeddings[0]