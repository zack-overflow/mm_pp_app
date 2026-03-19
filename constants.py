import os

# Use /var/data/data.json if it exists, otherwise use local.json
if os.path.exists("/var/data/data.json"):
    PLAYER_SCORING_DATA_JSON_FILE_PATH = "/var/data/data.json"
    TEAMS_ALIVE_MASK_JSON_FILE_PATH = "/var/data/teams_alive_mask.json"
    ENTRIES_FILE_PATH = "null_kaval_entries_final.json"
    ENTRIES_WRITE_FILE_PATH = "/var/data/null_kaval_entries.json"
    PK_ENTRIES_FILE_PATH = "entries_final.json"
else:
    PLAYER_SCORING_DATA_JSON_FILE_PATH = "local.json"
    TEAMS_ALIVE_MASK_JSON_FILE_PATH = "teams_alive_mask.json"
    ENTRIES_FILE_PATH = "null_kaval_entries_temp.json"
    ENTRIES_WRITE_FILE_PATH = "null_kaval_entries.json"
    PK_ENTRIES_FILE_PATH = "entries.json"

DEFAULT_TEAMS_ALIVE_MASK = {
    "Akron": 1,
    "Alabama": 1,
    "Arizona": 1,
    "Arkansas": 1,
    "BYU": 1,
    "CA Baptist": 1,
    "Clemson": 1,
    "Duke": 1,
    "Florida": 1,
    "Furman": 1,
    "Georgia": 1,
    "Gonzaga": 1,
    "Hawai'i": 1,
    "High Point": 1,
    "Hofstra": 1,
    "Houston": 1,
    "Howard": 1,
    "Idaho": 1,
    "Illinois": 1,
    "Iowa": 1,
    "Iowa State": 1,
    "Kansas": 1,
    "Kennesaw St": 1,
    "Kentucky": 1,
    "Long Island": 1,
    "Louisville": 1,
    "McNeese": 1,
    "Miami": 1,
    "Miami OH": 1,
    "Michigan": 1,
    "Michigan St": 1,
    "Missouri": 1,
    "N Dakota St": 1,
    "Nebraska": 1,
    "North Carolina": 1,
    "Northern Iowa": 1,
    "Ohio State": 0,
    "Penn": 1,
    "Prairie View": 1,
    "Purdue": 1,
    "Queens": 1,
    "Saint Louis": 1,
    "Saint Mary's": 1,
    "Santa Clara": 1,
    "Siena": 1,
    "South Florida": 1,
    "St John's": 1,
    "TCU": 1,
    "Tennessee": 1,
    "Tennessee St": 1,
    "Texas": 1,
    "Texas A&M": 1,
    "Texas Tech": 1,
    "Troy": 0,
    "UCF": 1,
    "UCLA": 1,
    "UConn": 1,
    "Utah State": 1,
    "VCU": 1,
    "Vanderbilt": 1,
    "Villanova": 1,
    "Virginia": 1,
    "Wisconsin": 1,
    "Wright St": 1,
}