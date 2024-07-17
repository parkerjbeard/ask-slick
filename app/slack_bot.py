import os
import json
import asyncio
from slack_bolt import App
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from app.openai_client import OpenAIClient
from app.assistant_manager import AssistantManager
from app.dispatcher import Dispatcher
from app.services.travel.travel_planner import TravelPlanner
from utils.logger import logger
from slack_bolt.async_app import AsyncApp

def create_slack_bot(travel_planner: TravelPlanner):
    logger.info("Creating Slack bot")
    app = AsyncApp(
        token=os.environ.get("SLACK_BOT_TOKEN"),
        signing_secret=os.environ.get("SLACK_SIGNING_SECRET")
    )
    logger.info("Slack bot created")

    assistant_manager = AssistantManager()
    dispatcher = Dispatcher()

    @app.event("message")
    async def handle_message_events(event, say):
        #logger.info(f"Received event: {event}")
        await process_message_event(event, say, travel_planner, assistant_manager, dispatcher)

    logger.info("Message event handler registered")

    @app.error
    async def global_error_handler(error, body, logger):
        logger.error(f"Error: {error}")
        logger.error(f"Request body: {body}")

    # Additional logging to verify the bot is running
    logger.info("Starting Slack bot")

    return app

async def process_message_event(event, say, travel_planner, assistant_manager, dispatcher):
    text = event.get("text", "")
    user = event.get("user")
    channel = event.get("channel")
    bot_id = os.environ.get("SLACK_BOT_ID")

    logger.info(f"Received message: {text}")

    if not text or not user:
        logger.warning("Ignoring message: Missing text or user")
        return

    text = text.lower()
    logger.info(f"Processing message: {text}")

    run, thread = await dispatcher.dispatch(text) 
    run = await assistant_manager.wait_on_run(thread.id, run.id)

    tool_call = await assistant_manager.handle_tool_call(run)
    responses = await handle_tool_call(tool_call, travel_planner)

    run = await assistant_manager.submit_tool_outputs(thread.id, run.id, tool_call, responses)
    run = await assistant_manager.wait_on_run(thread.id, run.id)

    messages = await assistant_manager.get_response(thread.id)
    assistant_response = messages.data[-1].content[0].text.value

    send_slack_response(say, assistant_response, responses, channel, event.get("ts"))
    assistant_manager.pretty_print(messages.data)

async def handle_tool_call(tool_call, travel_planner):
    name = tool_call.function.name
    if name == "parse_travel_request":
        arguments = json.loads(tool_call.function.arguments)
        travel_request = travel_planner.parse_travel_request(**arguments)
        if "error" in travel_request:
            return travel_request["error"]
        else:
            return travel_planner.plan_trip(travel_request)
    return None

def send_slack_response(say, assistant_response, tool_responses, channel, thread_ts):
    say(text=assistant_response, channel=channel, thread_ts=thread_ts)
    if tool_responses:
        say(tool_responses)