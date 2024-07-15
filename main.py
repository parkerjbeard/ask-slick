import os
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from app.slack_bot import app as slack_app
from app.google_client import GoogleClient
from app.openai_client import OpenAIClient
from app.services.calendar.calendar_manager import CalendarAssistant
from app.services.texts.prompt_generator import PromptGenerator
from app.services.travel.travel_planner import TravelPlanner
from app.services.todo.task_manager import TaskManager
from app.services.document_retrieval.document_searcher import DocumentSearcher
from database.db_manager import DatabaseManager
from utils.logger import logger
import openai

def lambda_handler(event, context):
    # Parse the incoming event from API Gateway
    body = json.loads(event['body'])
    
    # Process the Slack event
    slack_handler = SlackRequestHandler(slack_app)
    response = slack_handler.handle(body)
    
    return {
        'statusCode': 200,
        'body': json.dumps(response)
    }

def main():
    # Load environment variables
    load_dotenv()

    # Initialize database
    db_manager = DatabaseManager(os.getenv('DATABASE_URL'))
    db_manager.create_connection()

    # Initialize clients
    #google_client = GoogleClient()
    openai_client = OpenAIClient()
    openai.api_key = os.getenv("OPENAI_API_KEY")

    # Initialize services
    #calendar_assistant = CalendarAssistant(google_client, openai_client)
    prompt_generator = PromptGenerator()
    travel_planner = TravelPlanner()
    task_manager = TaskManager(db_manager, openai_client)
    document_searcher = DocumentSearcher([])  # Initialize with empty document list

    # Set up Slack app
    #slack_app.calendar_manager = calendar_assistant
    slack_app.prompt_generator = prompt_generator
    slack_app.travel_planner = travel_planner
    slack_app.task_manager = task_manager
    slack_app.document_searcher = document_searcher

    # Start the app
    logger.info("Starting the AI-Powered Personal Assistant Slack Bot")
    handler = SocketModeHandler(slack_app, os.environ["SLACK_APP_TOKEN"])
    handler.start()

if __name__ == "__main__":
    main()