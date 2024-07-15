# AI-Powered Personal Assistant Slack Bot

## Overview

This project is an advanced Slack bot that serves as an AI-powered personal assistant for busy professionals. It integrates various APIs and services to provide a wide range of functionalities, all accessible through natural language interactions in Slack.

## Key Features

1. Calendar Management
2. Family Communication Assistant
3. Travel Planning
4. Task Management
5. Document Retrieval

## Technical Stack

- Backend: Python
- Slack API: For bot interactions and command handling
- OpenAI API: For natural language processing and generation
- Google APIs: For calendar, email, and document management
- Database: SQLAlchemy for storing user preferences, family information, and document metadata

## Installation and Setup

1. Clone the repository:


## Usage

### Slack Commands

- `/schedule`: Schedule meetings or find open time slots
- `/family`: Generate prompts for family communication
- `/travel`: Plan trips and get travel suggestions
- `/todo`: Manage tasks and to-do lists
- `/document`: Search and retrieve documents

### Natural Language Interactions

Users can interact with the bot using natural language. For example:

- "Schedule a meeting with John and Sarah for 1 hour next Tuesday at 2 PM"
- "Find open slots for a 1-hour meeting next week"
- "Send an email to John and Sarah about the project update"
- "Add 'Finish report' to my todo list for tomorrow"
- "Find documents related to the Q4 marketing strategy"

## Functionality Details

### Calendar Management (CalendarAssistant)

- Schedule meetings
- Find open time slots
- Send coordination emails
- Get daily schedules
- Reschedule meetings
- Cancel meetings
- Set out-of-office periods

### Family Communication Assistant (PromptGenerator)

- Generate personalized communication prompts
- Create birthday message prompts
- Generate holiday message prompts
- Produce check-in message prompts for family members facing challenges

### Travel Planning (TravelPlanner)

- Parse travel requests
- Search for flights
- Find accommodations
- Generate travel suggestions

### Task Management (TaskManager)

- Add tasks
- Get tasks
- Update task status
- Delete tasks
- Prioritize tasks
- Generate daily schedules
- Parse natural language task descriptions

### Document Retrieval (DocumentSearcher)

- Generate document embeddings
- Search documents based on content queries
- Calculate cosine similarity for relevance ranking

## Additional Components

### Google Client

Handles authentication and interactions with Google APIs for calendar, email, and document management.

### OpenAI Client

Manages interactions with the OpenAI API for natural language processing tasks.

### Slack Bot

Handles Slack interactions and routes requests to appropriate services.

## Testing

The project includes unit tests for various components. To run the tests:


## Logging

The project uses a custom logger to track events and errors. Logs are stored in the `logs` directory.

## Contributing

1. Fork the repository
2. Create a new branch: `git checkout -b feature-branch-name`
3. Make changes and commit: `git commit -m 'Add some feature'`
4. Push to the branch: `git push origin feature-branch-name`
5. Submit a pull request

## License

This project is licensed under the MIT License.


## Logging

The project uses a custom logger to track events and errors. Logs are stored in the `logs` directory.

## Contributing

1. Fork the repository
2. Create a new branch: `git checkout -b feature-branch-name`
3. Make changes and commit: `git commit -m 'Add some feature'`
4. Push to the branch: `git push origin feature-branch-name`
5. Submit a pull request

## License

This project is licensed under the MIT License.