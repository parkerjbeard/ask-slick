import datetime
from typing import List, Dict, Optional
from database.db_manager import DatabaseManager
from app.openai_client import OpenAIClient

class TaskManager:
    def __init__(self, db_manager: DatabaseManager, openai_client: OpenAIClient):
        self.db_manager = db_manager
        self.openai_client = openai_client

    def add_task(self, user_id: str, task_description: str, due_date: Optional[datetime.date] = None, priority: str = "medium") -> bool:
        """
        Add a new task to the user's to-do list.
        """
        task = {
            "user_id": user_id,
            "description": task_description,
            "due_date": due_date,
            "priority": priority,
            "status": "pending",
            "created_at": datetime.datetime.now()
        }
        return self.db_manager.insert_task(task)

    def get_tasks(self, user_id: str, status: str = "pending") -> List[Dict]:
        """
        Retrieve tasks for a given user and status.
        """
        return self.db_manager.get_tasks(user_id, status)

    def update_task_status(self, task_id: int, new_status: str) -> bool:
        """
        Update the status of a task.
        """
        return self.db_manager.update_task_status(task_id, new_status)

    def delete_task(self, task_id: int) -> bool:
        """
        Delete a task from the to-do list.
        """
        return self.db_manager.delete_task(task_id)

    def prioritize_tasks(self, user_id: str) -> List[Dict]:
        """
        Use OpenAI to prioritize tasks based on their descriptions and due dates.
        """
        tasks = self.get_tasks(user_id)
        if not tasks:
            return []

        task_descriptions = "\n".join([f"{task['id']}: {task['description']} (Due: {task['due_date']})" for task in tasks])
        prompt = f"Prioritize the following tasks from highest to lowest priority. Only return the task IDs in order, separated by commas:\n\n{task_descriptions}"
        
        prioritized_ids = self.openai_client.generate_text(prompt).split(',')
        prioritized_tasks = sorted(tasks, key=lambda x: prioritized_ids.index(str(x['id'])) if str(x['id']) in prioritized_ids else len(tasks))
        
        return prioritized_tasks

    def generate_daily_schedule(self, user_id: str) -> str:
        """
        Generate a daily schedule based on the user's tasks.
        """
        tasks = self.prioritize_tasks(user_id)
        task_list = "\n".join([f"- {task['description']} (Priority: {task['priority']}, Due: {task['due_date']})" for task in tasks])
        
        prompt = f"Create a daily schedule based on the following prioritized tasks:\n\n{task_list}\n\nProvide a structured schedule with time blocks and task assignments."
        return self.openai_client.generate_text(prompt, max_tokens=300)

    def parse_natural_language_task(self, user_id: str, text: str) -> Dict:
        """
        Parse a natural language task description and extract relevant information.
        """
        prompt = f"Extract the following information from this task description: 1) Task description, 2) Due date (if any), 3) Priority (high, medium, or low). Task: {text}"
        response = self.openai_client.generate_text(prompt)
        
        # Parse the response and create a task dictionary
        # This is a simplified version; you might want to use regex or more sophisticated parsing
        lines = response.split('\n')
        task = {
            "user_id": user_id,
            "description": lines[0].split(': ', 1)[1] if len(lines) > 0 else text,
            "due_date": lines[1].split(': ', 1)[1] if len(lines) > 1 else None,
            "priority": lines[2].split(': ', 1)[1] if len(lines) > 2 else "medium"
        }
        
        return task