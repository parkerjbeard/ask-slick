import os
from openai import OpenAI
from typing import Dict, Any, Tuple, List
import json
from datetime import datetime, timedelta
from .search_flight import create_flight_search
from .search_hotel import create_hotel_search
from utils.dates_format import parse_date, get_weekend_dates, get_next_weekday
from app.openai_helper import OpenAIClient
from utils.logger import logger
import re

class TravelPlanner:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is not set")
        self.default_origin = os.getenv("DEFAULT_ORIGIN", "")
        self.flight_search = create_flight_search()
        self.hotel_search = create_hotel_search()
        self.openai_client = OpenAIClient()

    def parse_travel_request(self, prompt: str, chat_history: List[str]) -> Dict[str, Any]:
        parse_prompt = (
            "Parse the following travel request into a JSON format with keys: "
            "origin, destination, departure_date, return_date, check_in, check_out. "
            "Given the context, if no origin was provided, the origin is none. If an origin is provided, "
            "the origin is the provided origin. "
            "For origin and destination, provide the 3-letter airport code. "
            "If any information is missing, use null as the value. "
            "For date ranges like 'this weekend', use the range in the check_in and check_out fields. "
            "For specific days like 'Tuesday' or 'Friday', use those as departure_date and return_date. "
            f"Travel request: {prompt}"
        )
        logger.debug(f"Extracting travel request with prompt: {parse_prompt}")
        logger.debug(f"Chat history: {chat_history}")
        
        try:
            response = self.openai_client.extract_travel_request(parse_prompt, chat_history)
            logger.debug(f"Raw extracted travel request: {response}")
        except Exception as e:
            logger.error(f"Error in OpenAI extraction: {str(e)}", exc_info=True)
            return {"error": f"Failed to extract travel request: {str(e)}"}
        
        if isinstance(response, dict) and 'message' in response:
            response_text = response['message']
        elif isinstance(response, str):
            response_text = response
        else:
            logger.error(f"Unexpected response format: {response}")
            return {"error": "Failed to parse travel request. Unexpected response format."}

        logger.debug(f"Response text before JSON parsing: {response_text}")
        
        if not response_text.strip():
            logger.error("Empty response text")
            return {"error": "Failed to parse travel request. Empty response from OpenAI."}

        # Remove Markdown code block syntax if present
        response_text = re.sub(r'^```json\s*|\s*```$', '', response_text.strip())

        try:
            parsed_request = json.loads(response_text)
            logger.debug(f"Parsed JSON request: {parsed_request}")
            
            # Process dates and normalize airport codes
            self._process_dates(parsed_request)
            self._normalize_airport_codes(parsed_request)
            
            return parsed_request
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {str(e)}", exc_info=True)
            logger.error(f"Failed JSON string: {response_text}")
            return {"error": f"Failed to parse travel request. JSON error: {str(e)}"}

    def _process_dates(self, parsed_request: Dict[str, Any]) -> None:
        departure_date = None
        for key in ['departure_date', 'return_date', 'check_in', 'check_out']:
            if parsed_request[key] and parsed_request[key].lower() in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']:
                if key == 'departure_date':
                    parsed_request[key] = get_next_weekday(parsed_request[key])
                    departure_date = datetime.strptime(parsed_request[key], '%Y-%m-%d')
                elif key == 'return_date' and departure_date:
                    parsed_request[key] = get_next_weekday(parsed_request[key], departure_date)
                else:
                    parsed_request[key] = get_next_weekday(parsed_request[key])
            else:
                parsed_request[key] = parse_date(parsed_request[key])

        if parsed_request['check_in'] == 'this weekend' or parsed_request['check_out'] == 'this weekend':
            parsed_request['check_in'], parsed_request['check_out'] = get_weekend_dates()

        if parsed_request['origin'] is None and self.default_origin:
            parsed_request['origin'] = self.default_origin

        if parsed_request['departure_date'] and parsed_request['return_date']:
            dep_date = datetime.strptime(parsed_request['departure_date'], '%Y-%m-%d')
            ret_date = datetime.strptime(parsed_request['return_date'], '%Y-%m-%d')
            if ret_date <= dep_date:
                ret_date = dep_date + timedelta(days=1)
                parsed_request['return_date'] = ret_date.strftime('%Y-%m-%d')

    def _normalize_airport_codes(self, travel_request: Dict[str, Any]) -> None:
        if travel_request["origin"]:
            travel_request["origin"] = travel_request["origin"].upper()
        if travel_request["destination"]:
            travel_request["destination"] = travel_request["destination"].upper()

    def plan_trip(self, travel_request: Dict[str, Any]) -> Tuple[str, List[Any]]:
        response = ""
        flights = []

        hotel_response = self._search_hotels(travel_request)
        if hotel_response:
            response += hotel_response

        flight_response, flights = self._search_flights(travel_request)
        if flight_response:
            response += flight_response

        suggestion_response = self._generate_suggestions(travel_request)
        if suggestion_response:
            response += suggestion_response

        if not response:
            response = self._handle_insufficient_info(travel_request)

        return response.strip(), flights

    async def _search_hotels(self, travel_request: dict) -> Tuple[str, List[Any]]:
        """Search for hotels based on the travel request."""
        if travel_request.get("destination") and travel_request.get("check_in") and travel_request.get("check_out"):
            hotels = self.hotel_search.search_hotels(
                location=travel_request["destination"],
                check_in_date=travel_request["check_in"],
                check_out_date=travel_request["check_out"],
                adults=travel_request.get("adults", "2"),
                children=travel_request.get("children", "0"),
                rating=travel_request.get("rating", "8"),
                currency=travel_request.get("currency", "USD"),
                min_price=travel_request.get("min_price"),
                max_price=travel_request.get("max_price"),
                amenities=travel_request.get("amenities"),
                property_types=travel_request.get("property_types")
            )
            response = f"Hotels in {travel_request['destination']} from {travel_request['check_in']} to {travel_request['check_out']}:\n"
            response += f"{hotels}\n\n"
            return response
        return "Insufficient information to search for hotels."

    async def _search_flights(self, travel_request: dict) -> Tuple[str, List[Any]]:
        """Search for flights based on the travel request."""
        logger.debug(f"Searching flights with parameters: {travel_request}")
        if travel_request.get("origin") and travel_request.get("destination") and travel_request.get("departure_date"):
            flights = self.flight_search.search_flights(
                origin=travel_request["origin"],
                destination=travel_request["destination"],
                departure_date=travel_request["departure_date"],
                return_date=travel_request.get("return_date"),
                adults=travel_request.get("adults", "1"),
                travel_class=travel_request.get("travel_class", "1")
            )
            response = f"Flights from {travel_request['origin']} to {travel_request['destination']} on {travel_request['departure_date']}:\n"
            response += f"{flights}\n\n"
            return response
        return "Insufficient information to search for flights."

    def _generate_suggestions(self, travel_request: Dict[str, Any]) -> str:
        if travel_request["destination"] and not (travel_request["origin"] or (travel_request["check_in"] and travel_request["check_out"])):
            suggestions = self.generate_travel_suggestions(travel_request["destination"])
            return f"Suggestions for {travel_request['destination']}:\n{suggestions}"
        return ""

    def _handle_insufficient_info(self, travel_request: Dict[str, Any]) -> str:
        return "I'm sorry, but I couldn't determine what specific travel information you need. Could you please provide more details about what you're looking for?"

    def search_return_flights(self, departure_token: str, return_date: str) -> str:
        try:
            return self.flight_search.search_flights(
                origin="",
                destination="",
                departure_date="",
                return_date=return_date,
                departure_token=departure_token
            )
        except Exception as e:
            return f"An error occurred while searching for return flights: {str(e)}"