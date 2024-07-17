import os
import json
import asyncio
from slack_bolt.async_app import AsyncApp
from app.assistant_manager import AssistantManager
from app.dispatcher import Dispatcher
from app.services.travel.travel_planner import TravelPlanner
from utils.logger import logger

def create_slack_bot(travel_planner: TravelPlanner):
    app = AsyncApp(
        token=os.environ.get("SLACK_BOT_TOKEN"),
        signing_secret=os.environ.get("SLACK_SIGNING_SECRET")
    )

    assistant_manager = AssistantManager()
    dispatcher = Dispatcher()

    @app.event("message")
    async def handle_message_events(event, say):
        await process_message_event(event, say, travel_planner, assistant_manager, dispatcher)

    @app.error
    async def global_error_handler(error, body, logger):
        logger.error(f"Error: {error}")
        logger.error(f"Request body: {body}")

    return app

async def process_message_event(event, say, travel_planner, assistant_manager, dispatcher):
    text = event.get("text", "")
    user = event.get("user")
    channel = event.get("channel")

    if not text or not user:
        return

    try:
        dispatch_result = await dispatcher.dispatch(text.lower())
        thread_id = dispatch_result.get('thread_id')
        run_id = dispatch_result.get('run_id')
        function_output = dispatch_result.get('function_output')
        
        if not thread_id or not run_id:
            raise ValueError("Invalid dispatch result")

        if function_output:
            await send_slack_response(say, function_output, None, channel, event.get("ts"))
        else:
            run = assistant_manager.wait_on_run(thread_id, run_id)

            if run.required_action is not None and run.required_action.type == "submit_tool_outputs":
                tool_calls = run.required_action.submit_tool_outputs.tool_calls
                tool_outputs = [
                    {
                        "tool_call_id": tool_call.id,
                        "output": await handle_tool_call(tool_call, travel_planner)
                    }
                    for tool_call in tool_calls
                ]
                run = assistant_manager.wait_on_run(thread_id, run_id)

            run = assistant_manager.wait_on_run(thread_id, run_id)
            messages = await assistant_manager.get_response(thread_id)

            if messages.data:
                assistant_response = messages.data[-1].content[0].text.value
                await send_slack_response(say, assistant_response, None, channel, event.get("ts"))
            else:
                await say(text="I'm sorry, but I couldn't generate a response. Please try again.", channel=channel)

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