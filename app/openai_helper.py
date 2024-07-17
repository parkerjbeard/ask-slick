import os
from openai import OpenAI
import json

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
from typing import List, Dict, Any

class OpenAIClient:
    def __init__(self):
        self.model = "gpt-3.5-turbo"

    def _create_chat_completion(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        response = client.chat.completions.create(model=self.model,
        messages=messages)
        return {
            "role": response.choices[0].message.role,
            "message": response.choices[0].message.content
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
        return response["message"].strip().lower()

    def classify_text(self, text: str, categories: List[str]) -> str:
        """
        Classify the given text into one of the provided categories.
        """
        messages = [
            {"role": "system", "content": "You are a helpful assistant that classifies text."},
            {"role": "user", "content": f"Please classify the following text into one of these categories. Your output will be a single word: {', '.join(categories)}\n\nText: {text}"}
        ]
        response = self._create_chat_completion(messages)
        return response["message"].strip().lower()

    def analyze_sentiment(self, text: str) -> str:
        """
        Analyze the sentiment of the given text.
        """
        messages = [
            {"role": "system", "content": "You are a helpful assistant that analyzes sentiment in text."},
            {"role": "user", "content": f"Please analyze the sentiment of the following text:\n\n{text}"}
        ]
        response = self._create_chat_completion(messages)
        return response['message']

    def search_documents(self, query: str, documents: List[str]) -> List[str]:
        """
        Search for relevant documents based on the given query.
        """
        messages = [
            {"role": "system", "content": "You are a helpful assistant that searches for relevant documents."},
            {"role": "user", "content": f"Given the following documents, please find the most relevant ones for the query: '{query}'\n\nDocuments:\n" + "\n".join(documents)}
        ]
        response = self._create_chat_completion(messages)
        return response['message'].split(", ")

    def classify_with_context(self, current_message: str, chat_history: List[str], categories: List[str]) -> str:
        """
        Classify the current message based on the chat history and given categories.
        """
        context = "\n".join(chat_history[-5:])  # Use the last 5 messages for context
        messages = [
            {"role": "system", "content": "You are a helpful assistant that classifies messages based on context. Pay close attention to the difference between travel requests and flight selections."},
            {"role": "user", "content": f"""Given the following chat history and categories, classify the current message. Your output should be a single word from the categories list.

            Chat history:
            {context}

            Current message: {current_message}

            Categories: {', '.join(categories)}

            Remember:
            - 'travel' is for new travel requests or questions about travel.
            - 'flight_selection' is only for when a user is selecting a specific flight from a list of options previously provided.
            - If in doubt between 'travel' and 'flight_selection', choose 'travel'.
            """}
        ]
        response = self._create_chat_completion(messages)
        return response['message'].strip().lower()
    
    def extract_travel_request(self, unstructured_text: str) -> Dict[str, Any]:
        """
        Extract structured travel request data from unstructured text.
        """
        messages = [
            {"role": "system", "content": "You are a helpful assistant that extracts structured travel request data from unstructured text."},
            {"role": "user", "content": f"Extract the travel request details from the following text:\n\n{unstructured_text}"}
        ]
        response = self._create_chat_completion(messages)
        return response['message'].strip().lower()

