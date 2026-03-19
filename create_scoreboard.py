import json
from constants import TEAMS_ALIVE_MASK, ENTRIES_FILE_PATH, PK_ENTRIES_FILE_PATH
from get_entrant_data import get_entrant_data

def get_multiplier(seed):
    if seed < 6:
        return 1
    elif seed < 13:
        return 2
    else:
        return 3

def create_scoreboard(pikap):
    entries_path = PK_ENTRIES_FILE_PATH if pikap else ENTRIES_FILE_PATH
    with open(entries_path, 'r') as f:
        entries_data = json.load(f)

    entrants = list(entries_data.keys())

    combined_data = {}
    for entrant in entrants:
        entrant_data = get_entrant_data(entrant, pikap=pikap)
        combined_data[entrant] = entrant_data

    # Sum the points for each player
    for entrant, player_data in combined_data.items():
        total_points = 0
        sum_multiplier = 0
        for player, data in player_data.items():
            if not isinstance(data, dict):
                continue
            # Check if the pts_mult is a number
            pts_mult = data.get('pts_mult')
            if isinstance(pts_mult, (int, float)):
                total_points += pts_mult
            
            # Add up the multiplier points based on the seeds if the team is alive
            team = data.get('team')
            if TEAMS_ALIVE_MASK.get(team, 0) == 1:
                try:
                    sum_multiplier += get_multiplier(int(data.get('seed')))
                except (TypeError, ValueError):
                    pass
                
        combined_data[entrant]['score'] = total_points
        combined_data[entrant]['sum_multiplier'] = sum_multiplier

        # Sum the number of players alive for each entrant
        alive_count = 0
        for player, data in player_data.items():
            if not isinstance(data, dict):
                continue
            if TEAMS_ALIVE_MASK.get(data.get('team'), 0) == 1:
                alive_count += 1

        combined_data[entrant]['alive_count'] = alive_count

    print(combined_data)
    return combined_data

if __name__ == "__main__":
    # Example usage
    scoreboard = create_scoreboard(pikap=False)
    print(json.dumps(scoreboard, indent=2))