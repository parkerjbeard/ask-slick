from typing import Optional
import os
import json  # Add this import
from openai import OpenAI

class AssistantManager:
    """
    A class to manage assistants.
    """
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    async def list_assistants(self):
        response = self.client.beta.assistants.list()
        return {assistant.name: assistant.id for assistant in response.data}

    async def retrieve_assistant(self, assistant_id: str):
        return self.client.beta.assistants.retrieve(assistant_id)

    async def create_assistant(self, name: str, instructions: str, tools: list, model: str):
        return self.client.beta.assistants.create(
            name=name,
            instructions=instructions,
            tools=tools,
            model=model
        )

    async def update_assistant(self, assistant_id: str, name: Optional[str] = None, description: Optional[str] = None,
                               instructions: Optional[str] = None, tools: Optional[list] = None):
        update_fields = {}
        if name is not None:
            update_fields['name'] = name
        if description is not None:
            update_fields['description'] = description
        if instructions is not None:
            update_fields['instructions'] = instructions
        if tools is not None:
            update_fields['tools'] = tools
        return self.client.beta.assistants.update(assistant_id, **update_fields)

    async def delete_assistant(self, assistant_id: str):
        return self.client.beta.assistants.delete(assistant_id)

    async def create_thread(self):
        return self.client.beta.threads.create()

    async def create_message(self, thread_id: str, role: str, content: str):
        return self.client.beta.threads.messages.create(
            thread_id=thread_id,
            role=role,
            content=content
        )

    async def create_run(self, thread_id: str, assistant_id: str):
        return await self.client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=assistant_id
        )

    async def wait_on_run(self, thread_id: str, run_id: str):
        import time
        run = self.client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)
        while run.status in ["queued", "in_progress"]:
            time.sleep(0.5)
            run = self.client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)
        return run

    async def list_messages(self, thread_id: str, order="asc", after=None):
        return self.client.beta.threads.messages.list(thread_id=thread_id, order=order, after=after)

    async def get_assistant_id_by_name(self, name: str):
        """
        Get the ID of an assistant by its name.

        Args:
            name (str): The name of the assistant.

        Returns:
            str: The ID of the assistant if found, otherwise None.
        """
        assistants = await self.list_assistants()
        return assistants.get(name)

    async def get_assistant_response(self, thread_id: str, run_id: str):
        """
        Get the assistant's response from a thread after a run is completed.

        Args:
            thread_id (str): The ID of the thread.
            run_id (str): The ID of the run.

        Returns:
            str: The assistant's response.
        """
        messages = await self.list_messages(thread_id)
        for message in messages.data:
            if message.role == "assistant" and message.run_id == run_id:
                return message.content[0].text.value
        return None
    
    async def submit_message(self, assistant_id: str, thread_id: str, user_message: str):
        """
        Submit a user message to a thread and create a new run.

        Args:
            assistant_id (str): The ID of the assistant.
            thread_id (str): The ID of the thread.
            user_message (str): The user's message content.

        Returns:
            The created run object.
        """
        self.client.beta.threads.messages.create(
            thread_id=thread_id, role="user", content=user_message
        )
        return self.client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=assistant_id,
        )

    async def get_response(self, thread_id: str):
        """
        Get all messages from a thread in ascending order.

        Args:
            thread_id (str): The ID of the thread.

        Returns:
            The list of messages in the thread.
        """
        return self.client.beta.threads.messages.list(thread_id=thread_id, order="asc")

    async def create_thread_and_run(self, assistant_id: str, user_input: str):
        """
        Create a new thread and submit a message to it.

        Args:
            assistant_id (str): The ID of the assistant.
            user_input (str): The user's message content.

        Returns:
            tuple: A tuple containing the created thread and run objects.
        """
        thread = await self.create_thread()
        run = await self.submit_message(assistant_id, thread.id, user_input)
        return thread, run

    async def wait_on_run(self, thread_id: str, run_id: str):
        """
        Wait for a run to complete.

        Args:
            thread_id (str): The ID of the thread.
            run_id (str): The ID of the run.

        Returns:
            The completed run object.
        """
        import time
        run = self.client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)
        while run.status in ["queued", "in_progress"]:
            time.sleep(0.5)
            run = self.client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)
        return run

    def pretty_print(self, messages):
        """
        Pretty print messages from a thread.

        Args:
            messages: The messages to print.
        """
        print("# Messages")
        for m in messages:
            print(f"{m.role}: {m.content[0].text.value}")
        print()

    async def handle_tool_call(self, run):
        """
        Handle tool call from a run.

        Args:
            run: The run object.

        Returns:
            The tool call object.
        """
        tool_call = run.required_action.submit_tool_outputs.tool_calls[0]
        return tool_call

    async def submit_tool_outputs(self, thread_id: str, run_id: str, tool_call, responses):
        """
        Submit tool outputs for a run.

        Args:
            thread_id (str): The ID of the thread.
            run_id (str): The ID of the run.
            tool_call: The tool call object.
            responses: The responses to submit.

        Returns:
            The updated run object.
        """
        run = self.client.beta.threads.runs.submit_tool_outputs(
            thread_id=thread_id,
            run_id=run_id,
            tool_outputs=[
                {
                    "tool_call_id": tool_call.id,
                    "output": json.dumps(responses),
                }
            ],
        )
        return run