from __future__ import annotations

import math
import pickle
import re
import time
from copy import deepcopy
from dataclasses import dataclass

import numpy as np

from .bracket import GameNode, TeamRef
import csv

from .config import KENPOM_RATINGS_PATH, PLAYER_DATA_PATH, SILVER_RATINGS_PATH, TEAM_RATINGS_PATH
from .names import resolve_matchup_to_barttorvik, resolve_matchup_to_kenpom, resolve_matchup_to_silver


@dataclass
class Team:
    team_name: str
    seed: int

    def get_multiplier(self) -> int:
        if self.seed < 6:
            return 1
        if self.seed < 13:
            return 2
        return 3


def load_kenpom_ratings(path=KENPOM_RATINGS_PATH) -> dict[str, float]:
    ratings = {}
    with open(path, "r") as f:
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) < 5 or not parts[0].isdigit():
                continue
            team_name = re.sub(r" \d{1,2}\*?$", "", parts[1].strip())
            rating_text = parts[4].replace("+", "")
            ratings[team_name] = float(rating_text)
    return ratings


def load_silver_ratings(path=SILVER_RATINGS_PATH) -> dict[str, float]:
    ratings = {}
    with open(path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ratings[row["sb_name"].strip()] = float(row["adjusted_composite"])
    return ratings


def load_player_data(path=PLAYER_DATA_PATH):
    with open(path, "rb") as f:
        return pickle.load(f)


def load_team_ratings(path=TEAM_RATINGS_PATH):
    with open(path, "rb") as f:
        return pickle.load(f)


def _normal_cdf(value: float) -> float:
    return 0.5 * (1.0 + math.erf(value / math.sqrt(2.0)))


def _win_probability_kenpom(team1_name: str, team2_name: str, ratings_lookup: dict[str, float]) -> float:
    available_names = set(ratings_lookup.keys())
    team1_rating = ratings_lookup[resolve_matchup_to_kenpom(team1_name, available_names)]
    team2_rating = ratings_lookup[resolve_matchup_to_kenpom(team2_name, available_names)]
    return _normal_cdf((team1_rating - team2_rating) / 11.0)


def _win_probability_silver(team1_name: str, team2_name: str, ratings_lookup: dict[str, float]) -> float:
    available_names = set(ratings_lookup.keys())
    r1 = ratings_lookup[resolve_matchup_to_silver(team1_name, available_names)]
    r2 = ratings_lookup[resolve_matchup_to_silver(team2_name, available_names)]
    return 1.0 / (1.0 + 10.0 ** (-(r1 - r2) / 400.0))


def _win_probability(team1_name: str, team2_name: str, ratings_lookup: dict[str, float], model: str = "silver") -> float:
    if model == "silver":
        return _win_probability_silver(team1_name, team2_name, ratings_lookup)
    return _win_probability_kenpom(team1_name, team2_name, ratings_lookup)


def _simulate_game(team1: Team, team2: Team, ratings_lookup: dict[str, float], model: str = "silver") -> Team:
    return team1 if np.random.random() < _win_probability(team1.team_name, team2.team_name, ratings_lookup, model) else team2


def _simulate_player_points(player_ppg, gamma_params=None, tempo_factor=1.0, def_factor=1.0) -> float:
    if gamma_params is not None:
        shape, _loc, scale = gamma_params
        return float(np.random.gamma(shape, scale) * tempo_factor * def_factor)

    if not player_ppg:
        return 0.0

    variance = max(float(player_ppg) / 5.0, 1e-6)
    return float(max(0.0, np.random.normal(float(player_ppg), variance)))


def _handle_player_bookkeeping_for_team(
    player_bk_dict: dict,
    team_ref: Team,
    opponent_team: Team,
    team_maps: dict[str, dict[str, str]],
    team_ratings: dict,
) -> None:
    team_dict = player_bk_dict.get(team_ref.team_name)
    if not team_dict:
        return

    meta = team_ratings.get("_meta", {})
    avg_tempo = meta.get("avg_tempo", 1.0)
    avg_de = meta.get("avg_de", 1.0)
    available_torvik_names = {name for name in team_ratings if name != "_meta"}

    tempo_factor = 1.0
    def_factor = 1.0

    try:
        team_torvik = resolve_matchup_to_barttorvik(team_ref.team_name, team_maps, available_torvik_names)
        opp_torvik = resolve_matchup_to_barttorvik(opponent_team.team_name, team_maps, available_torvik_names)
    except KeyError:
        team_torvik = None
        opp_torvik = None

    if team_torvik and opp_torvik:
        team_tempo = team_ratings[team_torvik]["tempo"]
        opp_tempo = team_ratings[opp_torvik]["tempo"]
        opp_de = team_ratings[opp_torvik]["adj_de"]
        expected_pace = (team_tempo * opp_tempo) / avg_tempo
        tempo_factor = expected_pace / avg_tempo
        def_factor = opp_de / avg_de

    multiplier = team_ref.get_multiplier()

    for stats in team_dict.values():
        increment = _simulate_player_points(
            stats.get("ppg"),
            gamma_params=stats.get("gamma_params"),
            tempo_factor=tempo_factor,
            def_factor=def_factor,
        ) * multiplier
        stats["running_total_simulated"] = float(stats.get("running_total_simulated", 0.0) + increment)


def _resolve_team(ref: TeamRef | GameNode, *args, **kwargs) -> Team:
    if isinstance(ref, TeamRef):
        return Team(ref.name, ref.seed)
    return _simulate_remaining_games(ref, *args, **kwargs)  # model flows through via *args/**kwargs


def _simulate_remaining_games(
    node: GameNode,
    seed_map: dict[str, int],
    ratings_lookup: dict[str, float],
    player_bk_dict: dict,
    team_game_counts: dict[str, int],
    team_maps: dict[str, dict[str, str]],
    team_ratings: dict,
    model: str = "silver",
) -> Team:
    # Already-played real games: points are in the scoring data, skip entirely
    if node.locked_winner and not node.forced:
        return Team(node.locked_winner, seed_map[node.locked_winner])

    team1 = _resolve_team(node.left, seed_map, ratings_lookup, player_bk_dict, team_game_counts, team_maps, team_ratings, model)
    team2 = _resolve_team(node.right, seed_map, ratings_lookup, player_bk_dict, team_game_counts, team_maps, team_ratings, model)

    # Forced what-if games: use the forced winner but still simulate player points
    if node.forced:
        winner = Team(node.locked_winner, seed_map[node.locked_winner])
    else:
        winner = _simulate_game(team1, team2, ratings_lookup, model)

    team_game_counts[team1.team_name] = team_game_counts.get(team1.team_name, 0) + 1
    team_game_counts[team2.team_name] = team_game_counts.get(team2.team_name, 0) + 1
    _handle_player_bookkeeping_for_team(player_bk_dict, team1, team2, team_maps, team_ratings)
    _handle_player_bookkeeping_for_team(player_bk_dict, team2, team1, team_maps, team_ratings)
    return winner


def simulate_remaining_player_scores(
    bracket_root: GameNode,
    seed_map: dict[str, int],
    ratings_lookup: dict[str, float],
    player_data_template: dict,
    team_maps: dict[str, dict[str, str]],
    team_ratings: dict,
    n_sims: int,
    verbose: bool = False,
    model: str = "silver",
) -> dict[str, dict]:
    player_keys = [
        (team_name, player_name)
        for team_name, roster in player_data_template.items()
        for player_name in roster.keys()
    ]
    player_scores = {key: np.zeros(n_sims, dtype=float) for key in player_keys}
    team_game_count_scores = {
        team_name: np.zeros(n_sims, dtype=int)
        for team_name in player_data_template.keys()
    }
    champion_counts = {}
    progress_step = max(1, n_sims // 25)
    started_at = time.perf_counter()

    for sim_index in range(n_sims):
        player_bk_dict = deepcopy(player_data_template)
        team_game_counts = {team_name: 0 for team_name in player_data_template.keys()}
        for roster in player_bk_dict.values():
            for stats in roster.values():
                stats["running_total_simulated"] = 0.0
        champion = _simulate_remaining_games(
            bracket_root,
            seed_map,
            ratings_lookup,
            player_bk_dict,
            team_game_counts,
            team_maps,
            team_ratings,
            model,
        )
        champion_counts[champion.team_name] = champion_counts.get(champion.team_name, 0) + 1

        for team_name, roster in player_bk_dict.items():
            team_game_count_scores[team_name][sim_index] = int(team_game_counts.get(team_name, 0))
            for player_name, stats in roster.items():
                player_scores[(team_name, player_name)][sim_index] = float(stats.get("running_total_simulated", 0.0))

        if verbose and (sim_index + 1 == n_sims or (sim_index + 1) % progress_step == 0):
            completed = sim_index + 1
            fraction = completed / n_sims
            bar_width = 24
            filled = int(bar_width * fraction)
            bar = "#" * filled + "-" * (bar_width - filled)
            elapsed = time.perf_counter() - started_at
            eta = (elapsed / completed) * (n_sims - completed) if completed else 0.0
            print(
                f"\rSim progress [{bar}] {completed}/{n_sims} "
                f"({fraction:6.1%}) elapsed={elapsed:6.1f}s eta={eta:6.1f}s",
                end="",
                flush=True,
            )

    if verbose:
        print()
        top_champions = sorted(champion_counts.items(), key=lambda item: (-item[1], item[0]))[:8]
        print("Sampled champion frequencies during this run:")
        for team_name, count in top_champions:
            print(f"  {team_name:24s} {count:>4d} ({count / n_sims:6.1%})")

    return {
        "player_scores": player_scores,
        "team_game_counts": team_game_count_scores,
    }
