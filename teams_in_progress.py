import json
import os

from constants import TEAM_IN_PROGRESS_MASK_JSON_FILE_PATH


def get_team_in_progress_mask():
    """Return team in-progress mask loaded from persisted scraper output."""
    if not os.path.exists(TEAM_IN_PROGRESS_MASK_JSON_FILE_PATH):
        return {}

    try:
        with open(TEAM_IN_PROGRESS_MASK_JSON_FILE_PATH, "r") as f:
            file_mask = json.load(f)
    except (ValueError, TypeError, OSError, json.JSONDecodeError):
        return {}

    normalized = {}
    for team, in_progress in file_mask.items():
        normalized[team] = 1 if str(in_progress) == "1" else 0
    return normalized


def is_team_in_progress(team_name):
    if not team_name:
        return False
    return get_team_in_progress_mask().get(team_name, 0) == 1
