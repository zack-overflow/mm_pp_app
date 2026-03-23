from __future__ import annotations


def compute_finish_probabilities(score_rows: list[list[float]]) -> tuple[list[float], list[float]]:
    if not score_rows:
        return [], []

    n_entrants = len(score_rows)
    n_sims = len(score_rows[0])
    win_credit = [0.0] * n_entrants
    top3_credit = [0.0] * n_entrants

    for sim_index in range(n_sims):
        column = [score_rows[row_index][sim_index] for row_index in range(n_entrants)]
        winning_total = max(column)
        winner_indexes = [idx for idx, value in enumerate(column) if value == winning_total]
        split_credit = 1.0 / len(winner_indexes)
        for idx in winner_indexes:
            win_credit[idx] += split_credit

        cutoff = min(3, len(column))
        cutoff_value = sorted(column)[-cutoff]
        for idx, value in enumerate(column):
            if value >= cutoff_value:
                top3_credit[idx] += 1.0

    return (
        [value / n_sims for value in win_credit],
        [value / n_sims for value in top3_credit],
    )
