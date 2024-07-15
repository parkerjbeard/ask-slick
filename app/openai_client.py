import os
import openai
from typing import List, Dict, Any

class OpenAIClient:
    def __init__(self):
        openai.api_key = os.getenv("OPENAI_API_KEY")
        self.model = "gpt-3.5-turbo"

    def _create_chat_completion(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        response = openai.ChatCompletion.create(
            model=self.model,
            messages=messages
        )
        return {
            "role": response.choices[0].message['role'],
            "message": response.choices[0].message['content']
        }

    def generate_text(self, prompt: str, max_tokens: int = 150) -> str:
        """
        Generate text based on a given prompt.
        """
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ]
        response = self._create_chat_completion(messages)
        return response["message"]

    def summarize_text(self, text: str) -> str:
        """
        Summarize the given text.
        """
        messages = [
            {"role": "system", "content": "You are a helpful assistant that summarizes text."},
            {"role": "user", "content": f"Please summarize the following text:\n\n{text}"}
        ]
        response = self._create_chat_completion(messages)
        return response["message"]

    def extract_keywords(self, text: str) -> List[str]:
        """
        Extract keywords from the given text.
        """
        messages = [
            {"role": "system", "content": "You are a helpful assistant that extracts keywords from text."},
            {"role": "user", "content": f"Please extract the main keywords from the following text:\n\n{text}"}
        ]
        response = self._create_chat_completion(messages)
        return response["message"].split(", ")

    def classify_text(self, text: str, categories: List[str]) -> str:
        """
        Classify the given text into one of the provided categories.
        """
        messages = [
            {"role": "system", "content": "You are a helpful assistant that classifies text."},
            {"role": "user", "content": f"Please classify the following text into one of these categories: {', '.join(categories)}\n\nText: {text}"}
        ]
        response = self._create_chat_completion(messages)
        return response["message"]

    def analyze_sentiment(self, text: str) -> str:
        """
        Analyze the sentiment of the given text.
        """
        messages = [
            {"role": "system", "content": "You are a helpful assistant that analyzes sentiment in text."},
            {"role": "user", "content": f"Please analyze the sentiment of the following text:\n\n{text}"}
        ]
        response = self._create_chat_completion(messages)
        return response["message"]

    def search_documents(self, query: str, documents: List[str]) -> List[str]:
        """
        Search for relevant documents based on the given query.
        """
        messages = [
            {"role": "system", "content": "You are a helpful assistant that searches for relevant documents."},
            {"role": "user", "content": f"Given the following documents, please find the most relevant ones for the query: '{query}'\n\nDocuments:\n" + "\n".join(documents)}
        ]
        response = self._create_chat_completion(messages)
        return response["message"].split(", ")