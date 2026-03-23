import sys
import unittest
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[1]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from projections.bracket import GameNode, TeamRef, apply_forced_winners, iter_games


def build_test_bracket():
    iowa_game = GameNode(
        round_number=1,
        label="region-4-r64-Clemson-Iowa",
        left=TeamRef("Clemson", 8),
        right=TeamRef("Iowa", 9),
    )
    florida_game = GameNode(
        round_number=1,
        label="region-4-r64-Florida-Prairie View A&M",
        left=TeamRef("Florida", 1),
        right=TeamRef("Prairie View A&M", 16),
    )
    round32 = GameNode(
        round_number=2,
        label="region-4-r32-1",
        left=iowa_game,
        right=florida_game,
    )
    semifinal = GameNode(
        round_number=5,
        label="f4-2",
        left=round32,
        right=TeamRef("Duke", 1),
    )
    return GameNode(
        round_number=6,
        label="championship",
        left=semifinal,
        right=TeamRef("Houston", 1),
    )


class ForcedWinnerValidationTest(unittest.TestCase):
    def test_apply_forced_winners_accepts_stepwise_path(self):
        root = build_test_bracket()

        apply_forced_winners(
            root,
            {
                "region-4-r64-Clemson-Iowa": "Iowa",
                "region-4-r32-1": "Iowa",
            },
        )

        games = {game.label: game for game in iter_games(root)}
        self.assertEqual(games["region-4-r64-Clemson-Iowa"].locked_winner, "Iowa")
        self.assertTrue(games["region-4-r64-Clemson-Iowa"].forced)
        self.assertEqual(games["region-4-r32-1"].locked_winner, "Iowa")
        self.assertTrue(games["region-4-r32-1"].forced)

    def test_apply_forced_winners_rejects_skipping_required_earlier_win(self):
        root = build_test_bracket()

        with self.assertRaisesRegex(ValueError, "not guaranteed to reach game"):
            apply_forced_winners(root, {"region-4-r32-1": "Iowa"})

    def test_apply_forced_winners_rejects_unknown_game_label(self):
        root = build_test_bracket()

        with self.assertRaisesRegex(ValueError, "Unknown forced winner game label"):
            apply_forced_winners(root, {"unknown-game": "Iowa"})

    def test_apply_forced_winners_rejects_team_outside_game_subtree(self):
        root = build_test_bracket()

        with self.assertRaisesRegex(ValueError, "not a valid participant"):
            apply_forced_winners(root, {"region-4-r32-1": "Duke"})


if __name__ == "__main__":
    unittest.main()
