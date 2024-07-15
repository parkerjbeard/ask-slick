import os
import openai
from typing import Dict, Any

class TravelPlanner:
    def __init__(self):
        openai.api_key = os.getenv("OPENAI_API_KEY")
        self.system_message = {
            "role": "system",
            "content": "You are a travel planner assistant. You can parse travel requests, search for flights and accommodations, and generate travel suggestions."
        }
        self.conversation_history = [self.system_message]

    def _create_message_and_run(self, content: str) -> Dict[str, Any]:
        self.conversation_history.append({"role": "user", "content": content})

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=self.conversation_history
        )

        assistant_message = response.choices[0].message['content']
        self.conversation_history.append({"role": "assistant", "content": assistant_message})

        return {"role": "assistant", "message": assistant_message}

    def parse_travel_request(self, prompt: str) -> dict:
        """
        Use OpenAI to parse the travel request from the user's prompt.
        """
        response = self._create_message_and_run(prompt)
        return response["message"]

    def search_flights(self, origin: str, destination: str, departure_date: str, return_date: str) -> dict:
        """
        Placeholder function for searching flights.
        """
        return {
            "flights": [
                {
                    "airline": "Example Airlines",
                    "flight_number": "EA123",
                    "departure": f"{origin} at 10:00 AM",
                    "arrival": f"{destination} at 12:00 PM",
                    "price": "$300"
                }
            ]
        }

    def search_accommodations(self, city_code: str, check_in: str, check_out: str) -> dict:
        """
        Placeholder function for searching accommodations.
        """
        return {
            "hotels": [
                {
                    "name": "Example Hotel",
                    "address": f"{city_code} Main Street",
                    "price_per_night": "$150",
                    "rating": 4.5
                }
            ]
        }

    def generate_travel_suggestions(self, destination: str) -> str:
        """
        Generate travel suggestions for a given destination using OpenAI.
        """
        prompt = f"Provide travel suggestions for {destination}. Include popular attractions, local cuisine, and cultural experiences."
        response = self._create_message_and_run(prompt)
        return response["message"]

    def __del__(self):
        """
        Clean up method (no longer needed for chat completion API).
        """
        pass