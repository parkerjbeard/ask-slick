import os
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from app.slack_bot import initialize_slack_app
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

def main():
    # Load environment variables
    load_dotenv()

    # Initialize database
    db_manager = DatabaseManager(os.getenv('DATABASE_URL'))
    db_manager.create_connection()

    # Initialize clients
    openai_client = OpenAIClient()
    openai.api_key = os.getenv("OPENAI_API_KEY")

    # Initialize services
    prompt_generator = PromptGenerator()
    travel_planner = TravelPlanner()
    task_manager = TaskManager(db_manager, openai_client)
    document_searcher = DocumentSearcher([])  # Initialize with empty document list

    # Set up and initialize Slack app
    slack_app = initialize_slack_app(
        prompt_generator=prompt_generator,
        travel_planner=travel_planner,
        task_manager=task_manager,
        document_searcher=document_searcher
    )

    # Start the app
    logger.info("Starting the AI-Powered Personal Assistant Slack Bot")
    
    slack_app.start(port=3000)

if __name__ == "__main__":
    main()