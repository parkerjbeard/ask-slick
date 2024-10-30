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
    GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
    GOOGLE_REDIRECT_URI = os.getenv('GOOGLE_REDIRECT_URI')
    KMS_KEY_ID = os.getenv('KMS_KEY_ID')
    GOOGLE_API_VERSION = os.getenv('GOOGLE_API_VERSION', 'v3')
settings = Settings()
