import json
import pandas as pd
from constants import JSON_FILE_PATH

def find_top_players(N=15):
    # Load the data from the JSON file
    with open(JSON_FILE_PATH, 'r') as f:
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

def perfect_bracket():
    """
    Returns a dataframe with the top N players in the competition and the entrants that picked them
    """
    N = 15

    # :pad the top players list
    top_players_df = find_top_players(N)

    # Add column for entrants
    top_players_df['entrants'] = ''

    df = pd.read_csv('combined_players.csv') # columns are entrants
    pp_players = pd.read_csv('pp_players_form2025.csv')
    pp_players = pp_players[['firstName', 'lastName', 'pts_std', 'seed', 'team']]
    # combine first and last name to create full player name
    pp_players['player'] = pp_players['firstName'].str.upper() + ' ' + pp_players['lastName'].str.upper()
    # make names uppercase and remove punctuation
    pp_players['player'] = pp_players['player'].str.replace(r'[^A-Z\s]', '', regex=True)

    df_pikap = pd.read_csv('combined_players.csv') # columns are entrants
    for entrant_name in df_pikap.columns:
        entrant_players = df[entrant_name].tolist()
        # If the entrant players are in the top players df, add them to a column that lists that
        for i, row in top_players_df.iterrows():
            if row['player'] in entrant_players:
                # If the player is in the entrant players, add the entrant name to the column
                if top_players_df.at[i, 'entrants'] == '':
                    top_players_df.at[i, 'entrants'] = entrant_name
                else:
                    top_players_df.at[i, 'entrants'] += ', ' + entrant_name

    # Remove any trailing commas
    top_players_df['entrants'] = top_players_df['entrants'].str.strip(', ')

    print(top_players_df)
    
    # Change to data structure rhat can be sent to frontend
    print(top_players_df)
    top_players_dict = top_players_df.to_dict(orient='records')

    return top_players_dict


if __name__ == "__main__":
    # Test the function
    print(find_top_players())
    print(perfect_bracket())