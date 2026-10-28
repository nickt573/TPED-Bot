import json
import os

# Saves bot settings and scheduled reminders so they survive restarts
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

def load_config():
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_config(data):
    # Write to a temp file first so a crash mid-write can't corrupt the config
    tmp_path = CONFIG_PATH + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
    os.replace(tmp_path, CONFIG_PATH)
