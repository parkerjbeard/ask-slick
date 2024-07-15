import os
import openai
from typing import Dict, Any
from utils.logger import logger
import json
import ast
import dateparser
from datetime import datetime, timedelta

def parse_date(date_string: str) -> str:
    """Parse a date string and return it in YYYY-MM-DD format."""
    if date_string is None or date_string.lower() == 'null':
        return None
    parsed_date = dateparser.parse(date_string, settings={'RELATIVE_BASE': datetime.now()})
    return parsed_date.strftime('%Y-%m-%d') if parsed_date else None

def get_weekend_dates():
    """Get the dates for the upcoming weekend."""
    today = datetime.now()
    saturday = today + timedelta((5 - today.weekday()) % 7)
    sunday = saturday + timedelta(days=1)
    return saturday.strftime('%Y-%m-%d'), sunday.strftime('%Y-%m-%d')


class TravelPlanner:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            logger.error("OpenAI API key is not set in environment variables")
            raise ValueError("OpenAI API key is not set")
        
        openai.api_key = self.api_key
        self.system_message = {
            "role": "system",
            "content": "You are a travel planner assistant. You can parse travel requests, search for flights and accommodations, and generate travel suggestions."
        }
        self.conversation_history = [self.system_message]
        self.default_origin = os.getenv("DEFAULT_ORIGIN", "")
        if not self.default_origin:
            logger.warning("DEFAULT_ORIGIN is not set in environment variables")

    def _create_message_and_run(self, content: str) -> Dict[str, Any]:
        try:
            self.conversation_history.append({"role": "user", "content": content})

            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=self.conversation_history
            )

            assistant_message = response.choices[0].message['content']
            self.conversation_history.append({"role": "assistant", "content": assistant_message})

            return {"role": "assistant", "message": assistant_message}
        except Exception as e:
            logger.error(f"Error in _create_message_and_run: {str(e)}")
            raise

    def parse_travel_request(self, prompt: str) -> dict:
        try:
            parse_prompt = f"Parse the following travel request into a JSON format with keys: origin, destination, departure_date, return_date, check_in, check_out. If any information is missing, use null as the value. For date ranges like 'this weekend', use the range in the check_in and check_out fields. Travel request: {prompt}"
            response = self._create_message_and_run(parse_prompt)
            
            # Attempt to parse the response as JSON
            try:
                parsed_request = json.loads(response["message"])
            except json.JSONDecodeError:
                logger.error(f"Failed to parse JSON from OpenAI response: {response['message']}")
                return {"error": "Failed to parse travel request. Please provide more details."}

            # Process dates
            for key in ['departure_date', 'return_date', 'check_in', 'check_out']:
                parsed_request[key] = parse_date(parsed_request[key])

            # Handle 'this weekend' case
            if parsed_request['check_in'] == 'this weekend' or parsed_request['check_out'] == 'this weekend':
                parsed_request['check_in'], parsed_request['check_out'] = get_weekend_dates()

            # Set default origin if not provided
            if parsed_request['origin'] is None and self.default_origin:
                parsed_request['origin'] = self.default_origin

            # Validate the parsed request
            required_keys = ["origin", "destination", "departure_date", "return_date", "check_in", "check_out"]
            if not all(key in parsed_request for key in required_keys):
                logger.error(f"Parsed request is missing required keys: {parsed_request}")
                return {"error": "Failed to parse travel request. Please provide more details."}

            return parsed_request
        
        except Exception as e:
            logger.error(f"Error in parse_travel_request: {str(e)}")
            return {"error": f"Failed to parse travel request: {str(e)}"}

    def plan_trip(self, travel_request: dict) -> str:
        """
        Plan a trip based on the parsed travel request.
        """
        try:
            response = ""
            if travel_request["destination"]:
                if travel_request["check_in"] and travel_request["check_out"]:
                    accommodations = self.search_accommodations(travel_request["destination"], travel_request["check_in"], travel_request["check_out"])
                    response += f"Accommodations in {travel_request['destination']} from {travel_request['check_in']} to {travel_request['check_out']}:\n"
                    response += f"{json.dumps(accommodations, indent=2)}\n\n"
                else:
                    response += "Accommodation dates not provided. Please specify check-in and check-out dates for accommodation suggestions.\n\n"

            if travel_request["origin"] and travel_request["destination"] and travel_request["departure_date"]:
                flights = self.search_flights(travel_request["origin"], travel_request["destination"], travel_request["departure_date"], travel_request["return_date"])
                response += f"Flights from {travel_request['origin']} to {travel_request['destination']} on {travel_request['departure_date']}:\n"
                response += f"{json.dumps(flights, indent=2)}\n\n"
            else:
                response += "Not enough information provided for flight search. Please specify origin, destination, and departure date.\n\n"

            if travel_request["destination"]:
                suggestions = self.generate_travel_suggestions(travel_request["destination"])
                response += f"Suggestions for {travel_request['destination']}:\n{suggestions}"

            return response
        except Exception as e:
            logger.error(f"Error in plan_trip: {str(e)}")
            return f"An error occurred while planning your trip: {str(e)}"


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