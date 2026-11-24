import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from src.data_collection import manage_era5_downloads as manager
from src.data_collection import safe_submit_era5 as safe
from src.data_collection import recover_era5_requests as recovery
from src.data_collection.manifest_runtime import manifest_session, validate_manifest_scope


class TestManifestIsolation(unittest.TestCase):
    def setUp(self):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        self.root = Path(d.name)
        self.old = self.root / "old.json"
        self.new = self.root / "v2.json"
        self.base_job = {
            "job_id": "2020-08-tmax",
            "dataset": "derived-era5-single-levels-daily-statistics",
            "year": 2020, "month": 8,
            "statistic": "tmax", "daily_statistic": "daily_maximum",
            "area": [82, -26, 34, 70],
            "time_zone": "utc+00:00", "frequency": "1_hourly",
            "target": "data/raw/era5/historical_candidate_v2/tmax/2020/era5_tmax_2020_08.nc",
            "status": "planned", "request_id": None,
        }
        self.v2_data = {
            "version": 1,
            "geographic_scope": "europe_candidate_v2",
            "study_area": "data/processed/geography/europe_geographic_candidate_v2.geojson",
            "jobs": [self.base_job],
        }
        self.old.write_text('{"original":true}\n')
        self.new.write_text(json.dumps(self.v2_data))
        self.original = self.old.read_bytes()

    def test_session_load_save_only_selected_file(self):
        with patch.object(manager, "MANIFEST_PATH", self.old):
            with manifest_session(self.new):
                loaded = manager.load_manifest()
                validate_manifest_scope(loaded)
                loaded["jobs"][0]["status"] = "successful"
                manager.save_manifest(loaded)
        self.assertEqual(self.old.read_bytes(), self.original)
        self.assertEqual(json.loads(self.new.read_text())["jobs"][0]["status"], "successful")

    def test_invalid_area_fails_before_remote_call(self):
        self.v2_data["jobs"][0]["area"] = [72, -25, 34, 45]
        with self.assertRaises(ValueError):
            validate_manifest_scope(self.v2_data)

    def test_safe_cli_uses_selected_manifest(self):
        with patch.object(manager, "MANIFEST_PATH", self.old), \
             patch("sys.argv", ["safe_submit_era5", "--manifest", str(self.new), "--job", "2020-08-tmax"]), \
             patch.object(safe, "create_client", return_value=Mock()), \
             patch.object(safe, "safe_submit", return_value="already_recorded") as submit:
            safe.main()
        self.assertEqual(submit.call_count, 1)
        self.assertEqual(submit.call_args.args[1]["geographic_scope"], "europe_candidate_v2")
        self.assertEqual(self.old.read_bytes(), self.original)

    def test_manager_submit_delegates_to_safe(self):
        with patch.object(manager, "MANIFEST_PATH", self.old), \
             patch("sys.argv", ["manage_era5_downloads", "submit", "--manifest", str(self.new), "--job", "2020-08-tmax"]), \
             patch.object(manager, "create_client", return_value=Mock()), \
             patch.object(safe, "safe_submit", return_value="already_recorded") as submit:
            manager.main()
        submit.assert_called_once()
        self.assertEqual(self.old.read_bytes(), self.original)

    def test_recovery_dry_run_uses_selected_manifest(self):
        with patch.object(manager, "MANIFEST_PATH", self.old), \
             patch("sys.argv", ["recover_era5_requests", "--manifest", str(self.new)]), \
             patch.object(recovery, "create_client", return_value=Mock()), \
             patch.object(recovery, "discover_requests", return_value=[]):
            recovery.main()
        self.assertEqual(self.old.read_bytes(), self.original)


if __name__ == "__main__":
    unittest.main()
