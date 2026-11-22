
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from src.data_collection import manage_era5_downloads as manager


class TestERA5DownloadManager(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

        self.root = Path(self.temp_dir.name)
        self.manifest_path = self.root / "manifest.json"

        self.manifest = {
            "version": 1,
            "geographic_scope": "pilot_bbox_not_final_europe",
            "jobs": [
                {
                    "job_id": "2020-01-tmax",
                    "dataset": (
                        "derived-era5-single-levels-"
                        "daily-statistics"
                    ),
                    "year": 2020,
                    "month": 1,
                    "statistic": "tmax",
                    "daily_statistic": "daily_maximum",
                    "area": [72, -25, 34, 45],
                    "time_zone": "utc+00:00",
                    "frequency": "1_hourly",
                    "target": str(
                        self.root / "era5_tmax_2020_01.nc"
                    ),
                    "status": "planned",
                    "request_id": None,
                    "submitted_at": None,
                    "completed_at": None,
                }
            ],
        }

        self.job = self.manifest["jobs"][0]

        patcher = patch.object(
            manager,
            "MANIFEST_PATH",
            self.manifest_path,
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def saved_job(self):
        data = json.loads(
            self.manifest_path.read_text(
                encoding="utf-8"
            )
        )
        return data["jobs"][0]

    def test_submit_records_request_id(self):
        remote = SimpleNamespace(
            request_id="test-request-123",
            status="accepted",
        )

        client = Mock()
        client.submit.return_value = remote

        manager.submit_job(
            client, self.manifest, self.job
        )

        self.assertEqual(
            self.saved_job()["request_id"],
            "test-request-123",
        )
        self.assertEqual(
            self.saved_job()["status"],
            "accepted",
        )
        self.assertIsNotNone(
            self.saved_job()["submitted_at"]
        )

        client.submit.assert_called_once()

    def test_submit_does_not_duplicate_request(self):
        self.job["request_id"] = "existing-request"
        self.job["status"] = "accepted"

        client = Mock()

        manager.submit_job(
            client, self.manifest, self.job
        )

        client.submit.assert_not_called()

    def test_status_recovers_existing_request(self):
        self.job["request_id"] = "test-request-123"
        self.job["status"] = "accepted"

        client = Mock()
        client.get_remote.return_value = (
            SimpleNamespace(
                status="successful",
                results_ready=True,
            )
        )

        manager.check_job(
            client, self.manifest, self.job
        )

        client.get_remote.assert_called_once_with(
            "test-request-123"
        )

        self.assertEqual(
            self.saved_job()["status"],
            "successful",
        )
        self.assertIsNotNone(
            self.saved_job()["completed_at"]
        )

    def test_download_existing_successful_request(self):
        self.job["request_id"] = "test-request-123"
        self.job["status"] = "successful"

        remote = Mock()
        remote.status = "successful"

        def fake_download(path):
            Path(path).write_bytes(b"FAKE_NETCDF")
            return str(path)

        remote.download.side_effect = fake_download

        client = Mock()
        client.get_remote.return_value = remote

        # This test isolates download orchestration.
        # Actual NetCDF validation is tested separately.
        with patch.object(
            manager,
            "validate_netcdf",
            return_value=True,
        ) as validate:
            manager.download_job(
                client,
                self.manifest,
                self.job,
            )

        target = Path(self.job["target"])

        self.assertTrue(target.exists())
        self.assertEqual(
            target.read_bytes(),
            b"FAKE_NETCDF",
        )
        self.assertEqual(
            self.saved_job()["status"],
            "downloaded",
        )

        client.get_remote.assert_called_once_with(
            "test-request-123"
        )
        remote.download.assert_called_once()
        validate.assert_called_once()

    def test_monthly_request_accounts_for_leap_year(self):
        self.job["year"] = 2020
        self.job["month"] = 2

        request = manager.build_request(self.job)

        self.assertEqual(len(request["day"]), 29)
        self.assertEqual(request["day"][-1], "29")
        self.assertEqual(
            request["daily_statistic"],
            "daily_maximum",
        )


if __name__ == "__main__":
    unittest.main()
