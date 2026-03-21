import json
from constants import PLAYER_SCORING_DATA_JSON_FILE_PATH, ENTRIES_FILE_PATH, PK_ENTRIES_FILE_PATH
from teams_alive import is_team_alive

def get_player_data(player_name, pikap=False, entries_path=None):
    """
    Returns the player data for a specific player.
    This includes:
    - Player name
    - Team
    - Seed
    - Points(split by round)
    - Points multiplier
    - Team alive status
    - Ownership info (how many entrants picked this player)
    """

    # Load the JSON data
    with open(PLAYER_SCORING_DATA_JSON_FILE_PATH, 'r') as file:
        data = json.load(file)

    # Check if the player exists in the data
    if player_name not in data:
        return None

    player_data = data[player_name]

    # Reverse order of points to match the order of rounds without mutating source data
    pts = list(reversed(player_data.get("pts", [])))
    pts_mult_rounds = list(reversed(player_data.get("pts_mult_rounds", [])))

    # Count how many entrants picked this player
    target_entries_path = entries_path or (PK_ENTRIES_FILE_PATH if pikap else ENTRIES_FILE_PATH)
    picked_by = []
    total_entrants = 0
    try:
        with open(target_entries_path, 'r') as f:
            entries = json.load(f)
        total_entrants = len(entries)
        for entrant_name, entry in entries.items():
            picks = [p.strip().upper() for p in entry.get("picks", [])]
            if player_name in picks:
                picked_by.append(entrant_name)
    except (FileNotFoundError, json.JSONDecodeError):
        pass

    # Initialize the response dictionary
    response = {
        "player": player_name,
        "team": player_data["team"],
        "seed": player_data["seed"],
        "pts": pts,
        "pts_mult": player_data["pts_mult"],
        "pts_mult_round": pts_mult_rounds,
        "alive": is_team_alive(player_data.get("team")),
        "picked_by": picked_by,
        "total_entrants": total_entrants,
    }

    return response
    
