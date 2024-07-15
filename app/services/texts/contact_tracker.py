from datetime import datetime, timedelta
from typing import Dict, List

class ContactTracker:
    def __init__(self):
        self.contacts: Dict[str, Dict] = {}

    def add_family_member(self, name: str, relationship: str, interests: List[str], birthday: datetime) -> None:
        """
        Add a new family member to the contact tracker.
        
        :param name: Name of the family member
        :param relationship: Relationship to the family member
        :param interests: List of interests of the family member
        :param birthday: Birthday of the family member
        """
        self.contacts[name] = {
            "relationship": relationship,
            "interests": interests,
            "birthday": birthday,
            "last_contact": None,
            "recent_events": [],
            "known_challenges": []
        }

    def update_last_contact(self, name: str) -> None:
        """
        Update the last contact date for a family member.
        
        :param name: Name of the family member
        """
        if name in self.contacts:
            self.contacts[name]["last_contact"] = datetime.now()

    def add_recent_event(self, name: str, event: str) -> None:
        """
        Add a recent event for a family member.
        
        :param name: Name of the family member
        :param event: Description of the recent event
        """
        if name in self.contacts:
            self.contacts[name]["recent_events"].append(event)
            if len(self.contacts[name]["recent_events"]) > 5:
                self.contacts[name]["recent_events"].pop(0)

    def add_known_challenge(self, name: str, challenge: str) -> None:
        """
        Add a known challenge for a family member.
        
        :param name: Name of the family member
        :param challenge: Description of the challenge
        """
        if name in self.contacts:
            self.contacts[name]["known_challenges"].append(challenge)

    def remove_known_challenge(self, name: str, challenge: str) -> None:
        """
        Remove a known challenge for a family member.
        
        :param name: Name of the family member
        :param challenge: Description of the challenge to remove
        """
        if name in self.contacts and challenge in self.contacts[name]["known_challenges"]:
            self.contacts[name]["known_challenges"].remove(challenge)

    def get_family_members_to_contact(self, days_threshold: int = 7) -> List[str]:
        """
        Get a list of family members who haven't been contacted in the specified number of days.
        
        :param days_threshold: Number of days to use as the threshold
        :return: List of family members to contact
        """
        threshold_date = datetime.now() - timedelta(days=days_threshold)
        return [name for name, data in self.contacts.items() if data["last_contact"] is None or data["last_contact"] < threshold_date]

    def get_upcoming_birthdays(self, days_ahead: int = 7) -> List[Dict]:
        """
        Get a list of family members with upcoming birthdays within the specified number of days.
        
        :param days_ahead: Number of days to look ahead
        :return: List of dictionaries containing family member information and their upcoming birthday
        """
        today = datetime.now().date()
        upcoming_birthdays = []
        for name, data in self.contacts.items():
            birthday = data["birthday"].replace(year=today.year)
            if birthday < today:
                birthday = birthday.replace(year=today.year + 1)
            days_until_birthday = (birthday - today).days
            if 0 <= days_until_birthday <= days_ahead:
                upcoming_birthdays.append({
                    "name": name,
                    "relationship": data["relationship"],
                    "birthday": birthday,
                    "days_until": days_until_birthday
                })
        return upcoming_birthdays

    def get_family_member_info(self, name: str) -> Dict:
        """
        Get all stored information for a specific family member.
        
        :param name: Name of the family member
        :return: Dictionary containing all stored information for the family member
        """
        return self.contacts.get(name, {})