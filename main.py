import os
from dotenv import load_dotenv
load_dotenv()

import asyncio
from app.slack_bot import create_slack_bot
from app.services.travel.travel_planner import TravelPlanner
from utils.logger import logger

def main():
    # Initialize services
    travel_planner = TravelPlanner()

    # Set up and initialize Slack app
    slack_app = create_slack_bot(travel_planner)

    # Start the app
    logger.info("Starting the AI-Powered Personal Assistant Slack Bot")
    slack_app.start(port=3000)

if __name__ == "__main__":
    main()