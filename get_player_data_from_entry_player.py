import re
import pandas as pd
from espn_to_pp_map import pp_to_espn_map

def get_player_data_from_entry_player(entry_player, bk_dict):
    """
    Get the player data from the entry player string.
    """
    if entry_player in pp_to_espn_map:
        entry_player = pp_to_espn_map[entry_player].upper()

    for player, data in bk_dict.items():
        player = player.upper()  # Ensure player names are uppercase
        # Remove punctuation from player names
        player = re.sub(r'[^A-Z\s]', '', player)

        if player == entry_player:
            return data
    
    # raise ValueError(f"Player {entry_player} not found in bookkeeping dict")
    print(f"XXXXXXXXXXXX {entry_player} not found in bookkeeping dict")
    return {
        'pts': 0,
        'pts_mult': 0,
        'seed': 'Not played yet',
        'team': 'Not played yet',
    }