from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from .config import MATCHUP_TREE_PATH


@dataclass(frozen=True)
class TeamRef:
    name: str
    seed: int


@dataclass
class GameNode:
    round_number: int
    label: str
    left: TeamRef | "GameNode"
    right: TeamRef | "GameNode"
    locked_winner: str | None = None
    forced: bool = False
    teams: frozenset[str] | None = None


ROUND_NAMES = {
    1: "Round of 64",
    2: "Round of 32",
    3: "Sweet 16",
    4: "Elite 8",
    5: "Final Four",
    6: "Championship",
}


def _sort_key(values: frozenset[str]) -> tuple[str, ...]:
    return tuple(sorted(values))


def load_matchup_structure(path: Path | None = None) -> dict[str, dict[str, list[str]]]:
    path = path or MATCHUP_TREE_PATH
    structure = defaultdict(lambda: defaultdict(list))

    with open(path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["Team"] == "Team":
                continue
            structure[row["Team"]][row["Round"]].append(row["Opponent"])

    return structure


def _mutual_round64_pairs(region_teams: frozenset[str], structure: dict[str, dict[str, list[str]]]) -> list[frozenset[str]]:
    seen = set()
    pairs = []
    for team in sorted(region_teams):
        opponent = structure[team]["r64"][0]
        pair = frozenset((team, opponent))
        if pair not in seen:
            seen.add(pair)
            pairs.append(pair)
    return pairs


def _quarter_sets(region_teams: frozenset[str], structure: dict[str, dict[str, list[str]]]) -> list[frozenset[str]]:
    quarters = set()
    for team in region_teams:
        quarters.add(frozenset([team] + structure[team]["r64"] + structure[team]["r32"]))
    return sorted(quarters, key=_sort_key)


def _half_sets(region_teams: frozenset[str], structure: dict[str, dict[str, list[str]]]) -> list[frozenset[str]]:
    halves = set()
    for team in region_teams:
        halves.add(frozenset([team] + structure[team]["r64"] + structure[team]["r32"] + structure[team]["s16"]))
    return sorted(halves, key=_sort_key)


def _build_region_root(
    region_name: str,
    region_teams: frozenset[str],
    structure: dict[str, dict[str, list[str]]],
    seed_map: dict[str, int],
) -> GameNode:
    round64_pairs = _mutual_round64_pairs(region_teams, structure)
    leaf_nodes = {
        pair: GameNode(
            round_number=1,
            label=f"{region_name}-r64-{'-'.join(sorted(pair))}",
            left=TeamRef(sorted(pair)[0], seed_map[sorted(pair)[0]]),
            right=TeamRef(sorted(pair)[1], seed_map[sorted(pair)[1]]),
        )
        for pair in round64_pairs
    }

    quarter_nodes = {}
    quarter_sets = _quarter_sets(region_teams, structure)
    if len(quarter_sets) != 4:
        raise ValueError(f"Expected 4 quarter-sets for {region_name}, found {len(quarter_sets)}")

    for index, quarter in enumerate(quarter_sets, start=1):
        quarter_pairs = sorted(
            [pair for pair in round64_pairs if pair.issubset(quarter)],
            key=_sort_key,
        )
        if len(quarter_pairs) != 2:
            raise ValueError(f"Expected 2 round-of-64 pairs in quarter {index} of {region_name}")
        quarter_nodes[quarter] = GameNode(
            round_number=2,
            label=f"{region_name}-r32-{index}",
            left=leaf_nodes[quarter_pairs[0]],
            right=leaf_nodes[quarter_pairs[1]],
        )

    half_nodes = {}
    half_sets = _half_sets(region_teams, structure)
    if len(half_sets) != 2:
        raise ValueError(f"Expected 2 half-sets for {region_name}, found {len(half_sets)}")

    for index, half in enumerate(half_sets, start=1):
        included_quarters = sorted(
            [quarter for quarter in quarter_sets if quarter.issubset(half)],
            key=_sort_key,
        )
        if len(included_quarters) != 2:
            raise ValueError(f"Expected 2 quarter-sets in half {index} of {region_name}")
        half_nodes[half] = GameNode(
            round_number=3,
            label=f"{region_name}-s16-{index}",
            left=quarter_nodes[included_quarters[0]],
            right=quarter_nodes[included_quarters[1]],
        )

    ordered_halves = sorted(half_sets, key=_sort_key)
    return GameNode(
        round_number=4,
        label=f"{region_name}-e8",
        left=half_nodes[ordered_halves[0]],
        right=half_nodes[ordered_halves[1]],
    )


def _score_for_round(team_name: str, round_number: int, team_round_scores: dict[str, list[float]]) -> float | None:
    scores = team_round_scores.get(team_name, [])
    index = round_number - 1
    if index >= len(scores):
        return None
    return scores[index]


def _describe_side(ref: TeamRef | GameNode) -> str:
    if isinstance(ref, TeamRef):
        return ref.name

    if ref.locked_winner:
        return ref.locked_winner

    teams = sorted(ref.teams or [])
    if not teams:
        return "TBD"
    if len(teams) <= 4:
        return "{" + " / ".join(teams) + "}"
    return "{" + " / ".join(teams[:4]) + " / ...}"


def describe_game(node: GameNode) -> str:
    return f"{_describe_side(node.left)} vs {_describe_side(node.right)}"


def iter_games(node: GameNode):
    if isinstance(node.left, GameNode):
        yield from iter_games(node.left)
    if isinstance(node.right, GameNode):
        yield from iter_games(node.right)
    yield node


def format_bracket_status(root: GameNode) -> str:
    by_round = defaultdict(list)
    for node in iter_games(root):
        round_name = ROUND_NAMES.get(node.round_number, f"Round {node.round_number}")
        if node.locked_winner:
            line = f"[locked] {describe_game(node)} -> {node.locked_winner}"
        else:
            line = f"[pending] {describe_game(node)}"
        by_round[round_name].append(line)

    sections = []
    for round_number in sorted(ROUND_NAMES):
        round_name = ROUND_NAMES[round_number]
        if round_name not in by_round:
            continue
        locked_count = sum(1 for line in by_round[round_name] if line.startswith("[locked]"))
        total_count = len(by_round[round_name])
        sections.append(f"{round_name}: {locked_count}/{total_count} locked")
        sections.extend(f"  {line}" for line in by_round[round_name])
    return "\n".join(sections)


def _team_is_alive(team_name: str, teams_alive_mask: dict[str, int] | None) -> bool:
    if not teams_alive_mask:
        return False
    return str(teams_alive_mask.get(team_name, 0)) == "1"


def _resolve_completed_game_winner(
    team1: str,
    team2: str,
    round_number: int,
    games_played: dict[str, int],
    teams_alive_mask: dict[str, int] | None,
) -> str | None:
    team1_games = games_played.get(team1, 0)
    team2_games = games_played.get(team2, 0)

    if min(team1_games, team2_games) < round_number:
        return None

    if team1_games != team2_games:
        return team1 if team1_games > team2_games else team2

    team1_alive = _team_is_alive(team1, teams_alive_mask)
    team2_alive = _team_is_alive(team2, teams_alive_mask)
    if team1_alive != team2_alive:
        return team1 if team1_alive else team2

    return None


def _annotate_locked_winners(
    node: GameNode,
    games_played: dict[str, int],
    team_round_scores: dict[str, list[float]],
    teams_alive_mask: dict[str, int] | None = None,
) -> tuple[frozenset[str], str | None]:
    if isinstance(node.left, GameNode):
        left_teams, left_winner = _annotate_locked_winners(
            node.left,
            games_played,
            team_round_scores,
            teams_alive_mask,
        )
    else:
        left_teams, left_winner = frozenset((node.left.name,)), None

    if isinstance(node.right, GameNode):
        right_teams, right_winner = _annotate_locked_winners(
            node.right,
            games_played,
            team_round_scores,
            teams_alive_mask,
        )
    else:
        right_teams, right_winner = frozenset((node.right.name,)), None

    node.teams = left_teams | right_teams

    if isinstance(node.left, TeamRef) and isinstance(node.right, TeamRef):
        participants = (node.left.name, node.right.name)
    elif left_winner and right_winner:
        participants = (left_winner, right_winner)
    else:
        participants = None

    if participants:
        team1, team2 = participants
        node.locked_winner = _resolve_completed_game_winner(
            team1,
            team2,
            node.round_number,
            games_played,
            teams_alive_mask,
        )

    return node.teams, node.locked_winner


def build_locked_bracket(
    seed_map: dict[str, int],
    games_played: dict[str, int],
    team_round_scores: dict[str, list[float]],
    teams_alive_mask: dict[str, int] | None = None,
    path: Path | None = None,
) -> GameNode:
    structure = load_matchup_structure(path)

    region_signatures = {}
    for team_name, rounds in structure.items():
        signature = frozenset([team_name] + rounds["r64"] + rounds["r32"] + rounds["s16"] + rounds["e8"])
        region_signatures.setdefault(signature, []).append(team_name)

    if len(region_signatures) != 4:
        raise ValueError(f"Expected 4 region signatures, found {len(region_signatures)}")

    region_roots = {}
    ordered_region_sets = sorted(region_signatures.keys(), key=_sort_key)
    for index, region_set in enumerate(ordered_region_sets, start=1):
        region_name = f"region-{index}"
        region_roots[region_set] = _build_region_root(region_name, region_set, structure, seed_map)

    semifinal_pairs = set()
    semifinal_nodes = []
    for region_set in ordered_region_sets:
        representative = min(region_set)
        paired_region = frozenset(structure[representative]["f4"])
        pair_key = tuple(sorted((region_set, paired_region), key=_sort_key))
        if pair_key in semifinal_pairs:
            continue
        semifinal_pairs.add(pair_key)

        left_region, right_region = pair_key
        semifinal_nodes.append(
            GameNode(
                round_number=5,
                label=f"f4-{len(semifinal_nodes) + 1}",
                left=region_roots[left_region],
                right=region_roots[right_region],
            )
        )

    if len(semifinal_nodes) != 2:
        raise ValueError(f"Expected 2 semifinals, found {len(semifinal_nodes)}")

    championship = GameNode(
        round_number=6,
        label="championship",
        left=semifinal_nodes[0],
        right=semifinal_nodes[1],
    )
    _annotate_locked_winners(championship, games_played, team_round_scores, teams_alive_mask)
    return championship


def _serialize_node(node: TeamRef | GameNode) -> dict:
    if isinstance(node, TeamRef):
        return {"type": "team", "name": node.name, "seed": node.seed}
    return {
        "type": "game",
        "label": node.label,
        "round_number": node.round_number,
        "locked_winner": node.locked_winner,
        "left": _serialize_node(node.left),
        "right": _serialize_node(node.right),
    }


def serialize_bracket_to_json(root: GameNode) -> dict:
    return _serialize_node(root)


def apply_forced_winners(root: GameNode, forced_winners: dict[str, str]) -> None:
    for game in iter_games(root):
        if game.label in forced_winners and game.locked_winner is None:
            game.locked_winner = forced_winners[game.label]
            game.forced = True
