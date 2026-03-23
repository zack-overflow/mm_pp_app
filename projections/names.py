from __future__ import annotations

import csv
import re
from pathlib import Path

from .config import TEAM_NAME_MAPPING_PATH


PLAYER_NAME_ALIASES = {
    "LABARON PHILON JR": "Labaron Philon",
    "MJ COLLINS JR": "MJ Collins",
    "SOLO BALL": "Solomon Ball",
}

TEAM_NAME_OVERRIDES = {
    "PRAIRIE VIEW": "Prairie View A&M",
}

MATCHUP_TO_SILVER_OVERRIDES = {
    "Iowa State": "Iowa St.",
    "Kennesaw State": "Kennesaw St.",
    "Miami (FL)": "U Miami (FL)",
    "Miami (OH)": "Miami University (OH)",
    "Michigan State": "Michigan St.",
    "North Dakota State": "North Dakota St.",
    "Ohio State": "Ohio St.",
    "Queens (NC)": "Queens",
    "Saint Mary's": "Saint Mary's (CA)",
    "St. John's (NY)": "St. John's",
    "Tennessee State": "Tennessee St.",
    "UNC": "North Carolina",
    "Utah State": "Utah St.",
    "Wright State": "Wright St.",
}

MATCHUP_TO_KENPOM_OVERRIDES = {
    "California Baptist": "Cal Baptist",
    "Iowa State": "Iowa St.",
    "Kennesaw State": "Kennesaw St.",
    "McNeese": "McNeese St.",
    "Miami (FL)": "Miami FL",
    "Miami (OH)": "Miami OH",
    "Michigan State": "Michigan St.",
    "North Dakota State": "North Dakota St.",
    "Ohio State": "Ohio St.",
    "Queens (NC)": "Queens",
    "St. John's (NY)": "St. John's",
    "Tennessee State": "Tennessee St.",
    "UConn": "Connecticut",
    "UNC": "North Carolina",
    "Utah State": "Utah St.",
    "Wright State": "Wright St.",
}


def normalize_name(value: str | None) -> str:
    if value is None:
        return ""
    text = str(value).upper()
    text = text.replace("&", " AND ")
    text = text.replace(".", " ")
    text = text.replace("'", "")
    text = text.replace("-", " ")
    text = re.sub(r"\s*\([^)]+\)", " ", text)
    text = re.sub(r"[^A-Z0-9 ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def normalize_player_name(value: str | None) -> str:
    return normalize_name(value)


def normalize_team_name(value: str | None) -> str:
    return normalize_name(value)


def alias_player_name(value: str) -> str:
    alias = PLAYER_NAME_ALIASES.get(normalize_player_name(value))
    return alias or value


def _resolve_to_available(name: str, available_names: set[str], overrides: dict[str, str] | None = None) -> str:
    if name in available_names:
        return name

    overrides = overrides or {}
    override = overrides.get(name)
    if override and override in available_names:
        return override

    normalized_lookup = {normalize_name(candidate): candidate for candidate in available_names}

    direct = normalized_lookup.get(normalize_name(name))
    if direct:
        return direct

    if override:
        normalized_override = normalized_lookup.get(normalize_name(override))
        if normalized_override:
            return normalized_override

    raise KeyError(f"Could not resolve name '{name}'")


def load_team_name_maps(path: Path | None = None) -> dict[str, dict[str, str]]:
    path = path or TEAM_NAME_MAPPING_PATH

    matchup_to_barttorvik = {}
    matchup_to_espn = {}
    espn_to_matchup = {}

    with open(path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            matchup_name = row["matchup_tree"].strip()
            barttorvik_name = row["barttorvik"].strip() or matchup_name
            espn_name = row["espn"].strip() or matchup_name

            matchup_to_barttorvik[matchup_name] = barttorvik_name
            matchup_to_espn[matchup_name] = espn_name
            espn_to_matchup[espn_name] = matchup_name

    for source_name, target_name in TEAM_NAME_OVERRIDES.items():
        espn_to_matchup[source_name] = target_name

    return {
        "matchup_to_barttorvik": matchup_to_barttorvik,
        "matchup_to_espn": matchup_to_espn,
        "espn_to_matchup": espn_to_matchup,
    }


def map_espn_team_to_matchup(team_name: str, team_maps: dict[str, dict[str, str]]) -> str:
    available_names = set(team_maps["espn_to_matchup"].keys())
    resolved_source = _resolve_to_available(team_name, available_names, TEAM_NAME_OVERRIDES)
    return team_maps["espn_to_matchup"][resolved_source]


def resolve_matchup_to_barttorvik(team_name: str, team_maps: dict[str, dict[str, str]], available_names: set[str]) -> str:
    preferred = team_maps["matchup_to_barttorvik"].get(team_name, team_name)
    return _resolve_to_available(preferred, available_names)


def resolve_matchup_to_kenpom(team_name: str, available_names: set[str]) -> str:
    return _resolve_to_available(team_name, available_names, MATCHUP_TO_KENPOM_OVERRIDES)


def resolve_matchup_to_silver(team_name: str, available_names: set[str]) -> str:
    return _resolve_to_available(team_name, available_names, MATCHUP_TO_SILVER_OVERRIDES)


def build_player_sim_index(player_data: dict) -> dict[tuple[str, str], tuple[str, str]]:
    index = {}
    for team_name, roster in player_data.items():
        team_key = normalize_team_name(team_name)
        for player_name in roster:
            player_key = normalize_player_name(player_name)
            index[(team_key, player_key)] = (team_name, player_name)
    return index


def resolve_pick_to_sim_key(
    pick_name: str,
    player_meta: dict | None,
    team_maps: dict[str, dict[str, str]],
    player_index: dict[tuple[str, str], tuple[str, str]],
) -> tuple[str, str] | None:
    if not player_meta:
        return None

    try:
        matchup_team = map_espn_team_to_matchup(player_meta["team"], team_maps)
    except KeyError:
        return None

    team_key = normalize_team_name(matchup_team)

    player_candidates = [pick_name, alias_player_name(pick_name)]
    for candidate in player_candidates:
        resolved = player_index.get((team_key, normalize_player_name(candidate)))
        if resolved:
            return resolved

    return None
