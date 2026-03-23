def get_player_data_from_entry_player(entry_player, bk_dict):
    """
    Get the player data from the entry player string.
    """
    lookup_name = str(entry_player).strip().upper()
    matches = []

    for player, data in bk_dict.items():
        key_name = str(player).strip().upper()
        stored_name = str(data.get("player", player)).strip().upper()
        if key_name == lookup_name or stored_name == lookup_name:
            matches.append(data)

    if len(matches) == 1:
        return matches[0]
    if matches:
        return matches[0]
    
    # raise ValueError(f"Player {entry_player} not found in bookkeeping dict")
    print(f"XXXXXXXXXXXX {lookup_name} not found in bookkeeping dict")
    return None
