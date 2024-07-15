import unittest
from unittest.mock import MagicMock
from datetime import date, datetime, timedelta
from app.services.todo.schedule_sender import ScheduleSender
from app.services.todo.task_manager import TaskManager
from app.google_client import GoogleClient

class TestScheduleSender(unittest.TestCase):
    def setUp(self):
        self.task_manager = MagicMock(spec=TaskManager)
        self.google_client = MagicMock(spec=GoogleClient)
        self.schedule_sender = ScheduleSender(self.task_manager, self.google_client)

    def test_send_daily_schedule(self):
        user_id = "user123"
        email = "user@example.com"
        schedule = "9:00 AM - Finish the report\n10:00 AM - Call the client"
        
        self.task_manager.generate_daily_schedule.return_value = schedule
        self.google_client.send_email.return_value = True
        
        result = self.schedule_sender.send_daily_schedule(user_id, email)
        self.assertTrue(result)
        self.google_client.send_email.assert_called_once_with(
            email,
            f"Your Daily Schedule for {date.today()}",
            f"Here's your schedule for today:\n\n{schedule}"
        )

    def test_send_weekly_summary(self):
        user_id = "user123"
        email = "user@example.com"
        completed_tasks = [
            {"description": "Finish the report", "due_date": date(2023, 10, 15)},
            {"description": "Call the client", "due_date": date(2023, 10, 16)}
        ]
        pending_tasks = [
            {"description": "Prepare presentation", "due_date": date(2023, 10, 17)},
            {"description": "Send email to team", "due_date": date(2023, 10, 18)}
        ]
        
        self.task_manager.get_tasks.side_effect = [completed_tasks, pending_tasks]
        self.google_client.send_email.return_value = True
        
        result = self.schedule_sender.send_weekly_summary(user_id, email)
        self.assertTrue(result)
        self.google_client.send_email.assert_called_once_with(
            email,
            f"Your Weekly Task Summary - {date.today()}",
            f"Here's your weekly task summary:\n\nCompleted Tasks:\n- Finish the report (Due: 2023-10-15)\n- Call the client (Due: 2023-10-16)\n\nPending Tasks:\n- Prepare presentation (Due: 2023-10-17)\n- Send email to team (Due: 2023-10-18)\n"
        )

    def test_send_task_reminders(self):
        user_id = "user123"
        email = "user@example.com"
        today = date.today()
        tasks = [
            {"description": "Finish the report", "due_date": today + timedelta(days=1)},
            {"description": "Call the client", "due_date": today + timedelta(days=3)}
        ]
        
        self.task_manager.get_tasks.return_value = tasks
        self.google_client.send_email.return_value = True
        
        result = self.schedule_sender.send_task_reminders(user_id, email)
        self.assertTrue(result)
        self.google_client.send_email.assert_called_once_with(
            email,
            "Task Reminders - Due Soon",
            f"The following tasks are due within the next 2 days:\n\n- Finish the report (Due: {today + timedelta(days=1)})\n"
        )

    def test_schedule_recurring_emails(self):
        user_id = "user123"
        email = "user@example.com"
        
        self.schedule_sender.schedule_recurring_emails(user_id, email)
        
        self.google_client.schedule_recurring_event.assert_any_call(
            "Send Daily Schedule",
            "Send daily schedule email",
            "RRULE:FREQ=DAILY;BYDAY=MO,TU,WE,TH,FR",
            unittest.mock.ANY
        )
        self.google_client.schedule_recurring_event.assert_any_call(
            "Send Weekly Summary",
            "Send weekly task summary email",
            "RRULE:FREQ=WEEKLY;BYDAY=FR",
            unittest.mock.ANY
        )
        self.google_client.schedule_recurring_event.assert_any_call(
            "Send Task Reminders",
            "Send task reminder emails",
            "RRULE:FREQ=DAILY",
            unittest.mock.ANY
        )

if __name__ == '__main__':
    unittest.main()