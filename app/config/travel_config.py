from app.config.base_config import BaseConfig

class TravelConfig(BaseConfig):
    SYSTEM_MESSAGE = """You are a travel assistant parsing travel requests. 
    When extracting information, follow these rules:
    1. For origin and destination, always use 3-letter IATA airport codes.
    2. If a specific airport is not mentioned, use the main airport code for the given city, state, or country.
       For example:
       - New York -> JFK (John F. Kennedy International Airport)
       - California -> LAX (Los Angeles International Airport)
       - Japan -> NRT (Narita International Airport)
    3. If the origin is not specified at all, use 'NULL' as the value.
    4. For all other fields, if the information is not provided, leave the field empty.
    5. Always include all fields in the output, even if they are empty.
    6. Use the chat history as context to infer any missing information.
    7. If you're unsure about the correct airport code, use your best judgment to provide the most likely code for the main airport in that location."""

    CATEGORY = "travel"
    ASSISTANT_NAME = "TravelAssistant"
    CATEGORY_DESCRIPTION = "Messages about trips, vacations, flights, hotels, or any travel-related queries."
    FUNCTIONS = ["search_flights", "search_hotels"]

    def get_messages(self, history_context: str, user_input: str, function_name: str) -> list:
        return [
            {"role": "system", "content": self.SYSTEM_MESSAGE},
            {"role": "user", "content": f"Chat history:\n{history_context}\n\nParse the following travel request for {function_name}, using the chat history as context:\n\n{user_input}"}
        ]