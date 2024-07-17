import os
from dotenv import load_dotenv
load_dotenv()

import asyncio
from app.slack_bot import create_slack_bot
from app.services.travel.travel_planner import TravelPlanner
from utils.logger import logger
from app.assistant_manager import AssistantManager
from app.dispatcher import Dispatcher

async def update_assistants():
    assistant_manager = AssistantManager()
    dispatcher = Dispatcher()
    
    assistants = await assistant_manager.list_assistants()
    
    for assistant_name in ["TravelAssistant", "EmailAssistant", "GeneralAssistant"]:
        assistant_id = assistants.get(assistant_name)
        tools, model = dispatcher.get_tools_for_assistant(assistant_name)
        instructions = f"You are a {assistant_name}."
        
        if assistant_id:
            await assistant_manager.update_assistant(
                assistant_id=assistant_id,
                instructions=instructions,
                tools=tools
            )
            logger.info(f"Updated {assistant_name} with new tools and instructions")
        else:
            logger.info(f"{assistant_name} not found, creating a new one")
            await assistant_manager.create_assistant(
                name=assistant_name,
                instructions=instructions,
                tools=tools,
                model=model
            )

async def setup():
    # Update assistants
    await update_assistants()

    # Initialize services
    travel_planner = TravelPlanner()

    # Set up and initialize Slack app
    slack_app = create_slack_bot(travel_planner)
    return slack_app

def main():
    # Run the setup in the asyncio event loop
    slack_app = asyncio.get_event_loop().run_until_complete(setup())

    # Start the app
    logger.info("Starting the AI-Powered Personal Assistant Slack Bot")
    slack_app.start(port=3000)

if __name__ == "__main__":
    main()