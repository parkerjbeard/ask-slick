import dateparser
from datetime import datetime, timedelta

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