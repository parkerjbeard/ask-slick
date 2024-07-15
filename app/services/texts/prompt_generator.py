from typing import List, Dict
from app.openai_client import OpenAIClient

class PromptGenerator:
    def __init__(self):
        self.openai_client = OpenAIClient()

    def generate_prompt(self, family_member: str, relationship: str, last_contact: str, interests: List[str], recent_events: List[str]) -> str:
        """
        Generate a prompt for communicating with a family member.
        
        :param family_member: Name of the family member
        :param relationship: Relationship to the family member (e.g., "mother", "brother")
        :param last_contact: Date of last contact
        :param interests: List of interests of the family member
        :param recent_events: List of recent events in the family member's life
        :return: A generated prompt for communication
        """
        context = f"""
        Generate a thoughtful and personalized text message prompt for my {relationship}, {family_member}. 
        Our last contact was on {last_contact}. 
        Their interests include: {', '.join(interests)}. 
        Recent events in their life: {', '.join(recent_events)}.
        The message should be warm, caring, and reference their interests or recent events.
        Keep the message between 50-100 words.
        """

        prompt = self.openai_client.generate_text(context, max_tokens=150)
        return prompt

    def generate_birthday_prompt(self, family_member: str, relationship: str, age: int, interests: List[str]) -> str:
        """
        Generate a birthday message prompt for a family member.
        
        :param family_member: Name of the family member
        :param relationship: Relationship to the family member
        :param age: Age the family member is turning
        :param interests: List of interests of the family member
        :return: A generated birthday message prompt
        """
        context = f"""
        Generate a heartfelt birthday message for my {relationship}, {family_member}, who is turning {age}. 
        Their interests include: {', '.join(interests)}. 
        The message should be warm, celebratory, and possibly reference their interests or age milestone.
        Keep the message between 50-100 words.
        """

        prompt = self.openai_client.generate_text(context, max_tokens=150)
        return prompt

    def generate_holiday_prompt(self, family_member: str, relationship: str, holiday: str, traditions: List[str]) -> str:
        """
        Generate a holiday message prompt for a family member.
        
        :param family_member: Name of the family member
        :param relationship: Relationship to the family member
        :param holiday: Name of the holiday
        :param traditions: List of family traditions associated with the holiday
        :return: A generated holiday message prompt
        """
        context = f"""
        Generate a warm holiday message for my {relationship}, {family_member}, for {holiday}. 
        Our family traditions for this holiday include: {', '.join(traditions)}. 
        The message should be festive, reference our traditions, and express well wishes.
        Keep the message between 50-100 words.
        """

        prompt = self.openai_client.generate_text(context, max_tokens=150)
        return prompt

    def generate_check_in_prompt(self, family_member: str, relationship: str, last_contact: str, known_challenges: List[str]) -> str:
        """
        Generate a check-in message prompt for a family member who might be going through challenges.
        
        :param family_member: Name of the family member
        :param relationship: Relationship to the family member
        :param last_contact: Date of last contact
        :param known_challenges: List of known challenges the family member is facing
        :return: A generated check-in message prompt
        """
        context = f"""
        Generate a supportive check-in message for my {relationship}, {family_member}. 
        Our last contact was on {last_contact}. 
        They are currently facing these challenges: {', '.join(known_challenges)}. 
        The message should be caring, supportive, and offer help without being intrusive.
        Keep the message between 50-100 words.
        """

        prompt = self.openai_client.generate_text(context, max_tokens=150)
        return prompt