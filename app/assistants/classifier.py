from app.assistants.assistant_manager import AssistantManager
from typing import List, Dict, Any

class Classifier:
    def __init__(self, assistant_manager: AssistantManager):
        self.assistant_manager = assistant_manager
        self.classifier_assistant_id = None
        self.thread_id = None
        self.categories = ["schedule", "family", "travel", "todo", "document"]

    async def initialize(self):
        assistants = await self.assistant_manager.list_assistants()
        self.classifier_assistant_id = assistants.get("ClassifierAssistant")
        if not self.classifier_assistant_id:
            raise ValueError("ClassifierAssistant not found. Please run update_assistants() first.")

    async def classify_message(self, user_input: str) -> str:
        if not self.classifier_assistant_id:
            await self.initialize()

        if not self.thread_id:
            thread = await self.assistant_manager.create_thread()
            self.thread_id = thread.id

        await self.assistant_manager.create_message(self.thread_id, "user", user_input)

        messages = await self.assistant_manager.list_messages(self.thread_id, order="desc", limit=5)
        context = "\n".join([f"{msg.role}: {msg.content[0].text.value}" for msg in reversed(messages.data)])

        instructions = self._generate_classification_instructions(context)

        run = await self.assistant_manager.create_run(
            thread_id=self.thread_id,
            assistant_id=self.classifier_assistant_id,
            instructions=instructions
        )

        run = self.assistant_manager.wait_on_run(self.thread_id, run.id)
        classification = await self.assistant_manager.get_assistant_response(self.thread_id, run.id)

        return self._validate_classification(classification.strip().lower())

    def _generate_classification_instructions(self, context: str) -> str:
        return f"""
        Classify the last user message into one of these categories: {', '.join(self.categories)}.
        
        Consider the following guidelines:
        1. Schedule: Messages about appointments, meetings, or time-specific events.
        2. Family: Messages related to family members, relationships, or household matters.
        3. Travel: Messages about trips, vacations, flights, hotels, or any travel-related queries.
        4. Todo: Messages about tasks, to-do lists, or things that need to be done.
        5. Document: Messages about creating, editing, or managing documents, files, or paperwork.
        6. General: Messages that don't fit into the other categories.

        Context of the conversation:
        {context}

        Instructions:
        1. Analyze the context and the last user message carefully.
        2. If the message fits multiple categories, choose the most relevant one based on the primary intent.
        3. If the message doesn't clearly fit any category, choose the closest match.
        4. Your response should be a single word (the category name in lowercase).

        Example classifications:
        - "What time is my dentist appointment?" -> schedule
        - "Book a flight to New York for next week" -> travel
        - "Remind me to call mom tonight" -> family (primary intent) or todo (secondary intent)
        - "Create a report on Q2 sales" -> document

        Now, classify the last user message:
        """

    def _validate_classification(self, classification: str) -> str:
        if classification not in self.categories:
            # If the classification is invalid, default to the most general category
            return "general"
        return classification