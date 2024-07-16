import os
from dotenv import load_dotenv

# Load environment variables at the very beginning
load_dotenv()

# Ensure OPENAI_API_KEY is set
if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("OPENAI_API_KEY is not set in environment variables")

# Now import the rest of the modules
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
from app.assistant_manager import AssistantManager
from openai import OpenAI

async def main():
    # Initialize database
    db_manager = DatabaseManager(os.getenv('DATABASE_URL'))
    db_manager.create_connection()

    # Initialize services
    prompt_generator = PromptGenerator()
    travel_planner = TravelPlanner()
    task_manager = TaskManager(db_manager, OpenAI)
    document_searcher = DocumentSearcher([])  # Initialize with empty document list

    # Initialize AssistantManager
    assistant_manager = AssistantManager()

    # Create or retrieve the assistant
    assistant_name = "BeardoGPT"
    assistants = await assistant_manager.list_assistants()
    if assistant_name in assistants:
        assistant_id = assistants[assistant_name]
    else:
        assistant = await assistant_manager.create_assistant(
            name=assistant_name,
            instructions="You are a personal assistant for a digital marketing CEO. Answer questions in 1 sentence or less unless specifically asked for more context.",
            tools=[],  # Add any tools if necessary
            model="gpt-3.5-turbo-0125"  # Specify the model to use
        )
        assistant_id = assistant.id

    # Set up and initialize Slack app
    slack_app = initialize_slack_app(
        prompt_generator=prompt_generator,
        travel_planner=travel_planner,
        task_manager=task_manager,
        document_searcher=document_searcher,
        assistant_id=assistant_id  # Pass the assistant ID to the Slack app
    )

    # Start the app
    logger.info("Starting the AI-Powered Personal Assistant Slack Bot")

    slack_app.start(port=3000)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())