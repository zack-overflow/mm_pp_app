import json
import sys
import tempfile
import unittest
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[1]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

import app as app_module


class ProjectionEndpointTest(unittest.TestCase):
    def setUp(self):
        self.client = app_module.app.test_client()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.projections_path = Path(self.temp_dir.name) / "projections.json"
        self.pk_projections_path = Path(self.temp_dir.name) / "pk_projections.json"
        app_module.PROJECTIONS_JSON_FILE_PATH = str(self.projections_path)
        app_module.PK_PROJECTIONS_JSON_FILE_PATH = str(self.pk_projections_path)

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


if __name__ == "__main__":
    unittest.main()
