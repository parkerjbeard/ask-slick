from app.assistants.assistant_manager import AssistantManager
from app.config.assistant_config import AssistantCategory, AssistantConfig

class Classifier:
    def __init__(self, assistant_manager: AssistantManager):
        self.assistant_manager = assistant_manager
        self.classifier_assistant_id = None
        self.thread_id = None
        self.categories = [category.value for category in AssistantCategory if category != AssistantCategory.CLASSIFIER]

    async def initialize(self):
        assistants = await self.assistant_manager.list_assistants()
        self.classifier_assistant_id = assistants.get(AssistantConfig.ASSISTANT_NAMES[AssistantCategory.CLASSIFIER])
        if not self.classifier_assistant_id:
            raise ValueError(f"{AssistantConfig.ASSISTANT_NAMES[AssistantCategory.CLASSIFIER]} not found. Please run update_assistants() first.")


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
        guidelines = "\n".join([f"{i+1}. {category.name.capitalize()}: {description}" 
                                for i, (category, description) in enumerate(AssistantConfig.CATEGORY_DESCRIPTIONS.items())])

        return f"""
        Classify the last user message into one of these categories: {', '.join(self.categories)}.
        
        Consider the following guidelines:
        {guidelines}

        Context of the conversation:
        {context}

        Instructions:
        1. Analyze the context and the last user message carefully.
        2. If the message fits multiple categories, choose the most relevant one based on the primary intent.
        3. If the message doesn't clearly fit any category, choose the closest match.
        4. Your response should be a single word (the category name in lowercase).

        Example classifications:
        - "What time is my dentist appointment?" -> {AssistantCategory.SCHEDULE.value}
        - "Book a flight to New York for next week" -> {AssistantCategory.TRAVEL.value}
        - "Remind me to call mom tonight" -> {AssistantCategory.FAMILY.value} (primary intent) or {AssistantCategory.TODO.value} (secondary intent)
        - "Create a report on Q2 sales" -> {AssistantCategory.DOCUMENT.value}

        Now, classify the last user message:
        """

    def _validate_classification(self, classification: str) -> str:
        if classification not in self.categories:
            # If the classification is invalid, default to the most general category
            return AssistantCategory.GENERAL.value
        return classification