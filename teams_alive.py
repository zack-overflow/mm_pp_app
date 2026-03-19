import json
import os

from constants import TEAMS_ALIVE_MASK_JSON_FILE_PATH, DEFAULT_TEAMS_ALIVE_MASK

def get_teams_alive_mask():
    """
    Return teams-alive mask.

    Starts with static defaults and, if present, overlays values from
    the live JSON file written by the scraper.
    """
    mask = dict(DEFAULT_TEAMS_ALIVE_MASK)
    if not os.path.exists(TEAMS_ALIVE_MASK_JSON_FILE_PATH):
        return mask

    try:
        with open(TEAMS_ALIVE_MASK_JSON_FILE_PATH, "r") as f:
            file_mask = json.load(f)

        for team, alive in file_mask.items():
            mask[team] = 1 if str(alive) == "1" else 0
    except (ValueError, TypeError, OSError, json.JSONDecodeError):
        pass

    return mask


def is_team_alive(team_name):
    if not team_name:
        return False
    return get_teams_alive_mask().get(team_name, 0) == 1
