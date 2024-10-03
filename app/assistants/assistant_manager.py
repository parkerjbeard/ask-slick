from app.assistants.assistant_factory import AssistantFactory
from app.config.config_manager import ConfigManager
from typing import Optional, List, Dict, Any
from app.config.settings import settings
from utils.logger import logger
from openai import OpenAI
import time

class AssistantManager:
    def __init__(self, config_manager: ConfigManager):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self._assistant_cache = {}
        self.config_manager = config_manager

    async def list_assistants(self) -> Dict[str, str]:
        response = self.client.beta.assistants.list()
        return {assistant.name: assistant.id for assistant in response.data}

    def retrieve_assistant(self, assistant_id: str) -> Any:
        if assistant_id not in self._assistant_cache:
            self._assistant_cache[assistant_id] = self.client.beta.assistants.retrieve(assistant_id)
        return self._assistant_cache[assistant_id]

    async def create_assistant(self, name: str, instructions: str, tools: List[Dict[str, Any]], model: str) -> Any:
        return self.client.beta.assistants.create(
            name=name,
            instructions=instructions,
            tools=tools,
            model=model
        )

    async def create_or_get_assistant(self, name: str) -> str:
        assistants = await self.list_assistants()
        assistant_id = assistants.get(name)

        if assistant_id:
            return assistant_id

        tools, model = AssistantFactory.get_tools_for_assistant(name)
        instructions = AssistantFactory.get_assistant_instructions(name)

        assistant = await self.create_assistant(
            name=name,
            instructions=instructions,
            tools=tools,
            model=model
        )
        return assistant.id

    async def update_assistant(self, assistant_id: str, name: Optional[str] = None, 
                               description: Optional[str] = None, instructions: Optional[str] = None, 
                               tools: Optional[List[Dict[str, Any]]] = None) -> Any:
        update_fields = {k: v for k, v in locals().items() if k != 'self' and v is not None}
        del update_fields['assistant_id']
        updated_assistant = self.client.beta.assistants.update(assistant_id, **update_fields)
        return updated_assistant

    async def delete_assistant(self, assistant_id: str) -> Any:
        result = self.client.beta.assistants.delete(assistant_id)
        return result

    async def create_thread(self) -> Any:
        thread = self.client.beta.threads.create()
        return thread

    async def create_message(self, thread_id: str, role: str, content: str) -> Any:
        message = self.client.beta.threads.messages.create(
            thread_id=thread_id,
            role=role,
            content=content
        )
        return message

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
        return response

    async def create_run(self, thread_id: str, assistant_id: str, instructions: Optional[str] = None) -> Any:
        assistant = self.retrieve_assistant(assistant_id)
        run_params = {
            "thread_id": thread_id,
            "assistant_id": assistant_id,
            "tools": assistant.tools,  # Include the assistant's tools in each run
        }
        if instructions:
            run_params["instructions"] = instructions
        run = self.client.beta.threads.runs.create(**run_params)
        return run

    def wait_on_run(self, thread_id: str, run_id: str) -> Any:
        while True:
            try:
                run = self.client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)
                if run.status in ["completed", "requires_action"]:
                    return run
                elif run.status in ["failed", "cancelled", "expired"]:
                    raise Exception(f"Run failed with status: {run.status}")
                time.sleep(0.5)
            except Exception as e:
                raise

    async def submit_tool_outputs(self, thread_id: str, run_id: str, tool_outputs: List[Dict[str, Any]]) -> Any:
        result = self.client.beta.threads.runs.submit_tool_outputs_and_poll(
            thread_id=thread_id,
            run_id=run_id,
            tool_outputs=tool_outputs
        )
        return result

    async def submit_message(self, assistant_id: str, thread_id: str, user_message: str) -> Any:
        await self.create_message(thread_id, "user", user_message)
        run = await self.create_run(thread_id, assistant_id)
        return run
    
    async def get_assistant_response(self, thread_id: str, run_id: str) -> Optional[str]:
        messages = await self.list_messages(thread_id)
        assistant_messages = []
        for message in messages.data:
            if message.role == "assistant" and message.run_id == run_id:
                if message.content and len(message.content) > 0:
                    assistant_messages.append(message.content[0].text.value)
        if not assistant_messages:
            logger.warning(f"No assistant response found for run_id: {run_id}")
            return None
        response = "\n".join(assistant_messages)
        return response

    async def handle_tool_call(self, run: Any) -> Any:
        tool_call = run.required_action.submit_tool_outputs.tool_calls[0]
        return tool_call