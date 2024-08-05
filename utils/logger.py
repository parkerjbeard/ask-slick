import logging
import os
from logging.handlers import RotatingFileHandler

# Create a directory for logs if it doesn't exist
log_dir = 'logs'
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# Define the log file path
log_file = os.path.join(log_dir, 'app.log')

# Create a custom logger
logger = logging.getLogger('slack_ai_assistant')
logger.setLevel(logging.DEBUG)

# Create handlers
console_handler = logging.StreamHandler()
file_handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=2)

# Set logging levels for handlers
console_handler.setLevel(logging.DEBUG)
file_handler.setLevel(logging.DEBUG)

# Create formatters and add them to handlers
console_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

console_handler.setFormatter(console_format)
file_handler.setFormatter(file_format)

# Add handlers to the logger
logger.addHandler(console_handler)
logger.addHandler(file_handler)