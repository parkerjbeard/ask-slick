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

            flights_by_airline = defaultdict(list)
            all_flights = data.get("best_flights", []) + data.get("other_flights", [])
            
            for flight_group in all_flights:
                for flight in flight_group.get("flights", []):
                    flight_info = {
                        "airline": flight.get("airline"),
                        "flight_number": flight.get("flight_number"),
                        "departure": f"{flight['departure_airport']['id']} at {flight['departure_airport']['time']}",
                        "arrival": f"{flight['arrival_airport']['id']} at {flight['arrival_airport']['time']}",
                        "price": flight_group.get("price"),
                        "duration": flight.get("duration"),
                        "stops": len(flight_group.get("flights", [])) - 1
                    }
                    flights_by_airline[flight_info["airline"]].append(flight_info)

            # Sort flights within each airline by price
            for airline in flights_by_airline:
                flights_by_airline[airline].sort(key=itemgetter("price"))

            # Create a formatted output string
            output = f"*Flights from {origin} to {destination} on {departure_date}:*\n\n"
            for airline, flights in sorted(flights_by_airline.items()):
                for flight in flights:
                    duration_hours, duration_minutes = divmod(flight["duration"], 60)
                    output += (
                        f"• {airline} {flight['flight_number']}: ${flight['price']} - "
                        f"{duration_hours}h {duration_minutes}m - {flight['stops']} stop(s)\n"
                    )
                output += "\n"  # Add a newline between airlines

            logger.info(f"Found {sum(len(flights) for flights in flights_by_airline.values())} flights")
            return {"formatted_output": output.strip()}

        except requests.RequestException as e:
            logger.error(f"Error in search_flights: {str(e)}")
            return {"error": f"Failed to retrieve flight data: {str(e)}"}

def create_flight_search() -> FlightSearch:
    """
    Factory function to create a FlightSearch instance.
    """
    return FlightSearch()