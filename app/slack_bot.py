from app.assistants.assistant_manager import AssistantManager
from utils.slack_formatter import SlackMessageFormatter
from app.config.config_manager import ConfigManager
from app.assistants.dispatcher import Dispatcher
from app.openai_helper import OpenAIClient
from slack_bolt.async_app import AsyncApp
from app.config.settings import settings
from utils.logger import logger
import traceback
from slack_bolt.adapter.aws_lambda import SlackRequestHandler
from app.google_client import GoogleAuthManager
from app.user_setup import UserSetup
from slack_bolt.adapter.aws_lambda.handler import SlackRequestHandler
from slack_bolt.adapter.aws_lambda.lazy_listener_runner import LambdaLazyListenerRunner
from slack_bolt.adapter.aws_lambda.handler import to_bolt_request, to_aws_response, not_found
from slack_bolt.logger import get_bolt_app_logger
from slack_bolt.async_app import AsyncApp

# Add this at the module level
_slack_app = None

class AsyncSlackRequestHandler(SlackRequestHandler):
    def __init__(self, app: AsyncApp):
        # Initialize the base handler
        self.app = app
        self.dispatcher = Dispatcher()
        self.logger = get_bolt_app_logger(app.name, AsyncSlackRequestHandler, app.logger)
        # Set the lazy listener runner on the app's listener_runner, not on self
        if getattr(self.app, "listener_runner", None):
            self.app.listener_runner.lazy_listener_runner = LambdaLazyListenerRunner(self.logger)
        if self.app.oauth_flow is not None:
            self.app.oauth_flow.settings.redirect_uri_page_renderer.install_path = "?"

    async def handle(self, event, context):
        self.logger.debug(f"Incoming event: {event}, context: {context}")

        method = event.get("requestContext", {}).get("http", {}).get("method")
        if method is None:
            # Possibly old API Gateway format
            method = event.get("requestContext", {}).get("httpMethod")

        if method is None:
            return not_found()
        if method == "POST":
            bolt_req = to_bolt_request(event)
            bolt_req.context["aws_lambda_function_name"] = context.function_name
            bolt_req.context["aws_lambda_invoked_function_arn"] = context.invoked_function_arn
            bolt_req.context["lambda_request"] = event
            
            # Handle message events directly
            if bolt_req.body.get("event", {}).get("type") == "message":
                event_data = bolt_req.body.get("event", {})
                
                # Skip bot messages to prevent infinite loops
                if event_data.get("bot_id") or event_data.get("bot_profile"):
                    return {
                        "statusCode": 200,
                        "body": '{"ok": true}'
                    }
                
                user_id = event_data.get("user")
                channel = event_data.get("channel")
                
                if user_id and channel:
                    normalized_user_id = f"slack_{user_id}"
                    
                    async def say(text, **kwargs):
                        kwargs['channel'] = channel
                        return await self.app.client.chat_postMessage(text=text, **kwargs)
                    
                    await process_message_event(
                        event=event_data,
                        say=say,
                        dispatcher=self.dispatcher,
                        normalized_user_id=normalized_user_id
                    )
                    return {
                        "statusCode": 200,
                        "body": '{"ok": true}'
                    }
            
            # For other events, use the app's middleware
            try:
                bolt_resp = await self.app.middleware(bolt_req)
                aws_response = to_aws_response(bolt_resp)
                return aws_response
            except Exception as e:
                self.logger.error(f"Error processing request: {e}")
                return {
                    "statusCode": 500,
                    "body": '{"ok": false, "error": "Internal server error"}'
                }

        return not_found()

def create_slack_bot(config_manager: ConfigManager):
    global _slack_app
    if _slack_app is not None:
        logger.debug("Returning existing Slack bot instance")
        return _slack_app

    logger.debug("Creating new Slack bot instance")
    _slack_app = AsyncApp(
        token=settings.SLACK_BOT_TOKEN,
        signing_secret=settings.SLACK_SIGNING_SECRET,
        process_before_response=True,
        installation_store=None
    )

    assistant_manager = AssistantManager(config_manager)
    dispatcher = Dispatcher()

    @_slack_app.event("message")
    async def handle_message_events(event, say):
        logger.debug(f"Received message event: {event}")
        # Extract user ID from the event and normalize it
        normalized_user_id = event.get('user')
        await process_message_event(event, say, dispatcher, normalized_user_id)

    @_slack_app.error
    async def global_error_handler(error, body, logger):
        logger.error(f"Global error: {error}")
        logger.error(f"Request body: {body}")

    logger.debug("Slack bot created successfully")
    return _slack_app

