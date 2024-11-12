import boto3
from datetime import datetime, timezone
from utils.logger import logger
from botocore.exceptions import ClientError

class ThreadStore:
    def __init__(self, table_name="user_threads"):
        self.dynamodb = boto3.resource('dynamodb')
        self.table = self.dynamodb.Table(table_name)

    async def get_thread(self, user_id: str) -> str | None:
        try:
            response = self.table.get_item(
                Key={
                    'slack_user_id': user_id
                }
            )
            return response.get('Item', {}).get('thread_id')
        except ClientError as e:
            logger.error(f"Error getting thread for user {user_id}: {e}")
            return None

    async def store_thread(self, user_id: str, thread_id: str) -> bool:
        try:
            self.table.put_item(
                Item={
                    'slack_user_id': user_id,
                    'thread_id': thread_id,
                    'created_at': datetime.now(timezone.utc).isoformat(),
                    'last_used': datetime.now(timezone.utc).isoformat()
                }
            )
            return True
        except ClientError as e:
            logger.error(f"Error storing thread for user {user_id}: {e}")
            return False

    async def update_last_used(self, user_id: str) -> bool:
        try:
            self.table.update_item(
                Key={'slack_user_id': user_id},
                UpdateExpression='SET last_used = :time',
                ExpressionAttributeValues={
                    ':time': datetime.now(timezone.utc).isoformat()
                }
            )
            return True
        except ClientError as e:
            logger.error(f"Error updating last_used for user {user_id}: {e}")
            return False

    async def delete_thread(self, user_id: str) -> bool:
        try:
            self.table.delete_item(
                Key={'slack_user_id': user_id}
            )
            return True
        except ClientError as e:
            logger.error(f"Error deleting thread for user {user_id}: {e}")
            return False