import json
import sys
import tempfile
import unittest
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[1]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

import app as app_module
import teams_in_progress as teams_in_progress_module


class LiveGameIndicatorTest(unittest.TestCase):
    def setUp(self):
        self.client = app_module.app.test_client()
        self.temp_dir = tempfile.TemporaryDirectory()
        temp_root = Path(self.temp_dir.name)

        self.player_data_path = temp_root / "local.json"
        self.projection_data_path = temp_root / "projection_local.json"
        self.teams_alive_path = temp_root / "teams_alive_mask.json"
        self.teams_in_progress_path = temp_root / "team_in_progress_mask.json"

        app_module.PLAYER_SCORING_DATA_JSON_FILE_PATH = str(self.player_data_path)
        app_module.PROJECTION_PLAYER_SCORING_DATA_JSON_FILE_PATH = str(self.projection_data_path)
        app_module.TEAMS_ALIVE_MASK_JSON_FILE_PATH = str(self.teams_alive_path)
        app_module.TEAM_IN_PROGRESS_MASK_JSON_FILE_PATH = str(self.teams_in_progress_path)

        teams_in_progress_module.TEAM_IN_PROGRESS_MASK_JSON_FILE_PATH = str(self.teams_in_progress_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_update_bk_persists_team_in_progress_mask(self):
        payload = {
            "player_scoring_data": {},
            "projection_player_scoring_data": {},
            "teams_alive_mask": {"Duke": 1},
            "team_in_progress_mask": {"Duke": 1, "Florida": 0},
        }

        update_response = self.client.post("/update_bk", json=payload)
        self.assertEqual(update_response.status_code, 200)

        self.assertTrue(self.teams_in_progress_path.exists())
        on_disk = json.loads(self.teams_in_progress_path.read_text())
        self.assertEqual(on_disk["Duke"], 1)
        self.assertEqual(on_disk["Florida"], 0)


if __name__ == "__main__":
    unittest.main()
