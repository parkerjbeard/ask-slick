from typing import Optional, List, Dict, Any
import os
import time
from openai import OpenAI
from utils.logger import logger

class AssistantManager:
    """A class to manage OpenAI assistants and threads."""

    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    # Assistant management
    async def list_assistants(self) -> Dict[str, str]:
        response = self.client.beta.assistants.list()
        return {assistant.name: assistant.id for assistant in response.data}

    async def retrieve_assistant(self, assistant_id: str) -> Any:
        return self.client.beta.assistants.retrieve(assistant_id)

    async def create_assistant(self, name: str, instructions: str, tools: List[Dict[str, Any]], model: str) -> Any:
        return self.client.beta.assistants.create(
            name=name,
            instructions=instructions,
            tools=tools,
            model=model
        )

    async def update_assistant(self, assistant_id: str, name: Optional[str] = None, 
                               description: Optional[str] = None, instructions: Optional[str] = None, 
                               tools: Optional[List[Dict[str, Any]]] = None) -> Any:
        update_fields = {k: v for k, v in locals().items() if k != 'self' and v is not None}
        del update_fields['assistant_id']
        return self.client.beta.assistants.update(assistant_id, **update_fields)

    async def delete_assistant(self, assistant_id: str) -> Any:
        return self.client.beta.assistants.delete(assistant_id)

    async def get_assistant_id_by_name(self, name: str) -> Optional[str]:
        assistants = await self.list_assistants()
        return assistants.get(name)

    # Thread and message management
    async def create_thread(self) -> Any:
        return self.client.beta.threads.create()

    async def create_message(self, thread_id: str, role: str, content: str) -> Any:
        return self.client.beta.threads.messages.create(
            thread_id=thread_id,
            role=role,
            content=content
        )
    
    async def list_runs(self, thread_id: str) -> Any:
        return self.client.beta.threads.runs.list(thread_id=thread_id)

    async def list_messages(self, thread_id: str, order: str = "asc", after: Optional[str] = None, limit: Optional[int] = None) -> Any:
        params = {
            "thread_id": thread_id,
            "order": order,
        }
        if after:
            params["after"] = after
        if limit:
            params["limit"] = limit
        response = self.client.beta.threads.messages.list(**params)
        logger.debug(f"List messages response: {response}")
        return response
    
    # Run management
    async def create_run(self, thread_id: str, assistant_id: str, instructions: Optional[str] = None) -> Any:
        run_params = {
            "thread_id": thread_id,
            "assistant_id": assistant_id,
        }
        if instructions:
            run_params["instructions"] = instructions
        return self.client.beta.threads.runs.create(**run_params)

    def wait_on_run(self, thread_id: str, run_id: str) -> Any:
        while True:
            try:
                run = self.client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)
                if run.status in ["completed", "requires_action"]:
                    return run
                elif run.status in ["failed", "cancelled", "expired"]:
                    logger.error(f"Run failed with status: {run.status}")
                    raise Exception(f"Run failed with status: {run.status}")
                time.sleep(0.5)
            except Exception as e:
                logger.error(f"Error retrieving run status: {str(e)}")
                raise

    async def submit_tool_outputs(self, thread_id: str, run_id: str, tool_outputs: List[Dict[str, Any]]) -> Any:
        return self.client.beta.threads.runs.submit_tool_outputs(
            thread_id=thread_id,
            run_id=run_id,
            tool_outputs=tool_outputs
        )

    # Conversation flow
    async def submit_message(self, assistant_id: str, thread_id: str, user_message: str) -> Any:
        await self.create_message(thread_id, "user", user_message)
        return await self.create_run(thread_id, assistant_id)

    async def get_assistant_response(self, thread_id: str, run_id: str) -> Optional[str]:
        messages = await self.list_messages(thread_id)
        logger.debug(f"Messages: {messages}")
        for message in messages.data:
            logger.debug(f"Checking message - Role: {message.role}, Run ID: {message.run_id}")
            if message.role == "assistant" and message.run_id == run_id:
                if message.content and len(message.content) > 0:
                    return message.content[0].text.value
        logger.warning(f"No assistant response found for run_id: {run_id}")
        return None

    async def create_thread_and_run(self, assistant_id: str, user_input: str) -> tuple:
        thread = await self.create_thread()
        run = await self.submit_message(assistant_id, thread.id, user_input)
        return thread, run

    async def handle_tool_call(self, run: Any) -> Any:
        return run.required_action.submit_tool_outputs.tool_calls[0]