import os
import json
from datetime import datetime

def load_json(file_path):
    """
    Load a JSON file and return the data.
    
    :param file_path: Path to the JSON file.
    :return: Data loaded from the JSON file.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"No such file: '{file_path}'")
    
    with open(file_path, 'r') as file:
        return json.load(file)

def save_json(data, file_path):
    """
    Save data to a JSON file.
    
    :param data: Data to be saved.
    :param file_path: Path to the JSON file.
    """
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4)

def get_current_timestamp():
    """
    Get the current timestamp in a readable format.
    
    :return: Current timestamp as a string.
    """
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def ensure_dir(directory):
    """
    Ensure that a directory exists. If it doesn't, create it.
    
    :param directory: Path to the directory.
    """
    if not os.path.exists(directory):
        os.makedirs(directory)

# Example usage
if __name__ == "__main__":
    # Example of loading and saving JSON
    data = {"name": "AI Assistant", "version": "1.0"}
    save_json(data, 'example.json')
    loaded_data = load_json('example.json')
    print(loaded_data)

    # Example of getting current timestamp
    print(get_current_timestamp())

    # Example of ensuring a directory exists
    ensure_dir('example_dir')