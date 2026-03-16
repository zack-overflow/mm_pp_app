import os

# Use /var/data/data.json if it exists, otherwise use local.json
if os.path.exists("/var/data/data.json"):
    JSON_FILE_PATH = "/var/data/data.json"
    ENTRIES_FILE_PATH = "/var/data/entries.json"
else:
    JSON_FILE_PATH = "local.json"
    ENTRIES_FILE_PATH = "entries.json"

TEAMS_ALIVE_MASK = {
}

ESPN_TO_PP_MAP = {
    
}
