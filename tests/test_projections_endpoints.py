import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


APP_ROOT = Path(__file__).resolve().parents[1]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

import app as app_module
import get_player_data as get_player_data_module


class ProjectionEndpointTest(unittest.TestCase):
    def setUp(self):
        self.client = app_module.app.test_client()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.projections_path = Path(self.temp_dir.name) / "projections.json"
        self.pk_projections_path = Path(self.temp_dir.name) / "pk_projections.json"
        self.player_scoring_path = Path(self.temp_dir.name) / "player_scoring.json"
        self.entries_path = Path(self.temp_dir.name) / "entries.json"
        self.pk_entries_path = Path(self.temp_dir.name) / "pk_entries.json"
        app_module.PROJECTIONS_JSON_FILE_PATH = str(self.projections_path)
        app_module.PK_PROJECTIONS_JSON_FILE_PATH = str(self.pk_projections_path)
        get_player_data_module.PLAYER_SCORING_DATA_JSON_FILE_PATH = str(self.player_scoring_path)
        get_player_data_module.ENTRIES_FILE_PATH = str(self.entries_path)
        get_player_data_module.PK_ENTRIES_FILE_PATH = str(self.pk_entries_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_update_and_read_projection_snapshot(self):
        payload = {
            "generated_at": "2026-03-19T12:00:00+00:00",
            "model": "KenPom",
            "n_sims": 5000,
            "cadence_minutes": 90,
            "coverage": {"matched_picks": 10, "total_picks": 10, "unmatched_picks": 0, "unresolved_players": []},
            "warnings": [],
            "entrant_projections": [],
        }

        update_response = self.client.post("/update_projections", json=payload)
        self.assertEqual(update_response.status_code, 200)

        get_response = self.client.get("/projections")
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.get_json()["generated_at"], payload["generated_at"])

        on_disk = json.loads(self.projections_path.read_text())
        self.assertEqual(on_disk["model"], "KenPom")

    def test_pk_update_and_read_projection_snapshot(self):
        payload = {
            "generated_at": "2026-03-19T12:30:00+00:00",
            "model": "KenPom",
            "n_sims": 500,
            "cadence_minutes": 90,
            "coverage": {"matched_picks": 10, "total_picks": 10, "unmatched_picks": 0, "unresolved_players": []},
            "warnings": [],
            "entrant_projections": [],
        }

        update_response = self.client.post("/pk/update_projections", json=payload)
        self.assertEqual(update_response.status_code, 200)

        get_response = self.client.get("/pk/projections")
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.get_json()["generated_at"], payload["generated_at"])

        on_disk = json.loads(self.pk_projections_path.read_text())
        self.assertEqual(on_disk["n_sims"], 500)

    def test_player_endpoint_uses_pool_specific_entries_for_ownership(self):
        self.player_scoring_path.write_text(
            json.dumps(
                {
                    "COOPER FLAGG": {
                        "team": "Duke",
                        "seed": 1,
                        "pts": [22, 18],
                        "pts_mult": 62,
                        "pts_mult_rounds": [26, 36],
                    }
                }
            )
        )
        self.entries_path.write_text(
            json.dumps(
                {
                    "Main One": {"picks": ["COOPER FLAGG"]},
                    "Main Two": {"picks": ["OTHER PLAYER"]},
                }
            )
        )
        self.pk_entries_path.write_text(
            json.dumps(
                {
                    "Pk One": {"picks": ["COOPER FLAGG"]},
                    "Pk Two": {"picks": ["COOPER FLAGG"]},
                    "Pk Three": {"picks": ["OTHER PLAYER"]},
                }
            )
        )

        main_response = self.client.get("/player/Cooper-Flagg")
        self.assertEqual(main_response.status_code, 200)
        self.assertEqual(main_response.get_json()["picked_by"], ["Main One"])
        self.assertEqual(main_response.get_json()["total_entrants"], 2)

        pk_response = self.client.get("/pk/player/Cooper-Flagg")
        self.assertEqual(pk_response.status_code, 200)
        self.assertEqual(pk_response.get_json()["picked_by"], ["Pk One", "Pk Two"])
        self.assertEqual(pk_response.get_json()["total_entrants"], 3)

    def test_whatif_returns_bad_request_for_invalid_forced_winners(self):
        with patch.object(app_module, "_build_projection_inputs", return_value={}), patch(
            "projections.pipeline.build_projection_snapshot",
            side_effect=[
                {"entrant_projections": []},
                ValueError("Invalid forced winner path"),
            ],
        ):
            response = self.client.post(
                "/whatif",
                json={
                    "forced_winners": {"region-4-r32-1": "Iowa"},
                    "n_sims": 100,
                    "model": "silver",
                },
            )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "Invalid forced winner path")


if __name__ == "__main__":
    unittest.main()
