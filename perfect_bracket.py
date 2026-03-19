import json
import pandas as pd
from constants import PLAYER_SCORING_DATA_JSON_FILE_PATH, ENTRIES_FILE_PATH, PK_ENTRIES_FILE_PATH

def find_top_players(N=15):
    # Load the data from the JSON file
    with open(PLAYER_SCORING_DATA_JSON_FILE_PATH, 'r') as f:
        player_data = json.load(f)

    # Create a list to hold the player data
    players_list = []
    for player, data in player_data.items():
        # Check if the player is in the top N
        if data['pts_mult'] > 0:
            # Add the player to the list
            players_list.append({
                'player': player,
                'pts_mult': data['pts_mult'],
                'team': data['team']
            })
            
    # Create DataFrame from the list
    top_players = pd.DataFrame(players_list)
    
    # If any players were found, sort and limit to top N
    if not top_players.empty:
        # Sort the players by points multiplier
        top_players = top_players.sort_values(by='pts_mult', ascending=False)
        # Select the top N players
        top_players = top_players.head(N)

    return top_players.reset_index(drop=True)

def perfect_bracket(pikap=True):
    """
    Returns a dataframe with the top N players in the competition and the entrants that picked them
    """
    N = 30

    # :pad the top players list
    top_players_df = find_top_players(N)

    # Add column for entrants
    top_players_df['entrants'] = ''

    # Load entrant picks from entry JSON files (null_kaval_entries style).
    entries_path = PK_ENTRIES_FILE_PATH if pikap else ENTRIES_FILE_PATH
    with open(entries_path, 'r') as f:
        entries_data = json.load(f)

    top_players_norm = {
        str(player).strip().upper()
        for player in top_players_df['player'].tolist()
    }
    player_to_entrants = {player: [] for player in top_players_norm}

    for entrant_name, entrant_data in entries_data.items():
        picks = entrant_data.get('picks', [])
        normalized_picks = {
            str(pick).strip().upper()
            for pick in picks
            if str(pick).strip()
        }
        for player in normalized_picks.intersection(top_players_norm):
            player_to_entrants[player].append(entrant_name)

    for i, row in top_players_df.iterrows():
        lookup_name = str(row['player']).strip().upper()
        top_players_df.at[i, 'entrants'] = ', '.join(player_to_entrants.get(lookup_name, []))

    # Remove any trailing commas
    top_players_df['entrants'] = top_players_df['entrants'].str.strip(', ')

    # Change to data structure that can be sent to frontend
    top_players_dict = top_players_df.to_dict(orient='records')

    return top_players_dict


if __name__ == "__main__":
    # Test the function
    print(find_top_players())
    print(perfect_bracket())
