from typing import Dict, Any, List
from app.services.api_integrations import APIIntegration
from app.services.travel.search_flight import FlightSearch
from app.services.travel.search_hotel import HotelSearch
from utils.logger import logger

class TravelIntegration(APIIntegration):
    def __init__(self):
        self.flight_search = FlightSearch()
        self.hotel_search = HotelSearch()

    async def execute(self, function_name: str, params: dict) -> str:
        logger.debug(f"TravelIntegration executing function: {function_name} with params: {params}")
        
        if function_name == "search_flights":
            required_params = ["origin", "destination", "departure_date"]
            if not all(param in params for param in required_params):
                missing_params = [param for param in required_params if param not in params]
                logger.error(f"Missing required parameters for flight search: {missing_params}")
                return f"Unable to search for flights. Missing information: {', '.join(missing_params)}"
            return await self._search_flights(params)
        elif function_name == "search_hotels":
            return await self._search_hotels(params)
        else:
            logger.warning(f"Unknown function in TravelIntegration: {function_name}")
            return f"Unknown function: {function_name}"

    async def _search_flights(self, params: dict) -> str:
        if not params:
            return "No parameters provided for flight search"

        required_params = ["origin", "destination", "departure_date"]
        if not all(param in params for param in required_params):
            missing_params = [param for param in required_params if param not in params]
            return f"Missing required parameters for flight search: {', '.join(missing_params)}"
        
        try:
            return self.flight_search.search_flights(params)
        except Exception as e:
            logger.error(f"Error in flight search: {str(e)}", exc_info=True)
            return f"An error occurred during flight search: {str(e)}"

    async def _search_hotels(self, params: dict) -> str:
        required_params = ["location", "check_in_date", "check_out_date"]
        if not all(param in params for param in required_params):
            missing_params = [param for param in required_params if param not in params]
            return f"Missing required parameters for hotel search: {', '.join(missing_params)}"
        
        try:
            return self.hotel_search.search_hotels(**params)
        except Exception as e:
            logger.error(f"Error in hotel search: {str(e)}", exc_info=True)
            return f"An error occurred during hotel search: {str(e)}"

    def get_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "search_flights",
                    "description": "Search for flights using the SerpAPI Google Flights API with advanced options.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "origin": {"type": "string", "description": "The 3-letter airport code for the departure location"},
                            "destination": {"type": "string", "description": "The 3-letter airport code for the arrival location"},
                            "departure_date": {"type": "string", "description": "The date of departure in YYYY-MM-DD format"},
                            "return_date": {"type": "string", "description": "The date of return in YYYY-MM-DD format (optional for one-way trips)"},
                            "currency": {"type": "string", "description": "Currency code (e.g., USD, EUR)"},
                            "travel_class": {"type": "string", "description": "Travel class (e.g., '1' for Economy, '2' for Premium Economy, '3' for Business, '4' for First Class)"},
                            "adults": {"type": "string", "description": "Number of adult passengers"},
                            "children": {"type": "string", "description": "Number of child passengers"},
                            "infants_in_seat": {"type": "string", "description": "Number of infants in seat"},
                            "infants_on_lap": {"type": "string", "description": "Number of infants on lap"},
                            "stops": {"type": "string", "description": "Number of stops (e.g., '0' for non-stop, '1' for one stop)"},
                            "max_price": {"type": "string", "description": "Maximum price for flights"}
                        },
                        "required": ["origin", "destination", "departure_date"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_hotels",
                    "description": "Search for hotels using the SerpAPI Google Hotels API with advanced options.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "destination": {"type": "string", "description": "The location to search for hotels"},
                            "check_in": {"type": "string", "description": "The check-in date in YYYY-MM-DD format"},
                            "check_out": {"type": "string", "description": "The check-out date in YYYY-MM-DD format"},
                            "currency": {"type": "string", "description": "Currency code (e.g., USD, EUR)"},
                            "adults": {"type": "string", "description": "Number of adult guests"},
                            "children": {"type": "string", "description": "Number of child guests"},
                            "rating": {"type": "string", "description": "Minimum hotel rating (e.g., '8' for 4-star and above)"},
                            "min_price": {"type": "string", "description": "Minimum price for hotels"},
                            "max_price": {"type": "string", "description": "Maximum price for hotels"},
                            "amenities": {"type": "string", "description": "Comma-separated list of desired amenities"},
                            "property_types": {"type": "string", "description": "Comma-separated list of desired property types"}
                        },
                        "required": ["destination", "check_in", "check_out"]
                    }
                }
            }
        ]

    def get_instructions(self) -> str:
        return """You are a friendly Travel Assistant chatbot. Your job is to help users plan trips, find flights and hotels, and give travel tips. Keep your responses short, fun, and easy to read.

        When users ask about flights or hotels, use these functions:
        - 'search_flights' for flight info
        - 'search_hotels' for hotel info

        For travel recommendations:
        1. Suggest 3 must-see attractions
        2. Mention 2 unique local experiences
        3. Recommend 2 great places to eat (use $ for cheap, $$ for mid-range, $$$ for expensive)
        4. Suggest 1 cool day trip
        5. Give a quick tip on getting around

        Be specific with names and brief descriptions. Mix it up with history, culture, food, and fun activities. Keep it casual and chatty, like you're texting a friend!

        Remember, keep your entire response in one message and make it snappy!
        """