async def process_message_event(event, say, dispatcher, normalized_user_id):
    # Add check for bot messages
    if 'bot_id' in event:
        logger.debug("Ignoring bot message")
        return
        
    logger.info(f"Processing message event for user {normalized_user_id}")
    logger.info(f"Full event data: {event}")
    
    text = event.get("text", "")
    channel = event.get("channel")
    
    logger.info(f"Message text: '{text}' in channel: {channel}")

    try:
        # Check user setup status first
        user_setup = UserSetup()
        
        # If user hasn't completed setup, handle new-user flow
        setup_status = user_setup._check_existing_user(normalized_user_id)
        if not setup_status:
            logger.info(f"New user detected: {normalized_user_id}")
            registration_success = user_setup.register_new_user(normalized_user_id)
            if not registration_success:
                logger.error(f"Failed to register new user: {normalized_user_id}")
                await say(text="I'm sorry, but I encountered an error while setting up your account. Please try again later.", channel=channel)
                return
            
            logger.info(f"Starting setup process for new user: {normalized_user_id}")
            await user_setup.start_setup(normalized_user_id, say)
            return

        # If user is all set up, continue with the full assistant
        dispatcher.set_user_context(normalized_user_id)
        
        # Check Google auth status (get_credentials is now synchronous)
        google_auth_manager = GoogleAuthManager()
        credentials = google_auth_manager.get_credentials(normalized_user_id)

        if not credentials:
            auth_url = google_auth_manager.get_auth_url(normalized_user_id)
            await say(
                blocks=[
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "Before I can help you, I need access to your Google account. Click the button below to authenticate."
                        }
                    },
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "text": "Authenticate with Google"
                                },
                                "url": auth_url,
                                "action_id": "google_auth"
                            }
                        ]
                    }
                ],
                channel=channel
            )
            return

        # Now that we have credentials, generate a quick response
        openai_client = OpenAIClient()
        short_response = openai_client.generate_short_response(text)
        await say(text=short_response, channel=channel)

        logger.debug("Dispatching message")
        dispatch_result = await dispatcher.dispatch(text.lower(), normalized_user_id)
        logger.debug(f"Dispatch result: {dispatch_result}")
        
        if 'error' in dispatch_result:
            logger.error(f"Error in dispatch result: {dispatch_result['error']}")
            await say(text=f"I'm sorry, but I encountered an error: {dispatch_result['error']}", channel=channel)
            return

        thread_id = dispatch_result.get('thread_id')
        run_id = dispatch_result.get('run_id')
        function_outputs = dispatch_result.get('function_outputs')
        assistant_response = dispatch_result.get('assistant_response')
        
        logger.debug(f"Thread ID: {thread_id}, Run ID: {run_id}")
        logger.debug(f"Function outputs: {function_outputs}")
        logger.debug(f"Assistant response: {assistant_response}")

        if not thread_id or not run_id:
            logger.error("Invalid dispatch result: missing thread_id or run_id")
            await say(text="I'm sorry, but I encountered an error while processing your request. Please try again later.", channel=channel)
            return

        if function_outputs:
            logger.debug(f"Sending function outputs: {function_outputs}")
            for output in function_outputs:
                if isinstance(output, dict) and 'output' in output:
                    logger.debug(f"Sending function output: {output['output']}")
                    await send_slack_response(say, output['output'], None, channel)
                else:
                    logger.error(f"Unexpected output format: {output}")

        if assistant_response:
            logger.debug(f"Sending assistant response: {assistant_response}")
            await send_slack_response(say, assistant_response, None, channel)
        else:
            logger.warning("No assistant response received")
            await say(text="I'm sorry, but I couldn't generate a response. Please try again.", channel=channel)

    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        await say(text=f"I'm sorry, but I encountered an error while processing your request: {str(e)}\nPlease try again later.", channel=channel)

async def send_slack_response(say, assistant_response, tool_responses, channel):
    logger.debug(f"[SLACK] Attempting to send message to channel: {channel}")
    logger.debug(f"[SLACK] Bot token prefix: {settings.SLACK_BOT_TOKEN[:10] if settings.SLACK_BOT_TOKEN else 'None'}")
    
    slack_formatter = SlackMessageFormatter()
    
    try:
        formatted_message = await slack_formatter.format_message(assistant_response, channel)
        split_messages = slack_formatter.split_message(formatted_message)
        
        for message in split_messages:
            logger.debug(f"[SLACK] Sending formatted message: {message}")
            await say(**message)
    except Exception as e:
        logger.error(f"[SLACK] Error sending message: {str(e)}")
        logger.error(f"[SLACK] Full error context: {traceback.format_exc()}")
        # Fallback to plain text
        await say(text=assistant_response, channel=channel)
    
    if tool_responses:
        logger.debug(f"Sending tool responses: {tool_responses}")
        try:
            formatted_tool_response = await slack_formatter.format_message(str(tool_responses), channel)
            split_tool_messages = slack_formatter.split_message(formatted_tool_response)
            
            for message in split_tool_messages:
                await say(**message)
        except Exception as e:
            logger.error(f"Error formatting and sending tool response: {e}")
            # Fallback to plain text
            await say(text=str(tool_responses), channel=channel)
