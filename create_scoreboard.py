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
        combined_data = {}
        combined_data['gotti'] = get_entrant_data('gotti', pikap=False)

    # Sum the points for each player
    for entrant, player_data in combined_data.items():
        total_points = 0
        sum_multiplier = 0
        for player, data in player_data.items():
            # Check if the pts_mult is a number
            if isinstance(data['pts_mult'], (int, float)):
                total_points += data['pts_mult']
            
            # Add up the multiplier points based on the seeds
            sum_multiplier += get_multiplier(int(data['seed']))
                
        combined_data[entrant]['score'] = total_points
        combined_data[entrant]['sum_multiplier'] = sum_multiplier

        # Sum the number of players alive for each entrant
        alive_count = 0
        for player, data in player_data.items():
            if data['team'] in TEAMS_ALIVE_MASK:
                if TEAMS_ALIVE_MASK[data['team']] == 1:
                    alive_count += 1
            else:
                print(f"Warning: {data['team']} not found in TEAMS_ALIVE_MASK")

        combined_data[entrant]['alive_count'] = alive_count

    return combined_data