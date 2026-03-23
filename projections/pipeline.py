from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone

import numpy as np

from .bracket import apply_forced_winners, build_locked_bracket, format_bracket_status, serialize_bracket_to_json
from .config import DEFAULT_CADENCE_MINUTES, DEFAULT_N_SIMS
from .names import (
    build_player_sim_index,
    load_team_name_maps,
    map_espn_team_to_matchup,
    normalize_player_name,
    resolve_matchup_to_kenpom,
    resolve_matchup_to_silver,
    resolve_pick_to_sim_key,
)
from .ranking import compute_finish_probabilities
from .simulation import (
    load_kenpom_ratings,
    load_player_data,
    load_silver_ratings,
    load_team_ratings,
    simulate_remaining_player_scores,
)


def _numeric_points(value) -> float:
    return float(value) if isinstance(value, (int, float)) else 0.0


def _build_seed_map(team_seed_map: dict[str, int], team_maps: dict[str, dict[str, str]]) -> dict[str, int]:
    seed_map = {}
    for site_team_name, seed in team_seed_map.items():
        try:
            matchup_team = map_espn_team_to_matchup(site_team_name, team_maps)
        except KeyError:
            continue
        seed_map[matchup_team] = int(seed)
    return seed_map


def _build_live_team_state(
    player_scoring_data: dict,
    teams_alive_mask: dict[str, int],
    seed_map: dict[str, int],
    team_maps: dict[str, dict[str, str]],
) -> tuple[dict[str, int], dict[str, list[float]], dict[str, int]]:
    games_played = defaultdict(int)
    team_round_scores = defaultdict(list)
    matchup_alive_mask = {}

    for player_info in player_scoring_data.values():
        site_team_name = player_info.get("team")
        if not site_team_name:
            continue
        try:
            matchup_team = map_espn_team_to_matchup(site_team_name, team_maps)
        except KeyError:
            continue
        games_played[matchup_team] = max(games_played[matchup_team], len(player_info.get("pts", [])))
        while len(team_round_scores[matchup_team]) < len(player_info.get("pts", [])):
            team_round_scores[matchup_team].append(0.0)
        for index, pts in enumerate(player_info.get("pts", [])):
            team_round_scores[matchup_team][index] += _numeric_points(pts)

    for site_team_name, alive in teams_alive_mask.items():
        try:
            matchup_team = map_espn_team_to_matchup(site_team_name, team_maps)
        except KeyError:
            continue
        matchup_alive_mask[matchup_team] = 1 if str(alive) == "1" else 0

    for team_name in seed_map:
        games_played.setdefault(team_name, 0)
        team_round_scores.setdefault(team_name, [])
        matchup_alive_mask.setdefault(team_name, 0)

    return dict(games_played), dict(team_round_scores), matchup_alive_mask


def _build_player_catalog(raw_catalog: dict) -> dict[str, dict]:
    return {str(name).strip().upper(): value for name, value in raw_catalog.items()}


def _build_player_scoring_lookup(raw_scoring_data: dict) -> dict[str, dict]:
    by_name_team = {}
    by_name_unique = {}
    duplicate_names = set()

    for raw_key, row in raw_scoring_data.items():
        player_name = normalize_player_name(row.get("player") or raw_key)
        team_name = str(row.get("team") or "").strip()
        by_name_team[(player_name, team_name)] = row
        if player_name in by_name_unique:
            duplicate_names.add(player_name)
        else:
            by_name_unique[player_name] = row

    for player_name in duplicate_names:
        by_name_unique.pop(player_name, None)

    return {
        "by_name_team": by_name_team,
        "by_name_unique": by_name_unique,
    }


def _lookup_player_scoring_row(scoring_lookup: dict[str, dict], pick_name: str, player_meta: dict | None) -> dict | None:
    player_lookup = normalize_player_name(pick_name)
    if player_meta:
        team_name = str(player_meta.get("team") or "").strip()
        if team_name:
            row = scoring_lookup["by_name_team"].get((player_lookup, team_name))
            if row is not None:
                return row
    return scoring_lookup["by_name_unique"].get(player_lookup)


