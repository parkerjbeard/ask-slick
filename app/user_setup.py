from app.google_client import google_auth_manager, initialize_google_auth
from app.openai_helper import OpenAIClient
from utils.logger import logger
from typing import Dict, Any
import pytz
import boto3
from datetime import datetime, UTC
import asyncio
import traceback

class UserSetup:
    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb')
        self.user_preferences_table = self.dynamodb.Table('user_preferences')
        self.google_auth_manager = google_auth_manager
        self.openai_client = OpenAIClient()

    async def start_setup(self, user_id: str, say: Any) -> Dict[str, Any]:
        """
        Initiates the user setup process
        """
        logger.info(f"Starting user setup for {user_id}")
        
        # Initialize Google auth scopes before starting setup
        initialize_google_auth()
        
        # Check if user already exists
        if self._check_existing_user(user_id):
            logger.info(f"User {user_id} already exists")
            return {"status": "existing_user"}

        # Create flow and store it for later use
        self.flow = self.google_auth_manager.create_auth_flow()
        
        # Add logging before generating auth URL
        logger.info(f"Flow redirect URI: {self.flow.redirect_uri}")
        logger.info(f"Flow scopes: {self.flow.oauth2session.scope}")
        
        auth_url, _ = self.flow.authorization_url(access_type='offline', include_granted_scopes='true')
        
        # Log the generated URL
        logger.info(f"Generated auth URL: {auth_url}")

        # Start Google authentication
        await say(
            text="First, I'll need access to your Google account to help with calendar and email tasks.",
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "Hello! First, I'll need access to your Google account to help with calendar and email tasks."
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
            ]
        )

        return {
            "status": "auth_initiated",
            "next_step": "google_auth"
        }

    async def complete_google_auth(self, user_id: str, auth_code: str, say: Any) -> Dict[str, Any]:
        """
        Handles Google authentication completion
        """
        try:
            # Use the same flow instance from start_setup
            if not hasattr(self, 'flow'):
                # If flow doesn't exist (e.g., after a restart), create a new one
                self.flow = self.google_auth_manager.create_auth_flow()
                
            # Fetch token using the same flow instance
            self.flow.fetch_token(code=auth_code)
            credentials = self.flow.credentials

            # Save credentials
            if not self.google_auth_manager.save_credentials(user_id, credentials):
                raise Exception("Failed to save Google credentials")

            await say(blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "✅ Google authentication successful! Now, let's set up your timezone."
                    }
                }
            ])

            return {
                "status": "google_auth_completed",
                "next_step": "timezone_setup"
            }

        except Exception as e:
            logger.error(f"Error in Google authentication: {str(e)}")
            await say(text="❌ There was an error authenticating with Google. Please try again.")
            return {"status": "error", "message": str(e)}

    async def complete_timezone_setup(self, user_id: str, timezone_str: str, say: Any) -> Dict[str, Any]:
        # First verify that Google auth is completed
        credentials = self.google_auth_manager.get_credentials(user_id)
        if not credentials:
            await say(text="Please complete Google authentication first.")
            return {
                "status": "error",
                "message": "Google authentication required"
            }

        try:
            # Validate timezone
            if timezone_str not in pytz.all_timezones:
                await say(text="That timezone isn't valid. Please choose from a standard timezone (e.g., 'America/New_York', 'Europe/London')")
                return {"status": "invalid_timezone"}

            # Save user preferences
            self._save_user_preferences(user_id, {
                "timezone": timezone_str,
                "setup_completed": True,
                "setup_date": datetime.now(UTC).isoformat()
            })

            await say(blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"Perfect! I've set your timezone to {timezone_str}. You're all set to start using the assistant! Here are some things you can ask me to do:\n\n• Schedule meetings\n• Check your calendar\n• Send emails\n• Book travel"
                    }
                }
            ])

            return {
                "status": "setup_completed",
                "timezone": timezone_str
            }

        except Exception as e:
            logger.error(f"Error in timezone setup: {str(e)}")
            await say(text="I encountered an error setting up your timezone. Please try again.")
            return {"status": "error", "message": str(e)}

    def _check_existing_user(self, user_id: str) -> bool:
        """
        Checks if user already exists and has completed setup
        """
        try:
            logger.info(f"Checking existing user in DynamoDB - user_id: {user_id}")
            logger.debug(f"DynamoDB table name: {self.user_preferences_table.name}")
            
            # Use slack_user_id as the key
            response = self.user_preferences_table.get_item(Key={'slack_user_id': user_id})
            #logger.debug(f"DynamoDB response: {response}")
            
            if 'Item' in response:
                setup_completed = response['Item'].get('setup_completed', False)
                logger.info(f"User {user_id} setup status: {setup_completed}")
                return setup_completed
            
            logger.info(f"No existing record found for user {user_id}")
            return False
        except Exception as e:
            logger.error(f"Error checking existing user: {str(e)}")
            logger.error(f"Full exception details: {traceback.format_exc()}")
            return False

    def _save_user_preferences(self, user_id: str, preferences: Dict[str, Any]) -> None:
        """
        Saves user preferences to DynamoDB
        """
        try:
            # Ensure slack_user_id is set correctly
            item = {
                'slack_user_id': user_id,  # Primary key must be slack_user_id
                **preferences,
                'updated_at': datetime.now(UTC).isoformat()
            }
            logger.debug(f"Saving item to DynamoDB: {item}")
            self.user_preferences_table.put_item(Item=item)
        except Exception as e:
            logger.error(f"Error saving user preferences: {str(e)}")
            raise

    async def check_user_setup(self, user_id: str) -> Dict[str, Any]:
        """
        Checks the setup status for a user
        """
        is_setup = self._check_existing_user(user_id)
        return {
            "setup_completed": is_setup,
            "user_id": user_id
        }

    async def wait_for_setup_completion(self, user_id: str, timeout: int = 300) -> bool:
        """
        Waits for user setup to complete with a timeout
        Returns True if setup is completed, False if timeout occurs
        """
        start_time = datetime.now(UTC)
        while (datetime.now(UTC) - start_time).total_seconds() < timeout:
            if self._check_existing_user(user_id):
                return True
            await asyncio.sleep(1)  # Wait 1 second before checking again
        return False

    def register_new_user(self, user_id: str) -> bool:
        """
        Registers a new user in DynamoDB with initial preferences
        """
        try:
            logger.info(f"Registering new user in DynamoDB - user_id: {user_id}")
            
            # Initial user preferences with correct key name
            initial_preferences = {
                'slack_user_id': user_id,  # Changed from 'user_id' to 'slack_user_id'
                'setup_completed': False,
                'registration_date': datetime.now(UTC).isoformat(),
                'updated_at': datetime.now(UTC).isoformat()
            }
            
            logger.debug(f"Initial preferences: {initial_preferences}")
            self._save_user_preferences(user_id, initial_preferences)
            logger.info(f"Successfully registered new user: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error registering new user: {str(e)}")
            logger.error(f"Full exception details: {traceback.format_exc()}")
            return False