import json
from constants import PLAYER_SCORING_DATA_JSON_FILE_PATH, TEAMS_ALIVE_MASK

def get_player_data(player_name):
    """
    Returns the player data for a specific player.
    This includes:
    - Player name
    - Team
    - Seed
    - Points(split by round)
    - Points multiplier
    - Team alive status
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

    # check who picked this player

    # Initialize the response dictionary
    response = {
        "player": player_name,
        "team": player_data["team"],
        "seed": player_data["seed"],
        "pts": pts,
        "pts_mult": player_data["pts_mult"],
        "pts_mult_round": pts_mult_rounds,
        "alive": TEAMS_ALIVE_MASK.get(player_data.get("team"), 0) == 1,
    }

    return response
    