def _summarize_scores(values: np.ndarray) -> dict[str, float]:
    return {
        "mean": float(np.mean(values)),
        "median": float(np.median(values)),
        "p10": float(np.percentile(values, 10)),
        "p90": float(np.percentile(values, 90)),
    }


def _summarize_game_counts(values: np.ndarray) -> list[dict[str, float]]:
    counts, frequencies = np.unique(values.astype(int), return_counts=True)
    total = max(int(np.sum(frequencies)), 1)
    return [
        {
            "games": int(count),
            "probability": float(frequency / total),
        }
        for count, frequency in zip(counts, frequencies)
    ]


def _print_input_summary(entries: dict, player_scoring_data: dict, teams_alive_mask: dict[str, int]) -> None:
    total_picks = sum(len(entry.get("picks", [])) for entry in entries.values())
    scored_players = sum(1 for info in player_scoring_data.values() if _numeric_points(info.get("pts_mult")) > 0)
    alive_teams = sum(1 for alive in teams_alive_mask.values() if str(alive) == "1")
    eliminated_teams = sum(1 for alive in teams_alive_mask.values() if str(alive) != "1")

    print("Projection input summary:")
    print(f"  entrants:           {len(entries)}")
    print(f"  total picks:        {total_picks}")
    print(f"  scored players:     {scored_players}")
    print(f"  alive teams:        {alive_teams}")
    print(f"  eliminated teams:   {eliminated_teams}")


def _print_projection_summary(snapshot: dict) -> None:
    print("Top projected entrants:")
    for row in snapshot["entrant_projections"][:10]:
        print(
            f"  {row['entrant'][:24]:24s} "
            f"current={row['current_score']:6.1f} "
            f"remaining={row['projected_remaining_mean']:6.1f} "
            f"final={row['projected_total_mean']:6.1f} "
            f"win={row['win_probability']:6.1%} "
            f"top3={row['top3_probability']:6.1%}"
        )


def build_bracket_snapshot(projection_inputs: dict) -> dict:
    player_scoring_data = projection_inputs["player_scoring_data"]
    projection_player_scoring_data = projection_inputs.get("projection_player_scoring_data") or player_scoring_data
    teams_alive_mask = projection_inputs["teams_alive_mask"]
    team_seed_map = projection_inputs["team_seed_map"]

    team_maps = load_team_name_maps()
    seed_map = _build_seed_map(team_seed_map, team_maps)
    games_played, team_round_scores, alive_map = _build_live_team_state(
        projection_player_scoring_data,
        teams_alive_mask,
        seed_map,
        team_maps,
    )

    bracket_root = build_locked_bracket(
        seed_map,
        games_played,
        team_round_scores,
        teams_alive_mask=alive_map,
    )

    kenpom_ratings = load_kenpom_ratings()
    available_kenpom_names = set(kenpom_ratings.keys())
    matchup_kenpom = {}
    for matchup_name in seed_map:
        try:
            kenpom_name = resolve_matchup_to_kenpom(matchup_name, available_kenpom_names)
            matchup_kenpom[matchup_name] = kenpom_ratings[kenpom_name]
        except KeyError:
            pass

    silver_ratings = load_silver_ratings()
    available_silver_names = set(silver_ratings.keys())
    matchup_silver = {}
    for matchup_name in seed_map:
        try:
            silver_name = resolve_matchup_to_silver(matchup_name, available_silver_names)
            matchup_silver[matchup_name] = silver_ratings[silver_name]
        except KeyError:
            pass

    return {
        "bracket": serialize_bracket_to_json(bracket_root),
        "ratings": matchup_kenpom,
        "silver_ratings": matchup_silver,
        "seed_map": seed_map,
    }


