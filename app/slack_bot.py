import os
import json
import asyncio
from slack_bolt import App
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from app.openai_helper import OpenAIClient
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

    try:
        logger.info("Dispatching message")
        dispatch_result = await dispatcher.dispatch(text)
        logger.info(f"Dispatch result: {dispatch_result}")
        
        thread_id = dispatch_result.get('thread_id')
        run_id = dispatch_result.get('run_id')
        function_output = dispatch_result.get('function_output')
        
        if not thread_id or not run_id:
            logger.error(f"Invalid dispatch result: {dispatch_result}")
            raise ValueError("Invalid dispatch result")

        if function_output:
            logger.info(f"Function output available: {function_output}")
            await send_slack_response(say, function_output, None, channel, event.get("ts"))
        else:
            logger.info(f"Waiting for run completion: thread_id={thread_id}, run_id={run_id}")
            run = assistant_manager.wait_on_run(thread_id, run_id)
            logger.info(f"Run completed: {run}")

            if run.required_action is not None and run.required_action.type == "submit_tool_outputs":
                logger.info("Tool outputs required")
                tool_calls = run.required_action.submit_tool_outputs.tool_calls
                tool_outputs = []
                for tool_call in tool_calls:
                    logger.info(f"Handling tool call: {tool_call}")
                    response = await handle_tool_call(tool_call, travel_planner)
                    tool_outputs.append({
                        "tool_call_id": tool_call.id,
                        "output": response
                    })
                logger.info(f"Submitting tool outputs: {tool_outputs}")
                run = assistant_manager.wait_on_run(thread_id, run_id)
                logger.info(f"Tool outputs submitted, new run state: {run}")

            logger.info("Waiting for final run completion")
            run = assistant_manager.wait_on_run(thread_id, run_id)
            logger.info(f"Final run completed: {run}")

            logger.info("Getting assistant response")
            messages = await assistant_manager.get_response(thread_id)
            if messages.data:
                assistant_response = messages.data[-1].content[0].text.value
                logger.info(f"Assistant response: {assistant_response}")

                logger.info("Sending Slack response")
                await send_slack_response(say, assistant_response, None, channel, event.get("ts"))
                assistant_manager.pretty_print(messages.data)
            else:
                logger.warning("No messages found in the response")
                await say(text="I'm sorry, but I couldn't generate a response. Please try again.", channel=channel)

        logger.info("Message processing completed successfully")
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}", exc_info=True)
        await say(text="I'm sorry, but I encountered an error while processing your request. Please try again later.", channel=channel)
        
async def handle_tool_call(tool_call, travel_planner):
    function_name = tool_call.function.name
    function_args = json.loads(tool_call.function.arguments)
    
    if function_name == "search_flights":
        result = await travel_planner._search_flights(**function_args)
    elif function_name == "plan_trip":
        result = await travel_planner.plan_trip(function_args["travel_request"])
    else:
        result = f"Unknown function: {function_name}"
    
    return json.dumps(result)

async def send_slack_response(say, assistant_response, tool_responses, channel, thread_ts):
    await say(text=assistant_response, channel=channel, thread_ts=thread_ts)
    if tool_responses:
        await say(text=str(tool_responses), channel=channel, thread_ts=thread_ts)