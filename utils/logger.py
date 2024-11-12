import logging

# Create a custom logger
logger = logging.getLogger('slack_ai_assistant')
logger.setLevel(logging.DEBUG)

# Create handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)

# Create formatter and add it to handler
console_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(console_format)

# Add handler to the logger
logger.addHandler(console_handler)