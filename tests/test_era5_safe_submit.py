
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from src.data_collection import manage_era5_downloads as manager
from src.data_collection import safe_submit_era5 as safe


class TestSafeSubmission(unittest.TestCase):

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)

        self.manifest_path = (
            Path(temporary.name) / "manifest.json"
        )

        self.job = {
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
            "status": "planned",
            "request_id": None,
        }

        self.manifest = {"jobs": [self.job]}

        path_patch = patch.object(
            manager, "MANIFEST_PATH", self.manifest_path
        )
        path_patch.start()
        self.addCleanup(path_patch.stop)

    def test_new_submission_records_id(self):
        client = Mock()
        client.submit.return_value = SimpleNamespace(
            request_id="remote-123",
            status="accepted",
        )

        with patch.object(
            safe, "discover_requests", return_value=[]
        ):
            outcome = safe.safe_submit(
                client, self.manifest, self.job
            )

        self.assertEqual(outcome, "submitted")
        self.assertEqual(
            self.job["request_id"], "remote-123"
        )
        self.assertEqual(self.job["status"], "accepted")
        client.submit.assert_called_once()

    def test_existing_request_is_recovered(self):
        remote = SimpleNamespace(
            request_id="existing-123",
            status="successful",
            collection_id=self.job["dataset"],
            request=manager.build_request(self.job),
        )

        client = Mock()

        with patch.object(
            safe,
            "discover_requests",
            return_value=[remote],
        ):
            outcome = safe.safe_submit(
                client, self.manifest, self.job
            )

        self.assertEqual(outcome, "recovered")
        self.assertEqual(
            self.job["request_id"], "existing-123"
        )
        client.submit.assert_not_called()

    def test_interrupted_submission_never_retries(self):
        self.job["status"] = "submission_pending"
        client = Mock()

        with patch.object(
            safe, "discover_requests", return_value=[]
        ):
            with self.assertRaises(
                safe.SubmissionNeedsReview
            ):
                safe.safe_submit(
                    client, self.manifest, self.job
                )

        client.submit.assert_not_called()

    def test_network_error_leaves_pending_state(self):
        client = Mock()
        client.submit.side_effect = ConnectionError(
            "Network connection lost"
        )

        with patch.object(
            safe, "discover_requests", return_value=[]
        ):
            with self.assertRaises(ConnectionError):
                safe.safe_submit(
                    client, self.manifest, self.job
                )

        saved = manager.load_manifest()
        self.assertEqual(
            saved["jobs"][0]["status"],
            "submission_pending",
        )
        self.assertIsNone(
            saved["jobs"][0]["request_id"]
        )

    def test_duplicate_server_requests_are_blocked(self):
        request = manager.build_request(self.job)

        remotes = [
            SimpleNamespace(
                request_id=identifier,
                status="successful",
                collection_id=self.job["dataset"],
                request=request,
            )
            for identifier in ("A", "B")
        ]

        client = Mock()

        with patch.object(
            safe,
            "discover_requests",
            return_value=remotes,
        ):
            with self.assertRaises(
                safe.SubmissionNeedsReview
            ):
                safe.safe_submit(
                    client, self.manifest, self.job
                )

        client.submit.assert_not_called()


if __name__ == "__main__":
    unittest.main()
