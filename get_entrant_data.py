import json
import pandas as pd
from get_player_data_from_entry_player import get_player_data_from_entry_player
from constants import JSON_FILE_PATH


def get_entrant_data(entrant_name, pikap=False):
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
    pp_players = pp_players[['firstName', 'lastName', 'pts_std', 'seed', 'team']]
    # combine first and last name to create full player name
    pp_players['player'] = pp_players['firstName'].str.upper() + ' ' + pp_players['lastName'].str.upper()
    # make names uppercase and remove punctuation
    pp_players['player'] = pp_players['player'].str.replace(r'[^A-Z\s]', '', regex=True)

    if pikap:
        pikap_df = pd.read_csv('combined_players.csv') # columns are entrants
        entrant_players = pikap_df[entrant_name].tolist()
        print(entrant_players)
    else:
        nk_df = pd.read_csv('null_kaval_cleaned.csv') # columns are entrants
        entrant_players = nk_df[entrant_name].tolist()
        print(entrant_players)

    # Grab data for the enrant's players
    entrant_results = {}
    for entrant_player in entrant_players:
        res = get_player_data_from_entry_player(entrant_player, player_data)
        # if result is None, put a false entry in the dict

        if res is None:
            # get seed from pp_players
            pp_player = pp_players[pp_players['player'] == entrant_player]
            if not pp_player.empty:
                seed = int(pp_player['seed'].values[0])
                team = pp_player['team'].values[0]
                pts_std = pp_player['pts_std'].values[0]
            else:
                seed = 'Not found'
                team = 'Not found'
                pts_std = 'Not found'
            
            entrant_results[entrant_player] = {
                'pts': 'Not played yet',
                'pts_mult': 'Not played yet',
                'seed': seed,
                'team': team,
            }
            
            print(f"XXXXXXXXXXXX {entrant_player} not found in bookkeeping dict")
        else:
            pp_player = pp_players[pp_players['player'] == entrant_player]
            if not pp_player.empty:
                team = pp_player['team'].values[0]
                res['team'] = team
                entrant_results[entrant_player] = res
    
    return entrant_results

if __name__ == "__main__":
    # Test the function
    entrant_name = "Alex Popof"
    data = get_entrant_data(entrant_name)
    print(data)