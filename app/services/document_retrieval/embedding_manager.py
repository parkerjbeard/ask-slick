import openai
import os
from typing import List

class EmbeddingManager:
    def __init__(self):
        openai.api_key = os.environ.get("OPENAI_API_KEY")

    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate an embedding for the given text using OpenAI's API.
        """
        try:
            response = openai.Embedding.create(
                model="text-embedding-ada-002",
                input=text
            )
            return response['data'][0]['embedding']
        except Exception as e:
            print(f"Error in generate_embedding: {e}")
            return []