import pandas as pd
import json
from constants import TEAMS_ALIVE_MASK
from get_entrant_data import get_entrant_data

def get_multiplier(seed):
    if seed < 6:
        return 1
    elif seed < 13:
        return 2
    else:
        return 3

def create_scoreboard(pikap):
    if pikap:
        pikap_df = pd.read_csv('combined_players.csv') # columns are entrants
        entrants = pikap_df.columns.tolist()
        
        combined_data = {}
        for entrant in entrants:
            entrant_data = get_entrant_data(entrant, pikap=True)
            combined_data[entrant] = entrant_data
        
    else:
        nk_df = pd.read_csv('null_kaval_cleaned.csv') # columns are entrants
        entrants = nk_df.columns.tolist()
        
        # Get the player data for each entrant
        combined_data = {}
        for entrant in entrants:
            entrant_data = get_entrant_data(entrant, pikap=False)
            combined_data[entrant] = entrant_data

    # Sum the points for each player
    for entrant, player_data in combined_data.items():
        total_points = 0
        sum_multiplier = 0
        for player, data in player_data.items():
            # Check if the pts_mult is a number
            if isinstance(data['pts_mult'], (int, float)):
                total_points += data['pts_mult']
            
            # Add up the multiplier points based on the seeds if the team is alive
            if player != 'score' and player != 'sum_multiplier' and data['team'] in TEAMS_ALIVE_MASK and TEAMS_ALIVE_MASK[data['team']] == 1:
                sum_multiplier += get_multiplier(int(data['seed']))
                
        combined_data[entrant]['score'] = total_points
        combined_data[entrant]['sum_multiplier'] = sum_multiplier

        # Sum the number of players alive for each entrant
        alive_count = 0
        for player, data in player_data.items():
            print(f"Checking player: {player}, data: {data}")
            if player != 'score' and player != 'sum_multiplier' and data['team'] in TEAMS_ALIVE_MASK and TEAMS_ALIVE_MASK[data['team']] == 1:
                alive_count += 1

        # Sum estimated games left for each player's team times multiplier
        team_games_projection_df = pd.read_csv('team_games_played_r32_projection.csv')
        sum_games_projected = 0
        sum_games_projected_multiplier = 0
        for player, data in player_data.items():
            if player != 'score' and player != 'sum_multiplier' and data['team'] in TEAMS_ALIVE_MASK and TEAMS_ALIVE_MASK[data['team']] == 1:
                team = data['team']
                seed = int(data['seed'])
                games_played_proj = team_games_projection_df.loc[team_games_projection_df['team'] == team, 'Games Played'].values[0]
                games_played_proj_multiplier = get_multiplier(seed) * games_played_proj
                sum_games_projected += games_played_proj
                sum_games_projected_multiplier += games_played_proj_multiplier
                print(f"Team: {team}, Seed: {seed}, Games Played Projection: {games_played_proj}, Multiplier: {get_multiplier(seed)}, Sum Games Projected: {sum_games_projected}")

        combined_data[entrant]['alive_count'] = alive_count
        combined_data[entrant]['sum_games_projected'] = sum_games_projected
        combined_data[entrant]['sum_games_projected_multiplier'] = sum_games_projected_multiplier

    return combined_data

if __name__ == "__main__":
    # Example usage
    scoreboard = create_scoreboard(pikap=True)['weintraub']
    print(json.dumps(scoreboard, indent=2))