from app.google_client import google_auth_manager, initialize_google_auth
from app.openai_helper import OpenAIClient
from utils.logger import logger
from typing import Dict, Any
import boto3
from datetime import datetime, timezone
import asyncio

class UserSetup:
    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb')
        self.user_preferences_table = self.dynamodb.Table('user_preferences')
        self.user_manifests_table = self.dynamodb.Table('user_manifests')
        self.google_auth_manager = google_auth_manager
        self.openai_client = OpenAIClient()

    async def start_setup(self, user_id: str, say: Any) -> Dict[str, Any]:
        """
        Initiates the user setup process
        """
        logger.info(f"Starting user setup for user_id: {user_id}")

        # Clear existing scopes and initialize with defaults
        self.google_auth_manager.scopes.clear()
        self.google_auth_manager.initialize_default_scopes()

        # Check if user already exists
        if self._check_existing_user(user_id):
            logger.info(f"User {user_id} already exists")
            return {"status": "existing_user"}

        # Create flow with all scopes
        self.flow = self.google_auth_manager.create_auth_flow()

        # Generate auth URL
        auth_url = self.google_auth_manager.get_auth_url(user_id)

        logger.info("Google auth URL generated")

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

    async def complete_google_auth(self, user_id: str, auth_code: str, state_token: str) -> Dict[str, Any]:
        """
        Handles Google authentication completion
        """
        logger.info(f"Completing Google auth for user_id: {user_id}")

        try:
            # Verify state token matches user
            verified_user_id = await self.google_auth_manager.verify_state_token(state_token)
            if not verified_user_id or verified_user_id != user_id:
                logger.error(f"State token verification failed for user {user_id}")
                return {"status": "error", "message": "Invalid state token"}

            # Exchange the authorization code for credentials
            credentials = await self.google_auth_manager.exchange_code(auth_code, state_token)
            logger.info("Authorization code exchanged successfully")

            # Debug: token presence
            logger.debug(f"Credentials obtained - Token: {bool(credentials.token)}, Refresh Token: {bool(credentials.refresh_token)}")

            # Save credentials
            save_result = self.google_auth_manager.save_credentials(user_id, credentials)
            if not save_result:
                logger.error("Failed to save Google credentials")
                return {"status": "error", "message": "Failed to save credentials"}

            # Verify saved credentials
            saved_creds = await self.google_auth_manager.get_credentials(user_id)
            if not saved_creds:
                logger.error("Failed to verify saved credentials")
                return {"status": "error", "message": "Failed to verify credentials"}

            logger.info("Google authentication completed successfully")

            return {
                "status": "google_auth_completed",
                "next_step": "timezone_setup",
                "message": "Google authentication successful! Now, let's set up your timezone."
            }

        except Exception as e:
            logger.error(f"Google authentication error for user {user_id}: {repr(e)}")
            return {
                "status": "error", 
                "message": "There was an unexpected error during Google authentication. Please try again."
            }

    async def complete_timezone_setup(self, user_id: str, timezone_str: str, say: Any) -> Dict[str, Any]:
        """
        Completes timezone setup for the user
        """
        logger.info(f"Completing timezone setup for user_id: {user_id}")

        # Verify that Google auth is completed
        credentials = await self.google_auth_manager.get_credentials(user_id)
        if not credentials:
            await say(text="Please complete Google authentication first.")
            return {"status": "error", "message": "Google authentication required"}

        try:
            # Validate timezone. If needed, integrate a full list of valid tz strings or pytz.
            if timezone_str not in datetime.tzinfo.__subclasses__():
                await say(text="Invalid timezone. Please choose a standard timezone (e.g., 'America/New_York').")
                return {"status": "invalid_timezone"}

            # Save user preferences
            self._save_user_preferences(user_id, {
                "timezone": timezone_str,
                "setup_completed": True,
                "setup_date": datetime.now(timezone.utc).isoformat()
            })

            await say(blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            f"Perfect! I've set your timezone to {timezone_str}. You're all set to start using the assistant! "
                            "Here are some things you can ask me to do:\n\n"
                            "• Schedule meetings\n• Check your calendar\n• Send emails\n• Book travel"
                        )
                    }
                }
            ])

            logger.info(f"Timezone setup completed for user_id: {user_id}")

            return {
                "status": "setup_completed",
                "timezone": timezone_str
            }

        except Exception as e:
            logger.error(f"Timezone setup error for user {user_id}: {repr(e)}")
            await say(text="❌ There was an error setting up your timezone. Please try again.")
            return {"status": "error", "message": "Timezone setup failed"}

    def _check_existing_user(self, user_id: str) -> bool:
        """
        Checks if user already exists AND if they've completed setup
        """
        logger.info(f"Checking existing user in DynamoDB for user_id: {user_id}")
        try:
            response = self.user_preferences_table.get_item(Key={'slack_user_id': user_id})
            if 'Item' in response:
                setup_completed = response['Item'].get('setup_completed', False)
                logger.debug(f"User {user_id} setup status: {setup_completed}")
                return setup_completed

            logger.info(f"No existing record found for user_id: {user_id}")
            return False

        except Exception as e:
            logger.error(f"Error checking existing user {user_id}: {repr(e)}")
            return False

    def _save_user_preferences(self, user_id: str, preferences: Dict[str, Any]) -> None:
        """
        Saves user preferences to DynamoDB
        """
        try:
            item = {
                'slack_user_id': user_id,  # Primary key
                **preferences,
                'updated_at': datetime.now(timezone.utc).isoformat()
            }
            self.user_preferences_table.put_item(Item=item)
            logger.info(f"User preferences saved for user_id: {user_id}")
        except Exception as e:
            logger.error(f"Error saving preferences for user {user_id}: {repr(e)}")
            raise

    async def check_user_setup(self, user_id: str) -> bool:
        """
        Check if user has completed setup
        """
        try:
            response = self.user_manifests_table.get_item(
                Key={'slack_user_id': user_id}
            )
            if 'Item' in response:
                return response['Item'].get('setup_completed', False)
            return False
        except Exception as e:
            logger.error(f"Error checking user setup: {str(e)}")
            return False

    async def wait_for_setup_completion(self, user_id: str, timeout: int = 300) -> bool:
        """
        Waits for user setup to complete with a timeout
        Returns True if setup is completed, False if timeout occurs
        """
        logger.info(f"Waiting for setup completion for user_id: {user_id} with timeout: {timeout}s")
        start_time = datetime.now(timezone.utc)

        while (datetime.now(timezone.utc) - start_time).total_seconds() < timeout:
            if self._check_existing_user(user_id):
                logger.info(f"Setup completed for user_id: {user_id}")
                return True
            await asyncio.sleep(1)  # Wait 1 second before checking again

        logger.warning(f"Setup timeout reached for user_id: {user_id}")
        return False

    def register_new_user(self, user_id: str) -> bool:
        """
        Registers a new user in DynamoDB with initial preferences
        """
        logger.info(f"Registering new user with user_id: {user_id}")

        try:
            initial_preferences = {
                'slack_user_id': user_id,
                'setup_completed': False,
                'registration_date': datetime.now(timezone.utc).isoformat(),
                'updated_at': datetime.now(timezone.utc).isoformat()
            }

            self._save_user_preferences(user_id, initial_preferences)
            logger.info(f"Successfully registered new user: {user_id}")
            return True

        except Exception as e:
            logger.error(f"Error registering new user {user_id}: {repr(e)}")
            return False
