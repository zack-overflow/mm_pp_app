import json
import pandas as pd
from match_players import get_player_data_from_entry_player

JSON_FILE_PATH = "/var/data/scoreboard.json"

def get_entrant_data(entrant_name):
    """
    Get the data for a specific entrant.
    
    Args:
        entrant_name (str): The name of the entrant to get data for.

    Returns:
        dict: The data for the entrant.
    """
    print(f"Getting data for entrant: {entrant_name}")
    # Load the data from the JSON file
    with open(JSON_FILE_PATH, 'r') as f:
        player_data = json.load(f)
    
    pp_players = pd.read_csv('pp_players_form2025.csv')
    pp_players = pp_players[['firstName', 'lastName', 'playin']]
    # combine first and last name to create full player name
    pp_players['player'] = pp_players['firstName'].str.upper() + ' ' + pp_players['lastName'].str.upper()
    # make names uppercase and remove punctuation
    pp_players['player'] = pp_players['player'].str.replace(r'[^A-Z\s]', '', regex=True)

    # PLACEHOLDER: PICK RANDOM ROWS FROM pp_players where playin == 1
    playins = pp_players[pp_players['playin'] == 1]
    random_player_sample = playins.sample(15)

    data = {}
    for player in random_player_sample['player']:
        data[player] = get_player_data_from_entry_player(player, player_data)
    
    return data