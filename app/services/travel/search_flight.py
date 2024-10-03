from utils.travel_format import normalize_airport_codes, process_travel_dates, set_default_origin
from app.config.settings import settings
from utils.logger import logger
from datetime import datetime
from typing import Dict, Any
import traceback
import requests

class FlightSearch:
    def __init__(self):
        self.serpapi_api_key = settings.SERPAPI_API_KEY
        if not self.serpapi_api_key:
            raise ValueError("SerpAPI API key is not set in environment variables")

        self.default_params = {
            "currency": "USD",
            "hl": "en",
            "gl": "us",
            "travel_class": "1",
            "adults": "1",
            "children": "0",
            "infants_in_seat": "0",
            "infants_on_lap": "0",
            "stops": "0",
            "show_hidden": "false"
        }
        self.default_origin = settings.DEFAULT_ORIGIN

    def search_flights(self, travel_request: Dict[str, Any]) -> str:
        logger.debug(f"Searching flights with travel request: {travel_request}")
        try:
            if not travel_request:
                return "No travel request provided for flight search"

            # Process and normalize the travel request
            processed_request = self._process_travel_request(travel_request)
            
            params = self._build_params(processed_request)
            logger.debug(f"API request params: {params}")
            response = requests.get("https://serpapi.com/search", params=params)
            response.raise_for_status()
            data = response.json()

            #logger.debug(f"API response data: {data}")

            if "error" in data:
                return f"Failed to retrieve flight data: {data['error']}"

            best_flights = data.get("best_flights", [])
            logger.debug(f"Best flights data: {best_flights}")
            if not best_flights:
                return "No best flights found"

            formatted_results = self._format_flight_results(best_flights)
            logger.debug(f"Flight search results: {formatted_results}")
            return formatted_results
        except requests.RequestException as e:
            logger.error(f"Error searching for flights: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return f"Failed to retrieve flight data: {str(e)}"


    def _process_travel_request(self, travel_request: Dict[str, Any]) -> Dict[str, Any]:
        processed_request = travel_request
        
        # Normalize airport codes
        processed_request = normalize_airport_codes(processed_request)
        
        # Process dates
        processed_request = process_travel_dates(processed_request)
        
        # Set default origin if not provided
        processed_request = set_default_origin(processed_request, self.default_origin)
        
        return processed_request

    def _build_params(self, travel_request: Dict[str, Any]) -> Dict[str, Any]:
        params = {
            "engine": "google_flights",
            "api_key": self.serpapi_api_key,
            "departure_id": travel_request["origin"],
            "arrival_id": travel_request["destination"],
            "outbound_date": travel_request["departure_date"],
        }

        if travel_request.get("return_date"):
            params["return_date"] = travel_request["return_date"]
            params["type"] = "1"  # Round trip
        else:
            params["type"] = "2"  # One-way trip

        params.update(self.default_params)
        params.update({k: v for k, v in travel_request.items() if k in self._get_optional_params()})

        return params

    def _get_optional_params(self) -> list:
        return [
            "gl", "hl", "currency", "travel_class", "show_hidden", "adults", "children",
            "infants_in_seat", "infants_on_lap", "stops", "exclude_airlines", "include_airlines",
            "bags", "max_price", "outbound_times", "return_times", "emissions", "layover_duration",
            "exclude_conns", "max_duration"
        ]

    def _format_flight_results(self, best_flights: list) -> str:
        formatted_output = []
        for idx, flight_group in enumerate(best_flights, 1):
            logger.debug(f"Processing flight group {idx}: {flight_group}")
            flight_details = []
            flights = flight_group.get("flights", [])
            
            if not flights:
                logger.warning(f"No flights found in flight group {idx}")
                continue
            
            first_flight = flights[0]
            airline = first_flight.get("airline", "Unknown Airline")
            price = flight_group.get("price", "N/A")
            stops = len(flights) - 1
            
            for flight in flights:
                logger.debug(f"Processing flight: {flight}")
                duration_hours, duration_minutes = divmod(flight.get("duration", 0), 60)
                departure_time = datetime.strptime(flight['departure_airport']['time'], '%Y-%m-%d %H:%M')
                arrival_time = datetime.strptime(flight['arrival_airport']['time'], '%Y-%m-%d %H:%M')
                formatted_departure = departure_time.strftime('%B %d at %H:%M')
                formatted_arrival = arrival_time.strftime('%B %d at %H:%M')
                flight_details.append(
                    f"  - Departure: {flight['departure_airport']['name']} ({flight['departure_airport']['id']}) on {formatted_departure}\n"
                    f"  - Arrival: {flight['arrival_airport']['name']} ({flight['arrival_airport']['id']}) on {formatted_arrival}\n"
                    f"  - Duration: {duration_hours}h {duration_minutes}m"
                )
            
            formatted_output.append(
                f"{idx}. {airline} - ${price} - {stops} stop(s):\n" +
                "\n".join(flight_details)
            )
        
        if not formatted_output:
            return "No flight results could be formatted."
        
        return "\n\n".join(formatted_output)

def create_flight_search() -> FlightSearch:
    return FlightSearch()