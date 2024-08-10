from typing import Dict, Any
from datetime import datetime, timedelta
from .dates_format import parse_date, get_next_weekday, get_weekend_dates

def normalize_airport_codes(travel_request: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize airport codes to uppercase."""
    if travel_request.get("origin") and travel_request["origin"] != "NULL":
        travel_request["origin"] = travel_request["origin"].upper()
    if travel_request.get("destination"):
        travel_request["destination"] = travel_request["destination"].upper()
    return travel_request

def process_travel_dates(parsed_request: Dict[str, Any]) -> Dict[str, Any]:
    """Process and normalize dates in the travel request."""
    departure_date = None
    is_flight_search = 'departure_date' in parsed_request

    date_keys = ['departure_date', 'return_date'] if is_flight_search else ['check_in', 'check_out']

    for key in date_keys:
        if parsed_request.get(key):
            if parsed_request[key].lower() in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']:
                if key == 'departure_date':
                    parsed_request[key] = get_next_weekday(parsed_request[key])
                    departure_date = datetime.strptime(parsed_request[key], '%Y-%m-%d')
                elif key == 'return_date' and departure_date:
                    parsed_request[key] = get_next_weekday(parsed_request[key], departure_date)
                else:
                    parsed_request[key] = get_next_weekday(parsed_request[key])
            else:
                parsed_request[key] = parse_date(parsed_request[key])

    if not is_flight_search and (parsed_request.get('check_in') == 'this weekend' or parsed_request.get('check_out') == 'this weekend'):
        parsed_request['check_in'], parsed_request['check_out'] = get_weekend_dates()

    if is_flight_search and parsed_request.get('departure_date') and parsed_request.get('return_date'):
        dep_date = datetime.strptime(parsed_request['departure_date'], '%Y-%m-%d')
        ret_date = datetime.strptime(parsed_request['return_date'], '%Y-%m-%d')
        if ret_date <= dep_date:
            ret_date = dep_date + timedelta(days=1)
            parsed_request['return_date'] = ret_date.strftime('%Y-%m-%d')

    return parsed_request

def set_default_origin(travel_request: Dict[str, Any], default_origin: str) -> Dict[str, Any]:
    """Set the default origin if not provided or set to NULL in the travel request."""
    if travel_request.get('origin') is None or travel_request['origin'] in ["NULL", "null", "", "none"]:
        travel_request['origin'] = default_origin
    return travel_request