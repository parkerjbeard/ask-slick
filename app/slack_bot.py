from slack_bolt import App
import os
from app.services.travel.travel_planner import TravelPlanner
import traceback
from utils.logger import logger
from app.openai_client import OpenAIClient

def initialize_slack_app(prompt_generator, travel_planner, task_manager, document_searcher):
    # Initialize the Slack app
    app = App(
        token=os.environ.get("SLACK_BOT_TOKEN"),
        signing_secret=os.environ.get("SLACK_SIGNING_SECRET")
    )

    openai_client = OpenAIClient()

    @app.event("message")
    def handle_message_events(event, say):
        text = event.get("text", "").lower()
        print(text)
        user = event.get("user")

        if not text or not user:
            return

        # Classify the text to determine the category
        categories = ["schedule", "family", "travel", "todo", "document"]
        category = openai_client.classify_text(text, categories)
        print(category)
        logger.debug(f"Classified category: {category}")

        if category == "schedule":
            response = "Schedule a meeting"
        elif category == "family":
            # Assuming user information is fetched from a database or another service
            user_info = {"name": "John Doe", "relationship": "brother", "last_contact": "2023-01-01", "interests": ["hiking", "reading"], "recent_events": ["got a new job"]}
            response = prompt_generator.generate_prompt(user_info["name"], user_info["relationship"], user_info["last_contact"], user_info["interests"], user_info["recent_events"])
        elif category == "travel":
            logger.debug("Handling travel category")
            travel_request = travel_planner.parse_travel_request(text)
            logger.debug(f"Travel request parsed: {travel_request}")
            if "error" in travel_request:
                response = travel_request["error"]
            else:
                response = travel_planner.plan_trip(travel_request)
        elif category == "todo":
            response = task_manager.handle_todo_request(text)
        elif category == "document":
            response = document_searcher.search_documents(text)
        else:
            response = "I'm not sure how to help with that. You can ask me about scheduling, family prompts, travel, todos, or document retrieval."

        logger.debug(f"Response: {response}")
        say(response)

    return app