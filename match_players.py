import re
import pandas as pd
from espn_to_pp_map import espn_to_pp_map

def get_player_data_from_entry_player(entry_player, bk_dict):
    """
    Get the player data from the entry player string.
    """

    for player, data in bk_dict.items():
        player = player.upper()  # Ensure player names are uppercase
        # Remove punctuation from player names
        player = re.sub(r'[^A-Z\s]', '', player)
        if player in espn_to_pp_map:
            player = espn_to_pp_map[player].upper()

        if player == entry_player:
            return data
    
    raise ValueError(f"Player {entry_player} not found in bookkeeping dict")