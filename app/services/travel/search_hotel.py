import os
from typing import Dict, Any, Optional, List
from utils.logger import logger
import requests

class HotelSearch:
    def __init__(self):
        self.serpapi_api_key = os.getenv("SERPAPI_API_KEY")
        if not self.serpapi_api_key:
            logger.error("SerpAPI API key is not set in environment variables")
            raise ValueError("SerpAPI API key is not set")

        # Default values for optional parameters
        self.default_params = {
            "engine": "google_hotels",
            "currency": "USD",
            "hl": "en",  # Default language to English
            "gl": "us",  # Default country to United States
            "adults": "2",  # Default to 2 adults
            "children": "0",
            "rating": "8",
            "output": "json"
        }

    def search_hotels(self, location: str, check_in_date: str, check_out_date: str, **kwargs) -> dict:
        """
        Search for hotels using the SerpAPI Google Hotels API with advanced options.
        """
        try:
            base_url = "https://serpapi.com/search"
            params = {
                "q": location,
                "check_in_date": check_in_date,
                "check_out_date": check_out_date,
                "api_key": self.serpapi_api_key,
            }
            
            # Add default parameters
            params.update(self.default_params)

            # Add or override with provided optional parameters
            optional_params = [
                "gl", "hl", "currency", "adults", "children", "children_ages",
                "sort_by", "min_price", "max_price", "property_types", "amenities",
                "rating", "brands", "hotel_class", "free_cancellation", "special_offers",
                "eco_certified", "vacation_rentals", "bedrooms", "bathrooms",
                "next_page_token", "property_token", "no_cache", "async"
            ]

            for param in optional_params:
                if param in kwargs:
                    params[param] = kwargs[param]

            response = requests.get(base_url, params=params)
            response.raise_for_status()
            data = response.json()

            if "error" in data:
                logger.error(f"SerpAPI error: {data['error']}")
                return {"error": "Failed to retrieve hotel data"}

            hotels = []
            for hotel in data.get("hotels_results", []):
                hotels.append({
                    "name": hotel.get("name"),
                    "address": hotel.get("address"),
                    "price": hotel.get("price"),
                    "rating": hotel.get("rating"),
                    "reviews": hotel.get("reviews"),
                    "thumbnail": hotel.get("thumbnail"),
                    "property_token": hotel.get("property_token")
                })

            return {
                "hotels": hotels,
                "next_page_token": data.get("serpapi_pagination", {}).get("next_page_token")
            }

        except requests.RequestException as e:
            logger.error(f"Error in search_hotels: {str(e)}")
            return {"error": f"Failed to retrieve hotel data: {str(e)}"}

    def get_hotel_details(self, property_token: str) -> dict:
        """
        Get detailed information about a specific hotel using its property token.
        """
        try:
            base_url = "https://serpapi.com/search"
            params = {
                "engine": "google_hotels",
                "property_token": property_token,
                "api_key": self.serpapi_api_key,
                "output": "json"
            }

            response = requests.get(base_url, params=params)
            response.raise_for_status()
            data = response.json()

            if "error" in data:
                logger.error(f"SerpAPI error: {data['error']}")
                return {"error": "Failed to retrieve hotel details"}

            hotel_data = data.get("hotel_results", {})
            return {
                "name": hotel_data.get("name"),
                "address": hotel_data.get("address"),
                "phone": hotel_data.get("phone"),
                "description": hotel_data.get("description"),
                "check_in_time": hotel_data.get("check_in_time"),
                "check_out_time": hotel_data.get("check_out_time"),
                "rating": hotel_data.get("rating"),
                "reviews": hotel_data.get("reviews"),
                "price": hotel_data.get("price"),
                "website": hotel_data.get("website"),
                "amenities": hotel_data.get("amenities"),
                "images": hotel_data.get("images"),
                "nearby_places": hotel_data.get("nearby_places")
            }

        except requests.RequestException as e:
            logger.error(f"Error in get_hotel_details: {str(e)}")
            return {"error": f"Failed to retrieve hotel details: {str(e)}"}

def create_hotel_search() -> HotelSearch:
    """
    Factory function to create a HotelSearch instance.
    """
    return HotelSearch()