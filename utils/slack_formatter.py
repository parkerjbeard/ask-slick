import json
import re
from typing import Dict, Any, List
from app.openai_helper import OpenAIClient
from utils.logger import logger

class SlackMessageFormatter:
    def __init__(self):
        self.openai_client = OpenAIClient()
        self.emoji_pattern = re.compile("["
            u"\U0001F600-\U0001F64F"  # emoticons
            u"\U0001F300-\U0001F5FF"  # symbols & pictographs
            u"\U0001F680-\U0001F6FF"  # transport & map symbols
            u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
            u"\U00002702-\U000027B0"
            u"\U000024C2-\U0001F251"
            "]+", flags=re.UNICODE)

    def remove_emojis(self, text: str) -> str:

        return self.emoji_pattern.sub(r'', text)

    async def format_message(self, message: str, channel: str) -> Dict[str, Any]:
        prompt = f"""
        Format the following message for Slack using block kit. The output should be a valid JSON object that can be directly used with the Slack API. Use appropriate block types, including sections, dividers, and context blocks where necessary. Ensure the formatting enhances readability and engagement. Do not use any emojis in the formatting.

        Message to format:
        {message}

        The JSON structure should follow this format:
        {{
            "channel": "{channel}",
            "text": "A plain text summary of the message",
            "blocks": [
                // Formatted blocks here
            ]
        }}

        Rules:
        1. Include a "text" field with a plain text summary of the message.
        2. Use "type": "section" for main content.
        3. Use "type": "divider" to separate major sections.
        4. Use "type": "context" for additional information or metadata.
        5. Properly escape any special characters in the text.
        6. Use Slack's mrkdwn format for text styling (e.g., *bold*, ~strikethrough~). Do not use italics.
        7. If there are clear lists or steps, format them as numbered or bulleted lists.
        8. For any links, use the format <URL|text> in mrkdwn.
        9. Keep each text block under 3000 characters to comply with Slack's limits.
        10. Do not use any emojis in the formatting.

        Respond only with the formatted JSON, without any additional explanation.
        """

        try:
            response = self.openai_client.generate_text(prompt)
            # Attempt to find and extract the JSON object from the response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start != -1 and json_end != -1:
                json_str = response[json_start:json_end]
                formatted_message = json.loads(json_str)
            else:
                raise ValueError("No valid JSON object found in the response")
            
            # Remove emojis from all text fields in the formatted message
            formatted_message = self.remove_emojis_from_dict(formatted_message)
            
            logger.debug(f"Formatted Slack message: {formatted_message}")
            return formatted_message
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Error processing OpenAI response: {e}")
            return self._fallback_format(message, channel)
        except Exception as e:
            logger.error(f"Error formatting Slack message: {e}")
            return self._fallback_format(message, channel)

    def remove_emojis_from_dict(self, d: Dict[str, Any]) -> Dict[str, Any]:
        for key, value in d.items():
            if isinstance(value, str):
                d[key] = self.remove_emojis(value)
            elif isinstance(value, list):
                d[key] = [self.remove_emojis_from_dict(item) if isinstance(item, dict) else self.remove_emojis(item) if isinstance(item, str) else item for item in value]
            elif isinstance(value, dict):
                d[key] = self.remove_emojis_from_dict(value)
        return d

    def _fallback_format(self, message: str, channel: str) -> Dict[str, Any]:
        logger.warning("Using fallback message formatting")
        return {
            "channel": channel,
            "text": self.remove_emojis(message[:100] + "..."),  # Truncated message as fallback text
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": self.remove_emojis(message)
                    }
                }
            ]
        }

    def split_message(self, formatted_message: Dict[str, Any], max_blocks: int = 50) -> List[Dict[str, Any]]:
        blocks = formatted_message.get("blocks", [])
        messages = []
        
        for i in range(0, len(blocks), max_blocks):
            chunk = blocks[i:i + max_blocks]
            messages.append({
                "channel": formatted_message["channel"],
                "text": formatted_message.get("text", "Message continuation..."),
                "blocks": chunk
            })
        
        return messages