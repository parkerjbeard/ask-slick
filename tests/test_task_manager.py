import unittest
from unittest.mock import MagicMock
from datetime import datetime, date
from app.services.todo.task_manager import TaskManager
from database.db_manager import DatabaseManager
from app.openai_helper import OpenAIClient

class TestTaskManager(unittest.TestCase):
    def setUp(self):
        self.db_manager = MagicMock(spec=DatabaseManager)
        self.openai_client = MagicMock(spec=OpenAIClient)
        self.task_manager = TaskManager(self.db_manager, self.openai_client)

    def test_add_task(self):
        user_id = "user123"
        task_description = "Finish the report"
        due_date = date(2023, 10, 15)
        priority = "high"
        
        self.db_manager.insert_task.return_value = True
        
        result = self.task_manager.add_task(user_id, task_description, due_date, priority)
        self.assertTrue(result)
        self.db_manager.insert_task.assert_called_once()

    def test_get_tasks(self):
        user_id = "user123"
        tasks = [
            {"id": 1, "description": "Finish the report", "due_date": date(2023, 10, 15), "priority": "high", "status": "pending"},
            {"id": 2, "description": "Call the client", "due_date": date(2023, 10, 16), "priority": "medium", "status": "pending"}
        ]
        
        self.db_manager.get_tasks.return_value = tasks
        
        result = self.task_manager.get_tasks(user_id)
        self.assertEqual(result, tasks)
        self.db_manager.get_tasks.assert_called_once_with(user_id, "pending")

    def test_update_task_status(self):
        task_id = 1
        new_status = "completed"
        
        self.db_manager.update_task_status.return_value = True
        
        result = self.task_manager.update_task_status(task_id, new_status)
        self.assertTrue(result)
        self.db_manager.update_task_status.assert_called_once_with(task_id, new_status)

    def test_delete_task(self):
        task_id = 1
        
        self.db_manager.delete_task.return_value = True
        
        result = self.task_manager.delete_task(task_id)
        self.assertTrue(result)
        self.db_manager.delete_task.assert_called_once_with(task_id)

    def test_prioritize_tasks(self):
        user_id = "user123"
        tasks = [
            {"id": 1, "description": "Finish the report", "due_date": date(2023, 10, 15), "priority": "high", "status": "pending"},
            {"id": 2, "description": "Call the client", "due_date": date(2023, 10, 16), "priority": "medium", "status": "pending"}
        ]
        
        self.db_manager.get_tasks.return_value = tasks
        self.openai_client.generate_text.return_value = "1,2"
        
        result = self.task_manager.prioritize_tasks(user_id)
        self.assertEqual(result, tasks)
        self.db_manager.get_tasks.assert_called_once_with(user_id, "pending")
        self.openai_client.generate_text.assert_called_once()

    def test_generate_daily_schedule(self):
        user_id = "user123"
        tasks = [
            {"id": 1, "description": "Finish the report", "due_date": date(2023, 10, 15), "priority": "high", "status": "pending"},
            {"id": 2, "description": "Call the client", "due_date": date(2023, 10, 16), "priority": "medium", "status": "pending"}
        ]
        
        self.task_manager.prioritize_tasks = MagicMock(return_value=tasks)
        self.openai_client.generate_text.return_value = "9:00 AM - Finish the report\n10:00 AM - Call the client"
        
        result = self.task_manager.generate_daily_schedule(user_id)
        self.assertIn("9:00 AM - Finish the report", result)
        self.assertIn("10:00 AM - Call the client", result)
        self.task_manager.prioritize_tasks.assert_called_once_with(user_id)
        self.openai_client.generate_text.assert_called_once()

    def test_parse_natural_language_task(self):
        user_id = "user123"
        text = "Finish the report by next Monday with high priority"
        response = "Task description: Finish the report\nDue date: 2023-10-16\nPriority: high"
        
        self.openai_client.generate_text.return_value = response
        
        result = self.task_manager.parse_natural_language_task(user_id, text)
        expected_result = {
            "user_id": user_id,
            "description": "Finish the report",
            "due_date": "2023-10-16",
            "priority": "high"
        }
        self.assertEqual(result, expected_result)
        self.openai_client.generate_text.assert_called_once()

if __name__ == '__main__':
    unittest.main()