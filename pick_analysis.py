import csv
import json
import math
import statistics
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

from constants import ENTRIES_FILE_PATH, PK_ENTRIES_FILE_PATH


APP_DIR = Path(__file__).resolve().parent
PLAYER_LIST_PATH = APP_DIR / "espn_players_2026.csv"


def _entries_path(pikap=False):
    primary = APP_DIR / (PK_ENTRIES_FILE_PATH if pikap else ENTRIES_FILE_PATH)
    if primary.exists():
        return primary

    fallbacks = ["entries_final.json"] if pikap else [
        "null_kaval_entries_final.json",
        "null_kaval_entries_temp.json",
    ]
    for fallback_name in fallbacks:
        fallback_path = APP_DIR / fallback_name
        if fallback_path.exists():
            return fallback_path

    return primary


def _normalize_name(value):
    return str(value).strip().upper()


def _load_player_meta():
    with open(PLAYER_LIST_PATH, newline="") as f:
        rows = list(csv.DictReader(f))

    return {
        _normalize_name(row["player_name"]): {
            "team": row["team_name"],
            "seed": int(row["seed"]),
        }
        for row in rows
    }


def get_pick_analysis(pikap=False):
    with open(_entries_path(pikap), "r") as f:
        entries = json.load(f)

    player_meta = _load_player_meta()

    total_entrants = len(entries)
    filled_entries = {
        entrant: entry.get("picks", [])
        for entrant, entry in entries.items()
        if entry.get("picks")
    }
    filled_entry_count = len(filled_entries)

    player_counts = Counter()
    player_entrants = defaultdict(list)
    player_display = {}
    team_counts = Counter()
    team_unique_players = defaultdict(set)
    seed_counts = Counter()
    seed_unique_players = defaultdict(set)
    missing_players = []

    for entrant, picks in filled_entries.items():
        for pick in picks:
            normalized = _normalize_name(pick)
            if not normalized:
                continue

            player_display.setdefault(normalized, str(pick).strip())
            player_counts[normalized] += 1
            player_entrants[normalized].append(entrant)

            meta = player_meta.get(normalized)
            if meta is None:
                missing_players.append(str(pick).strip())
                continue

            team_counts[meta["team"]] += 1
            team_unique_players[meta["team"]].add(normalized)
            seed_counts[meta["seed"]] += 1
            seed_unique_players[meta["seed"]].add(normalized)

    all_seed_values = []
    for player_name, count in player_counts.items():
        meta = player_meta.get(player_name)
        if not meta:
            continue
        all_seed_values.extend([meta["seed"]] * count)

    ownership_denominator = filled_entry_count or max(total_entrants, 1)
    high_owned_threshold = max(2, math.ceil(ownership_denominator * 0.67))

    top_players = []
    for player_name, pick_count in player_counts.most_common():
        meta = player_meta.get(player_name)
        if not meta:
            continue

        top_players.append({
            "player": player_display.get(player_name, player_name.title()),
            "team": meta["team"],
            "seed": meta["seed"],
            "pick_count": pick_count,
            "ownership_pct": round((pick_count / ownership_denominator) * 100, 1),
            "entrants": player_entrants[player_name],
        })

    consensus_picks = [
        player
        for player in top_players
        if filled_entry_count > 0 and player["pick_count"] == filled_entry_count
    ]

    one_off_picks = [
        {
            **player,
            "only_entrant": player["entrants"][0] if player["entrants"] else "",
        }
        for player in top_players
        if player["pick_count"] == 1
    ]

    seed_breakdown = []
    for seed in sorted(seed_counts):
        top_seed_players = [
            {
                "player": player["player"],
                "team": player["team"],
                "pick_count": player["pick_count"],
            }
            for player in top_players
            if player["seed"] == seed
        ][:3]

        seed_breakdown.append({
            "seed": seed,
            "pick_count": seed_counts[seed],
            "avg_per_entry": round(seed_counts[seed] / ownership_denominator, 2),
            "unique_players": len(seed_unique_players[seed]),
            "top_players": top_seed_players,
        })

    team_breakdown = [
        {
            "team": team,
            "pick_count": pick_count,
            "unique_players": len(team_unique_players[team]),
        }
        for team, pick_count in team_counts.most_common()
    ]

    overlap_totals = defaultdict(list)
    pairwise_overlap = []
    normalized_entry_sets = {
        entrant: {_normalize_name(pick) for pick in picks if _normalize_name(pick)}
        for entrant, picks in filled_entries.items()
    }

    for (entrant_a, picks_a), (entrant_b, picks_b) in combinations(normalized_entry_sets.items(), 2):
        shared = len(picks_a & picks_b)
        union = len(picks_a | picks_b)
        jaccard = round(shared / union, 3) if union else 0

        overlap_totals[entrant_a].append(shared)
        overlap_totals[entrant_b].append(shared)
        pairwise_overlap.append({
            "entrant_a": entrant_a,
            "entrant_b": entrant_b,
            "shared_picks": shared,
            "jaccard": jaccard,
        })

    entrant_profiles = []
    for entrant, normalized_picks in normalized_entry_sets.items():
        valid_meta = [player_meta[name] for name in normalized_picks if name in player_meta]
        avg_seed = round(
            sum(meta["seed"] for meta in valid_meta) / len(valid_meta),
            2,
        ) if valid_meta else 0

        entrant_profiles.append({
            "entrant": entrant,
            "avg_seed": avg_seed,
            "unique_picks": sum(1 for name in normalized_picks if player_counts[name] == 1),
            "consensus_picks": sum(
                1 for name in normalized_picks
                if filled_entry_count > 0 and player_counts[name] == filled_entry_count
            ),
            "high_owned_picks": sum(
                1 for name in normalized_picks
                if player_counts[name] >= high_owned_threshold
            ),
            "avg_shared_picks": round(
                sum(overlap_totals[entrant]) / len(overlap_totals[entrant]),
                2,
            ) if overlap_totals[entrant] else 0,
        })

    entrant_profiles.sort(key=lambda row: (-row["unique_picks"], row["avg_shared_picks"], row["avg_seed"]))
    pairwise_overlap.sort(key=lambda row: (-row["shared_picks"], -row["jaccard"], row["entrant_a"], row["entrant_b"]))

    present_seeds = set(seed_counts.keys())
    missing_seeds = [seed for seed in range(1, 17) if seed not in present_seeds]

    summary = {
        "total_entrants": total_entrants,
        "filled_entries": filled_entry_count,
        "total_picks": sum(len(picks) for picks in filled_entries.values()),
        "unique_players": len(top_players),
        "average_seed": round(statistics.mean(all_seed_values), 2) if all_seed_values else 0,
        "median_seed": round(statistics.median(all_seed_values), 2) if all_seed_values else 0,
        "favorite_seed": seed_counts.most_common(1)[0][0] if seed_counts else None,
        "missing_seeds": missing_seeds,
    }

    return {
        "summary": summary,
        "top_players": top_players,
        "seed_breakdown": seed_breakdown,
        "team_breakdown": team_breakdown,
        "consensus_picks": consensus_picks,
        "one_off_picks": one_off_picks,
        "entrant_profiles": entrant_profiles,
        "pairwise_overlap": pairwise_overlap[:8],
        "missing_players": sorted(set(missing_players)),
    }
