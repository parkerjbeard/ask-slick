import os
from openai import OpenAI
from typing import Dict, Any
from utils.logger import logger
import json
from datetime import datetime, timedelta
from .search_flight import create_flight_search
from .search_hotel import create_hotel_search
from utils.dates_format import parse_date, get_weekend_dates, get_next_weekday

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class TravelPlanner:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            logger.error("OpenAI API key is not set in environment variables")
            raise ValueError("OpenAI API key is not set")
        self.default_origin = os.getenv("DEFAULT_ORIGIN", "")
        if not self.default_origin:
            logger.warning("DEFAULT_ORIGIN is not set in environment variables")

        self.flight_search = create_flight_search()
        self.hotel_search = create_hotel_search()

    def parse_travel_request(self, origin: str, destination: str, departure_date: str, return_date: str = None, check_in: str = None, check_out: str = None) -> dict:
        try:
            parsed_request = {
                "origin": origin,
                "destination": destination,
                "departure_date": departure_date,
                "return_date": return_date,
                "check_in": check_in,
                "check_out": check_out
            }

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
                    parsed_date = parse_date(parsed_request[key])
                    if parsed_date:
                        # Ensure the date is in the future
                        current_year = datetime.now().year
                        parsed_year = datetime.strptime(parsed_date, '%Y-%m-%d').year
                        if parsed_year < current_year:
                            # If the parsed year is in the past, update it to the next occurrence
                            updated_date = datetime.strptime(parsed_date, '%Y-%m-%d').replace(year=current_year)
                            if updated_date < datetime.now():
                                updated_date = updated_date.replace(year=current_year + 1)
                            parsed_request[key] = updated_date.strftime('%Y-%m-%d')
                        else:
                            parsed_request[key] = parsed_date
                    else:
                        parsed_request[key] = None

            if parsed_request['check_in'] == 'this weekend' or parsed_request['check_out'] == 'this weekend':
                parsed_request['check_in'], parsed_request['check_out'] = get_weekend_dates()

            if parsed_request['origin'] is None and self.default_origin:
                parsed_request['origin'] = self.default_origin

            # Ensure return_date is after departure_date
            if parsed_request['departure_date'] and parsed_request['return_date']:
                dep_date = datetime.strptime(parsed_request['departure_date'], '%Y-%m-%d')
                ret_date = datetime.strptime(parsed_request['return_date'], '%Y-%m-%d')
                if ret_date <= dep_date:
                    ret_date = dep_date + timedelta(days=1)
                    parsed_request['return_date'] = ret_date.strftime('%Y-%m-%d')

            required_keys = ["origin", "destination", "departure_date", "return_date", "check_in", "check_out"]
            if not all(key in parsed_request for key in required_keys):
                logger.error(f"Parsed request is missing required keys: {parsed_request}")
                return {"error": "Failed to parse travel request. Please provide more details."}

            # Validate airport codes
            if not self._is_valid_airport_code(parsed_request['origin']):
                logger.warning(f"Invalid origin airport code: {parsed_request['origin']}")
            if not self._is_valid_airport_code(parsed_request['destination']):
                logger.warning(f"Invalid destination airport code: {parsed_request['destination']}")

            return parsed_request

        except Exception as e:
            logger.error(f"Error in parse_travel_request: {str(e)}")
            return {"error": f"Failed to parse travel request: {str(e)}"}

    def _is_valid_airport_code(self, code: str) -> bool:
        """
        Check if the given code is a valid 3-letter airport code.
        This is a simple check and might need to be expanded with a proper airport code database.
        """
        return code is not None and isinstance(code, str) and len(code) == 3 and code.isalpha()

    def plan_trip(self, travel_request: dict) -> (str, list):
        """
        Plan a trip based on the parsed travel request.
        """
        try:
            response = ""
            flights = []
            logger.info(f"Planning trip with request: {json.dumps(travel_request, indent=2)}")

            if travel_request["destination"] and travel_request["check_in"] and travel_request["check_out"]:
                logger.info(f"Searching for accommodations in {travel_request['destination']} from {travel_request['check_in']} to {travel_request['check_out']}")
                accommodations = self.hotel_search.search_hotels(
                    travel_request["destination"],
                    travel_request["check_in"],
                    travel_request["check_out"]
                )
                response += f"Accommodations in {travel_request['destination']} from {travel_request['check_in']} to {travel_request['check_out']}:\n"
                response += f"{json.dumps(accommodations, indent=2)}\n\n"
                logger.info(f"Found {len(accommodations)} accommodations")

            if travel_request["origin"] and travel_request["destination"] and travel_request["departure_date"]:
                logger.info(f"Searching for flights from {travel_request['origin']} to {travel_request['destination']} on {travel_request['departure_date']}")
                flights = self.flight_search.search_flights(
                    travel_request["origin"],
                    travel_request["destination"],
                    travel_request["departure_date"],
                    travel_request["return_date"]
                )
                response += f"Flights from {travel_request['origin']} to {travel_request['destination']} on {travel_request['departure_date']}:\n"
                response += f"{flights}\n\n"  # Directly append the string output
                logger.info("Found best flights")

            if travel_request["destination"] and not (travel_request["origin"] or (travel_request["check_in"] and travel_request["check_out"])):
                logger.info(f"Generating travel suggestions for {travel_request['destination']}")
                suggestions = self.generate_travel_suggestions(travel_request["destination"])
                response += f"Suggestions for {travel_request['destination']}:\n{suggestions}"
                logger.info("Generated travel suggestions")

            if not response:
                logger.warning("Insufficient information provided in the travel request")
                logger.info(f"Missing information: {[k for k, v in travel_request.items() if v is None]}")
                response = "I'm sorry, but I couldn't determine what specific travel information you need. Could you please provide more details about what you're looking for?"

            logger.info("Trip planning completed successfully")
            return response.strip(), flights
        except Exception as e:
            logger.error(f"Error in plan_trip: {str(e)}", exc_info=True)
            return f"An error occurred while planning your trip: {str(e)}", []

    def search_return_flights(self, departure_token: str, return_date: str) -> str:
        try:
            flights = self.flight_search.search_flights(
                origin="",
                destination="",
                departure_date="",
                return_date=return_date,
                departure_token=departure_token
            )
            return flights
        except Exception as e:
            logger.error(f"Error in search_return_flights: {str(e)}", exc_info=True)
            return f"An error occurred while searching for return flights: {str(e)}"