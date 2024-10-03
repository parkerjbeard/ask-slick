import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    SLACK_BOT_TOKEN = os.getenv('SLACK_BOT_TOKEN')
    DATABASE_URL = os.getenv('DATABASE_URL')
    SLACK_APP_TOKEN = os.getenv('SLACK_APP_TOKEN')
    SERPAPI_API_KEY = os.getenv('SERPAPI_API_KEY')
    SLACK_SIGNING_SECRET = os.getenv('SLACK_SIGNING_SECRET')
    DEFAULT_ORIGIN = os.getenv('DEFAULT_ORIGIN')
    DEFAULT_TIMEZONE = os.getenv('DEFAULT_TIMEZONE')

settings = Settings()
