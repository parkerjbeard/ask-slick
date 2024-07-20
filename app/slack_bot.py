import os
import json
from slack_bolt.async_app import AsyncApp
from app.assistants.assistant_manager import AssistantManager
from app.assistants.dispatcher import Dispatcher
from app.services.travel.travel_planner import TravelPlanner
from utils.logger import logger

def create_slack_bot(travel_planner: TravelPlanner):
    logger.debug("Creating Slack bot")
    app = AsyncApp(
        token=os.environ.get("SLACK_BOT_TOKEN"),
        signing_secret=os.environ.get("SLACK_SIGNING_SECRET")
    )

    assistant_manager = AssistantManager()
    dispatcher = Dispatcher()

    @app.event("message")
    async def handle_message_events(event, say):
        logger.debug(f"Received message event: {event}")
        await process_message_event(event, say, travel_planner, assistant_manager, dispatcher)

    @app.error
    async def global_error_handler(error, body, logger):
        logger.error(f"Global error: {error}")
        logger.error(f"Request body: {body}")

    logger.debug("Slack bot created successfully")
    return app

async def process_message_event(event, say, travel_planner, assistant_manager, dispatcher):
    text = event.get("text", "")
    user = event.get("user")
    channel = event.get("channel")

    logger.debug(f"Processing message event - Text: {text}, User: {user}, Channel: {channel}")

    if not text or not user:
        logger.warning("Invalid message event: missing text or user")
        return

    try:
        logger.debug("Dispatching message")
        dispatch_result = await dispatcher.dispatch(text.lower())
        logger.debug(f"Dispatch result: {dispatch_result}")
        thread_id = dispatch_result.get('thread_id')
        run_id = dispatch_result.get('run_id')
        function_outputs = dispatch_result.get('function_outputs')
        
        if not thread_id or not run_id:
            logger.error("Invalid dispatch result: missing thread_id or run_id")
            raise ValueError("Invalid dispatch result")

        if function_outputs:
            logger.debug(f"Sending function outputs: {function_outputs}")
            for output in function_outputs:
                if isinstance(output, dict) and 'output' in output:
                    await send_slack_response(say, output['output'], None, channel)
                else:
                    logger.error(f"Unexpected output format: {output}")

        logger.debug(f"Waiting on run - Thread ID: {thread_id}, Run ID: {run_id}")
        run = assistant_manager.wait_on_run(thread_id, run_id)
        logger.debug(f"Run status: {run.status}")

        while run.status == "requires_action":
            logger.debug("Run requires action")
            tool_calls = run.required_action.submit_tool_outputs.tool_calls
            logger.debug(f"Tool calls: {tool_calls}")
            tool_outputs = [
                {
                    "tool_call_id": tool_call.id,
                    "output": await handle_tool_call(tool_call, travel_planner)
                }
                for tool_call in tool_calls
            ]
            logger.debug(f"Submitting tool outputs: {tool_outputs}")
            run = await assistant_manager.submit_tool_outputs(thread_id, run_id, tool_outputs)
            logger.debug(f"Updated run status: {run.status}")

        logger.debug("Getting assistant response")
        messages = await assistant_manager.get_assistant_response(thread_id, run_id)
        logger.debug(f"Received messages: {messages}")

        if messages is None:
            logger.error("No messages received from assistant_manager.get_assistant_response")
            await say(text="I'm sorry, but I couldn't generate a response. Please try again.", channel=channel)
        elif not hasattr(messages, 'data') or not messages.data:
            logger.warning("Messages object has no data attribute or data is empty")
            await say(text="I'm sorry, but I couldn't generate a response. Please try again.", channel=channel)
        else:
            assistant_response = messages.data[-1].content[0].text.value
            logger.debug(f"Assistant response: {assistant_response}")
            await send_slack_response(say, assistant_response, None, channel)

    except Exception as e:
        logger.error(f"Error processing message: {str(e)}", exc_info=True)
        await say(text="I'm sorry, but I encountered an error while processing your request. Please try again later.", channel=channel)
        
async def handle_tool_call(tool_call, travel_planner):
    function_name = tool_call.function.name
    function_args = json.loads(tool_call.function.arguments)
    
    logger.debug(f"Handling tool call - Function: {function_name}, Arguments: {function_args}")
    
    if function_name == "search_flights":
        result = await travel_planner._search_flights(function_args)
    elif function_name == "search_hotels":
        result = await travel_planner._search_hotels(function_args)
    elif function_name == "plan_trip":
        result = await travel_planner.plan_trip(function_args["travel_request"])
    else:
        logger.warning(f"Unknown function: {function_name}")
        result = f"Unknown function: {function_name}"
    
    logger.debug(f"Tool call result: {result}")
    return json.dumps(result)

async def send_slack_response(say, assistant_response, tool_responses, channel):
    logger.debug(f"Sending Slack response - Channel: {channel}, Response: {assistant_response}")
    await say(text=assistant_response, channel=channel)
    if tool_responses:
        logger.debug(f"Sending tool responses: {tool_responses}")
        await say(text=str(tool_responses), channel=channel)