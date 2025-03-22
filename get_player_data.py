def get_player_data(player_name):
    """
    Returns the player data for a specific player.
    """
    try:
        # Load the JSON file
        with open(JSON_FILE_PATH, 'r') as f:
            data = json.load(f)
        
        # Check if the player exists in the data
        if player_name in data:
            return data[player_name]
        else:
            return None
    except FileNotFoundError:
        print("File not found. Please check the file path.")
        return None
    except json.JSONDecodeError:
        print("Error decoding JSON. Please check the file format.")
        return None