def build_projection_snapshot(
    projection_inputs: dict,
    generated_at: str | None = None,
    n_sims: int = DEFAULT_N_SIMS,
    cadence_minutes: int = DEFAULT_CADENCE_MINUTES,
    verbose: bool = False,
    forced_winners: dict[str, str] | None = None,
    model: str = "silver",
) -> dict:
    generated_at = generated_at or datetime.now(timezone.utc).isoformat()

    entries = projection_inputs["entries"]
    player_scoring_data = projection_inputs["player_scoring_data"]
    projection_player_scoring_data = projection_inputs.get("projection_player_scoring_data") or player_scoring_data
    teams_alive_mask = projection_inputs["teams_alive_mask"]
    player_catalog = _build_player_catalog(projection_inputs["player_catalog"])
    scoring_lookup = _build_player_scoring_lookup(projection_player_scoring_data)
    team_seed_map = projection_inputs["team_seed_map"]

    if verbose:
        _print_input_summary(entries, projection_player_scoring_data, teams_alive_mask)

    team_maps = load_team_name_maps()
    seed_map = _build_seed_map(team_seed_map, team_maps)
    games_played, team_round_scores, _alive_map = _build_live_team_state(
        projection_player_scoring_data,
        teams_alive_mask,
        seed_map,
        team_maps,
    )

    bracket_root = build_locked_bracket(
        seed_map,
        games_played,
        team_round_scores,
        teams_alive_mask=_alive_map,
    )
    if forced_winners:
        apply_forced_winners(bracket_root, forced_winners)
    if verbose:
        print("Bracket state inferred from current site data:")
        print(format_bracket_status(bracket_root))
    if model == "silver":
        ratings_lookup = load_silver_ratings()
    else:
        ratings_lookup = load_kenpom_ratings()
    player_data = load_player_data()
    team_ratings = load_team_ratings()

    player_index = build_player_sim_index(player_data)
    simulation_results = simulate_remaining_player_scores(
        bracket_root=bracket_root,
        seed_map=seed_map,
        ratings_lookup=ratings_lookup,
        player_data_template=player_data,
        team_maps=team_maps,
        team_ratings=team_ratings,
        n_sims=n_sims,
        verbose=verbose,
        model=model,
    )
    simulated_remaining_scores = simulation_results["player_scores"]
    simulated_team_game_counts = simulation_results["team_game_counts"]

    entrant_rows = []
    total_picks = 0
    matched_picks = 0
    unresolved_players_global = set()

    for entrant_name, entrant_info in entries.items():
        picks = entrant_info.get("picks", [])
        total_picks += len(picks)

        current_score = 0.0
        alive_count = 0
        unresolved_players = []
        matched_pick_count = 0
        projected_arrays = []
        player_projection_rows = []

        for pick_name in picks:
            player_lookup = str(pick_name).strip().upper()
            player_meta = player_catalog.get(player_lookup)
            scoring_row = _lookup_player_scoring_row(scoring_lookup, pick_name, player_meta)
            current_points = _numeric_points((scoring_row or {}).get("pts_mult"))
            current_score += current_points

            alive = bool(player_meta and str(teams_alive_mask.get(player_meta["team"], 0)) == "1")

            sim_key = resolve_pick_to_sim_key(
                pick_name=pick_name,
                player_meta=player_meta,
                team_maps=team_maps,
                player_index=player_index,
            )

            if sim_key and sim_key in simulated_remaining_scores:
                matched_pick_count += 1
                projected_remaining_scores = simulated_remaining_scores[sim_key]
                projected_game_counts = simulated_team_game_counts.get(
                    sim_key[0],
                    np.zeros(n_sims, dtype=int),
                )
                projected_arrays.append(projected_remaining_scores)
                unresolved = False
            else:
                unresolved_players.append(pick_name)
                unresolved_players_global.add(pick_name)
                projected_remaining_scores = np.zeros(n_sims, dtype=float)
                projected_game_counts = np.zeros(n_sims, dtype=int)
                unresolved = True

            if alive:
                alive_count += 1

            projected_total_scores = projected_remaining_scores + current_points
            remaining_summary = _summarize_scores(projected_remaining_scores)
            total_summary = _summarize_scores(projected_total_scores)
            games_distribution = _summarize_game_counts(projected_game_counts)
            player_projection_rows.append(
                {
                    "player": pick_name,
                    "team": player_meta["team"] if player_meta else "",
                    "seed": player_meta["seed"] if player_meta else "",
                    "alive": alive,
                    "current_points": float(current_points),
                    "projected_remaining_mean": remaining_summary["mean"],
                    "projected_remaining_median": remaining_summary["median"],
                    "projected_remaining_p10": remaining_summary["p10"],
                    "projected_remaining_p90": remaining_summary["p90"],
                    "projected_total_mean": total_summary["mean"],
                    "projected_total_median": total_summary["median"],
                    "projected_total_p10": total_summary["p10"],
                    "projected_total_p90": total_summary["p90"],
                    "remaining_games_distribution": games_distribution,
                    "unresolved": unresolved,
                }
            )

        matched_picks += matched_pick_count

        projected_remaining = (
            np.sum(projected_arrays, axis=0) if projected_arrays else np.zeros(n_sims, dtype=float)
        )
        projected_total = projected_remaining + current_score

        entrant_rows.append(
            {
                "entrant": entrant_name,
                "current_score": float(current_score),
                "alive_count": int(alive_count),
                "matched_picks": int(matched_pick_count),
                "total_picks": len(picks),
                "unresolved_players": unresolved_players,
                "player_projections": sorted(
                    player_projection_rows,
                    key=lambda row: (-row["projected_total_mean"], -row["current_points"], row["player"]),
                ),
                "projected_remaining_scores": projected_remaining,
                "projected_total_scores": projected_total,
            }
        )

    if not entrant_rows:
        return {
            "generated_at": generated_at,
            "model": model,
            "n_sims": n_sims,
            "cadence_minutes": cadence_minutes,
            "coverage": {
                "total_entrants": 0,
                "total_picks": 0,
                "matched_picks": 0,
                "unmatched_picks": 0,
                "matched_pick_rate": 0.0,
                "unresolved_players": [],
            },
            "warnings": ["No entries available for projections."],
            "entrant_projections": [],
        }

    total_matrix = np.vstack([row["projected_total_scores"] for row in entrant_rows])
    win_probability, top3_probability = compute_finish_probabilities(total_matrix.tolist())

    output_rows = []
    for index, row in enumerate(entrant_rows):
        projected_remaining_summary = _summarize_scores(row["projected_remaining_scores"])
        projected_total_summary = _summarize_scores(row["projected_total_scores"])
        output_rows.append(
            {
                "entrant": row["entrant"],
                "current_score": row["current_score"],
                "projected_remaining_mean": projected_remaining_summary["mean"],
                "projected_remaining_median": projected_remaining_summary["median"],
                "projected_remaining_p10": projected_remaining_summary["p10"],
                "projected_remaining_p90": projected_remaining_summary["p90"],
                "projected_total_mean": projected_total_summary["mean"],
                "projected_total_median": projected_total_summary["median"],
                "projected_total_p10": projected_total_summary["p10"],
                "projected_total_p90": projected_total_summary["p90"],
                "win_probability": float(win_probability[index]),
                "top3_probability": float(top3_probability[index]),
                "alive_count": row["alive_count"],
                "matched_picks": row["matched_picks"],
                "total_picks": row["total_picks"],
                "unresolved_players": row["unresolved_players"],
                "player_projections": row["player_projections"],
            }
        )

    output_rows.sort(key=lambda row: (-row["win_probability"], -row["projected_total_mean"], -row["current_score"], row["entrant"]))

    warnings = []
    if unresolved_players_global:
        warnings.append(
            "Some picked players could not be matched to the simulation data. "
            "Their current points are included, but their future projected points are excluded."
        )
        if verbose:
            print("Unresolved picked players:")
            for player_name in sorted(unresolved_players_global):
                print(f"  - {player_name}")

    snapshot = {
        "generated_at": generated_at,
        "model": model,
        "n_sims": n_sims,
        "cadence_minutes": cadence_minutes,
        "coverage": {
            "total_entrants": len(output_rows),
            "total_picks": total_picks,
            "matched_picks": matched_picks,
            "unmatched_picks": total_picks - matched_picks,
            "matched_pick_rate": float(matched_picks / total_picks) if total_picks else 0.0,
            "unresolved_players": sorted(unresolved_players_global),
        },
        "warnings": warnings,
        "entrant_projections": output_rows,
    }
    if verbose:
        print(
            "Coverage summary: "
            f"{snapshot['coverage']['matched_picks']}/{snapshot['coverage']['total_picks']} picks matched "
            f"({snapshot['coverage']['matched_pick_rate']:.1%})"
        )
        _print_projection_summary(snapshot)
    return snapshot
