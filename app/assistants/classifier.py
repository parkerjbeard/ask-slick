from app.assistants.assistant_manager import AssistantManager

class Classifier:
    def __init__(self, assistant_manager: AssistantManager):
        self.assistant_manager = assistant_manager
        self.classifier_assistant_id = None
        self.thread_id = None

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

        instructions = f"""Classify the last user message into one of these categories: schedule, family, travel, todo, document.
        Consider the context of the conversation:
        
        {context}
        
        Your response should be a single word (the category)."""

        run = await self.assistant_manager.create_run(
            thread_id=self.thread_id,
            assistant_id=self.classifier_assistant_id,
            instructions=instructions
        )

        run = self.assistant_manager.wait_on_run(self.thread_id, run.id)
        classification = await self.assistant_manager.get_assistant_response(self.thread_id, run.id)

        return classification.strip().lower()