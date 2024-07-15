from slack_bolt import App
import os
from app.services.travel.travel_planner import TravelPlanner

# Initialize the Slack app
from dotenv import load_dotenv
load_dotenv()
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))

# These will be set from main.py
prompt_generator = None
travel_planner = None
task_manager = None
document_searcher = None

@app.event("app_mention")
def handle_mentions(event, say):
    text = event["text"].lower()
    user = event["user"]

    if "schedule" in text:
        response = "Schedule a meeting"
    elif "family" in text:
        # Assuming user information is fetched from a database or another service
        user_info = {"name": "John Doe", "relationship": "brother", "last_contact": "2023-01-01", "interests": ["hiking", "reading"], "recent_events": ["got a new job"]}
        response = prompt_generator.generate_prompt(user_info["name"], user_info["relationship"], user_info["last_contact"], user_info["interests"], user_info["recent_events"])
    elif "travel" in text:
        travel_request = travel_planner.parse_travel_request(text)
        if "error" in travel_request:
            response = travel_request["error"]
        else:
            flights = travel_planner.search_flights(travel_request["origin"], travel_request["destination"], travel_request["departure_date"], travel_request["return_date"])
            accommodations = travel_planner.search_accommodations(travel_request["destination"], travel_request["check_in"], travel_request["check_out"])
            suggestions = travel_planner.generate_travel_suggestions(travel_request["destination"])
            response = f"Flights: {flights}\nAccommodations: {accommodations}\nSuggestions: {suggestions}"
    elif "todo" in text:
        response = task_manager.handle_todo_request(text)
    elif "document" in text:
        response = document_searcher.search_documents(text)
    else:
        response = "I'm not sure how to help with that. You can ask me about scheduling, family prompts, travel, todos, or document retrieval."

    say(response)

@app.command("/schedule")
def handle_schedule_command(ack, respond, command):
    ack()
    response = "Schedule a meeting"
    respond(response)

@app.command("/family")
def handle_family_command(ack, respond, command):
    ack()
    user_info = {"name": "John Doe", "relationship": "brother", "last_contact": "2023-01-01", "interests": ["hiking", "reading"], "recent_events": ["got a new job"]}
    response = prompt_generator.generate_prompt(user_info["name"], user_info["relationship"], user_info["last_contact"], user_info["interests"], user_info["recent_events"])
    respond(response)

@app.command("/travel")
def handle_travel_command(ack, respond, command):
    ack()
    travel_request = travel_planner.parse_travel_request(command["text"])
    if "error" in travel_request:
        response = travel_request["error"]
    else:
        flights = travel_planner.search_flights(travel_request["origin"], travel_request["destination"], travel_request["departure_date"], travel_request["return_date"])
        accommodations = travel_planner.search_accommodations(travel_request["destination"], travel_request["check_in"], travel_request["check_out"])
        suggestions = travel_planner.generate_travel_suggestions(travel_request["destination"])
        response = f"Flights: {flights}\nAccommodations: {accommodations}\nSuggestions: {suggestions}"
    respond(response)

@app.command("/todo")
def handle_todo_command(ack, respond, command):
    ack()
    response = task_manager.handle_todo_request(command["text"])
    respond(response)

@app.command("/document")
def handle_document_command(ack, respond, command):
    ack()
    response = document_searcher.search_documents(command["text"])
    respond(response)