import pandas as pd
import json
from constants import JSON_FILE_PATH
from get_entrant_data import get_entrant_data

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
        for player, data in player_data.items():
            total_points += data['pts_mult']
        combined_data[entrant]['score'] = total_points

    return combined_data