import os
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timedelta
import requests
from utils.logger import logger
import traceback

class FlightSearch:
    def __init__(self):
        self.serpapi_api_key = os.getenv("SERPAPI_API_KEY")
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

    def search_flights(self, origin: str, destination: str, departure_date: str, return_date: Optional[str] = None, **kwargs) -> str:
        logger.debug(f"Searching flights with parameters: origin={origin}, destination={destination}, departure_date={departure_date}, return_date={return_date}, kwargs={kwargs}")
        try:
            params = self._build_params(origin, destination, departure_date, return_date, **kwargs)
            response = requests.get("https://serpapi.com/search", params=params)
            response.raise_for_status()
            data = response.json()

            if "error" in data:
                return f"Failed to retrieve flight data: {data['error']}"

            best_flights = data.get("best_flights", [])
            if not best_flights:
                return "No best flights found"

            formatted_results = self._format_flight_results(best_flights)
            logger.debug(f"Flight search results: {formatted_results}")
            return formatted_results
        except requests.RequestException as e:
            logger.error(f"Error searching for flights: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return f"Failed to retrieve flight data: {str(e)}"

    def _build_params(self, origin: str, destination: str, departure_date: str, return_date: Optional[str], **kwargs) -> Dict[str, Any]:
        params = {
            "engine": "google_flights",
            "api_key": self.serpapi_api_key,
            "departure_id": origin,
            "arrival_id": destination,
            "outbound_date": departure_date,
        }

        if return_date:
            params["return_date"] = self._validate_return_date(departure_date, return_date)
            params["type"] = kwargs.get("type", "1")  # Default to round trip
        else:
            params["type"] = "2"  # One-way trip

        params.update(self.default_params)
        params.update({k: v for k, v in kwargs.items() if k in self._get_optional_params()})

        return params

    def _validate_return_date(self, departure_date: str, return_date: str) -> str:
        dep_date = datetime.strptime(departure_date, '%Y-%m-%d')
        ret_date = datetime.strptime(return_date, '%Y-%m-%d')
        if ret_date <= dep_date:
            ret_date = dep_date + timedelta(days=1)
        return ret_date.strftime('%Y-%m-%d')

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
            flight_details = []
            for flight in flight_group.get("flights", []):
                duration_hours, duration_minutes = divmod(flight["duration"], 60)
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
                f"{idx}. {flight_group['airline']} - ${flight_group['price']} - {len(flight_group.get('flights', [])) - 1} stop(s):\n" +
                "\n".join(flight_details)
            )
        return "\n\n".join(formatted_output)

def create_flight_search() -> FlightSearch:
    return FlightSearch()