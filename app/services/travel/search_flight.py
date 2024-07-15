import os
from typing import Dict, Any, Optional
from utils.logger import logger
import requests
from collections import defaultdict
from operator import itemgetter
from datetime import datetime, timedelta

class FlightSearch:
    def __init__(self):
        self.serpapi_api_key = os.getenv("SERPAPI_API_KEY")
        if not self.serpapi_api_key:
            logger.error("SerpAPI API key is not set in environment variables")
            raise ValueError("SerpAPI API key is not set")

        # Default values for optional parameters
        self.default_params = {
            "currency": "USD",
            "hl": "en",  # Default language to English
            "gl": "us",  # Default country to United States
            "travel_class": "1",  # Default to Economy class
            "adults": "1",  # Default to 1 adult
            "children": "0",
            "infants_in_seat": "0",
            "infants_on_lap": "0",
            "stops": "0",  # Default to any number of stops
            "show_hidden": "false"
        }

    def search_flights(self, origin: str, destination: str, departure_date: str, return_date: Optional[str] = None, **kwargs) -> dict:
        """
        Search for flights using the SerpAPI Google Flights API with advanced options.
        """
        try:
            base_url = "https://serpapi.com/search"
            params = {
                "engine": "google_flights",
                "api_key": self.serpapi_api_key,
                "departure_id": origin,
                "arrival_id": destination,
                "outbound_date": departure_date,
            }
            
            # Handle trip type and return date
            if return_date:
                # Ensure return_date is after departure_date
                dep_date = datetime.strptime(departure_date, '%Y-%m-%d')
                ret_date = datetime.strptime(return_date, '%Y-%m-%d')
                if ret_date <= dep_date:
                    ret_date = dep_date + timedelta(days=1)
                    return_date = ret_date.strftime('%Y-%m-%d')
                
                params["return_date"] = return_date
                params["type"] = kwargs.get("type", "1")  # Default to round trip
            else:
                params["type"] = "2"

            # Add default parameters
            params.update(self.default_params)

            # Add or override with provided optional parameters
            optional_params = [
                "gl", "hl", "currency", "travel_class", "show_hidden", "adults", "children",
                "infants_in_seat", "infants_on_lap", "stops", "exclude_airlines", "include_airlines",
                "bags", "max_price", "outbound_times", "return_times", "emissions", "layover_duration",
                "exclude_conns", "max_duration"
            ]

            for param in optional_params:
                if param in kwargs:
                    params[param] = kwargs[param]

            logger.info(f"Searching flights with params: {params}")
            response = requests.get(base_url, params=params)
            logger.info(f"Response from SerpAPI: {response.json()}")
            response.raise_for_status()
            data = response.json()

            if "error" in data:
                logger.error(f"SerpAPI error: {data['error']}")
                return {"error": "Failed to retrieve flight data"}

            best_flights = data.get("best_flights", [])
            if not best_flights:
                return {"formatted_output": ["No best flights found"]}

            # Extract and format the best flights
            formatted_output = []
            for flight_group in best_flights:
                for flight in flight_group.get("flights", []):
                    duration_hours, duration_minutes = divmod(flight["duration"], 60)
                    formatted_output.append(
                        f"{flight['airline']} - ${flight_group['price']} - {flight['departure_airport']['time']} - "
                        f"{duration_hours}h {duration_minutes}m - {len(flight_group.get('flights', [])) - 1} stop(s)"
                    )

            logger.info(f"Found {len(best_flights)} best flights")
            return {"formatted_output": formatted_output}

        except requests.RequestException as e:
            logger.error(f"Error in search_flights: {str(e)}")
            return {"error": f"Failed to retrieve flight data: {str(e)}"}

def create_flight_search() -> FlightSearch:
    """
    Factory function to create a FlightSearch instance.
    """
    return FlightSearch()