def get_player_data_from_entry_player(entry_player, bk_dict):
    """
    Get the player data from the entry player string.
    """
    lookup_name = str(entry_player).strip().upper()

    for player, data in bk_dict.items():
        if str(player).strip().upper() == lookup_name:
            return data
    
    # raise ValueError(f"Player {entry_player} not found in bookkeeping dict")
    print(f"XXXXXXXXXXXX {lookup_name} not found in bookkeeping dict")
    return None