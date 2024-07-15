import datetime
from typing import List, Dict
from app.google_client import GoogleClient
from app.services.todo.task_manager import TaskManager

class ScheduleSender:
    def __init__(self, task_manager: TaskManager, google_client: GoogleClient):
        self.task_manager = task_manager
        self.google_client = google_client

    def send_daily_schedule(self, user_id: str, email: str) -> bool:
        """
        Generate and send the daily schedule to the user's email.
        """
        schedule = self.task_manager.generate_daily_schedule(user_id)
        subject = f"Your Daily Schedule for {datetime.date.today()}"
        body = f"Here's your schedule for today:\n\n{schedule}"
        
        return self.google_client.send_email(email, subject, body)

    def send_weekly_summary(self, user_id: str, email: str) -> bool:
        """
        Generate and send a weekly summary of completed and pending tasks.
        """
        completed_tasks = self.task_manager.get_tasks(user_id, status="completed")
        pending_tasks = self.task_manager.get_tasks = self.task_manager.get_tasks(user_id, status="pending")
        
        completed_summary = self._format_task_summary(completed_tasks, "Completed")
        pending_summary = self._format_task_summary(pending_tasks, "Pending")
        
        subject = f"Your Weekly Task Summary - {datetime.date.today()}"
        body = f"Here's your weekly task summary:\n\n{completed_summary}\n\n{pending_summary}"
        
        return self.google_client.send_email(email, subject, body)

    def _format_task_summary(self, tasks: List[Dict], status: str) -> str:
        """
        Format a list of tasks into a readable summary.
        """
        task_list = "\n".join([f"- {task['description']} (Due: {task['due_date']})" for task in tasks])
        return f"{status} Tasks:\n{task_list}\n"

    def send_task_reminders(self, user_id: str, email: str) -> bool:
        """
        Send reminders for tasks due soon.
        """
        tasks = self.task_manager.get_tasks(user_id, status="pending")
        today = datetime.date.today()
        soon_due_tasks = [task for task in tasks if task['due_date'] and (task['due_date'] - today).days <= 2]
        
        if not soon_due_tasks:
            return True  # No tasks due soon, no need to send a reminder
        
        task_list = "\n".join([f"- {task['description']} (Due: {task['due_date']})" for task in soon_due_tasks])
        subject = "Task Reminders - Due Soon"
        body = f"The following tasks are due within the next 2 days:\n\n{task_list}"
        
        return self.google_client.send_email(email, subject, body)

    def schedule_recurring_emails(self, user_id: str, email: str) -> None:
        """
        Schedule recurring emails for daily schedules, weekly summaries, and task reminders.
        """
        # Schedule daily schedule emails
        self.google_client.schedule_recurring_event(
            "Send Daily Schedule",
            "Send daily schedule email",
            "RRULE:FREQ=DAILY;BYDAY=MO,TU,WE,TH,FR",
            lambda: self.send_daily_schedule(user_id, email)
        )
        
        # Schedule weekly summary emails
        self.google_client.schedule_recurring_event(
            "Send Weekly Summary",
            "Send weekly task summary email",
            "RRULE:FREQ=WEEKLY;BYDAY=FR",
            lambda: self.send_weekly_summary(user_id, email)
        )
        
        # Schedule daily task reminder emails
        self.google_client.schedule_recurring_event(
            "Send Task Reminders",
            "Send task reminder emails",
            "RRULE:FREQ=DAILY",
            lambda: self.send_task_reminders(user_id, email)
        )