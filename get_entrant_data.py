import json
import pandas as pd
from get_player_data_from_entry_player import get_player_data_from_entry_player
from constants import (
    PLAYER_SCORING_DATA_JSON_FILE_PATH,
    ENTRIES_FILE_PATH,
    PK_ENTRIES_FILE_PATH,
)
from teams_alive import is_team_alive
from teams_in_progress import is_team_in_progress


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
    with open(PLAYER_SCORING_DATA_JSON_FILE_PATH, 'r') as f:
        player_data = json.load(f)

    # Load entrant picks from entry JSON files (null_kaval_entries style)
    entries_path = PK_ENTRIES_FILE_PATH if pikap else ENTRIES_FILE_PATH
    with open(entries_path, 'r') as f:
        entries_data = json.load(f)

    if entrant_name not in entries_data:
        raise KeyError(f"Entrant '{entrant_name}' not found in {entries_path}")

    entrant_players = entries_data[entrant_name].get('picks', [])
    print(entrant_players)

    # Metadata fallback for players not yet in bookkeeping JSON
    espn_players = pd.read_csv('espn_players_2026.csv')[['player_name', 'team_name', 'seed']]
    espn_players['player_name'] = espn_players['player_name'].astype(str).str.strip().str.upper()
    player_meta = {
        row['player_name']: {
            'team': row['team_name'],
            'seed': int(row['seed'])
        }
        for _, row in espn_players.iterrows()
    }

    # Grab data for the enrant's players
    entrant_results = {}
    for entrant_player in entrant_players:
        lookup_name = str(entrant_player).strip().upper()
        if not lookup_name:
            continue

        res = get_player_data_from_entry_player(lookup_name, player_data)
        # if result is None, put a false entry in the dict

        if res is None:
            meta = player_meta.get(lookup_name, {})
            seed = meta.get('seed', 'Not found')
            team = meta.get('team', 'Not found')
            
            entrant_results[lookup_name] = {
                'pts': 'Not played yet',
                'pts_mult': 'Not played yet',
                'seed': seed,
                'team': team,
                'alive': is_team_alive(team),
                'in_progress': is_team_in_progress(team),
            }
            
            print(f"XXXXXXXXXXXX {lookup_name} not found in bookkeeping dict")
        else:
            entrant_row = dict(res)
            # Use team from bookkeeping when present, otherwise fallback to ESPN player list.
            team = entrant_row.get('team') or player_meta.get(lookup_name, {}).get('team')
            if team is not None:
                entrant_row['team'] = team
            entrant_row['alive'] = is_team_alive(team)
            entrant_row['in_progress'] = is_team_in_progress(team)
            entrant_results[lookup_name] = entrant_row
    
    return entrant_results

if __name__ == "__main__":
    # Test the function
    entrant_name = "Jimmy Porter"
    data = get_entrant_data(entrant_name, pikap=False)
    print(data)