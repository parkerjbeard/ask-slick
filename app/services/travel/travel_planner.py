import os
import openai
from typing import Dict, Any
from utils.logger import logger
import json
import dateparser
from datetime import datetime, timedelta
from .search_flight import create_flight_search
from .search_hotel import create_hotel_search

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

def get_next_weekday(weekday: str, start_date: datetime = None) -> str:
    """Get the date of the next occurrence of the given weekday."""
    weekdays = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    start_date = start_date or datetime.now()
    target_day = weekdays.index(weekday.lower())
    days_ahead = target_day - start_date.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    next_day = start_date + timedelta(days=days_ahead)
    return next_day.strftime('%Y-%m-%d')

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
        
        self.flight_search = create_flight_search()
        self.hotel_search = create_hotel_search()

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
            parse_prompt = (
                "Parse the following travel request into a JSON format with keys: "
                "origin, destination, departure_date, return_date, check_in, check_out. "
                "For origin and destination, provide the 3-letter airport code. "
                "If any information is missing, use null as the value. "
                "For date ranges like 'this weekend', use the range in the check_in and check_out fields. "
                "For specific days like 'Tuesday' or 'Friday', use those as departure_date and return_date. "
                "You have already been given a default departure origin if one was not provided. If one was provided, this is the new departure origin. "
                f"Travel request: {prompt}"
            )
            response = self._create_message_and_run(parse_prompt)
            
            try:
                parsed_request = json.loads(response["message"])
            except json.JSONDecodeError:
                logger.error(f"Failed to parse JSON from OpenAI response: {response['message']}")
                return {"error": "Failed to parse travel request. Please provide more details."}

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


    def plan_trip(self, travel_request: dict) -> str:
        """
        Plan a trip based on the parsed travel request.
        """
        try:
            response = ""
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
                response += f"{json.dumps(flights, indent=2)}\n\n"
                logger.info(f"Found {len(flights.get('flights', []))} flights")

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
            return response.strip()
        except Exception as e:
            logger.error(f"Error in plan_trip: {str(e)}", exc_info=True)
            return f"An error occurred while planning your trip: {str(e)}"


    def generate_travel_suggestions(self, destination: str) -> str:
        """
        Generate travel suggestions for a given destination using OpenAI.
        """
        prompt = f"Provide travel suggestions for {destination}. Include popular attractions, local cuisine, and cultural experiences."
        response = self._create_message_and_run(prompt)
        return response["message"]

def create_travel_planner() -> TravelPlanner:
    """
    Factory function to create a TravelPlanner instance.
    """
    return TravelPlanner()