
import unittest
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import Mock

from src.data_collection.manage_era5_downloads import build_request
from src.data_collection.recover_era5_requests import (
    discover_requests,
    find_matches,
    normalize_request,
    request_matches,
)


class TestERA5RequestRecovery(unittest.TestCase):

    def setUp(self):
        self.job = {
            "job_id": "2020-08-tmax",
            "dataset": (
                "derived-era5-single-levels-daily-statistics"
            ),
            "year": 2020,
            "month": 8,
            "statistic": "tmax",
            "daily_statistic": "daily_maximum",
            "area": [72, -25, 34, 45],
            "time_zone": "utc+00:00",
            "frequency": "1_hourly",
            "status": "planned",
            "request_id": None,
        }

        self.manifest = {
            "version": 1,
            "jobs": [self.job],
        }

    def make_remote(
        self,
        request_id="request-123",
        request=None,
    ):
        if request is None:
            request = build_request(self.job)

        return SimpleNamespace(
            request_id=request_id,
            collection_id=self.job["dataset"],
            request=request,
            status="successful",
        )

    def test_full_month_matches(self):
        remote = self.make_remote()

        self.assertTrue(
            request_matches(self.job, remote)
        )

    def test_partial_month_does_not_match(self):
        request = build_request(self.job)

        request["day"] = ["01", "02", "03"]

        remote = self.make_remote(
            request=request
        )

        self.assertFalse(
            request_matches(self.job, remote)
        )

    def test_wrong_temperature_statistic_rejected(self):
        request = build_request(self.job)

        request["daily_statistic"] = "daily_mean"

        remote = self.make_remote(
            request=request
        )

        self.assertFalse(
            request_matches(self.job, remote)
        )

    def test_different_area_rejected(self):
        request = build_request(self.job)

        request["area"] = [72, -25, 34, 50]

        remote = self.make_remote(
            request=request
        )

        self.assertFalse(
            request_matches(self.job, remote)
        )

    def test_equivalent_date_formats_match(self):
        request = build_request(self.job)

        # Server may represent a single year as a list.
        request["year"] = ["2020"]
        request["month"] = "08"

        # Order of selected days should not matter.
        request["day"] = list(
            reversed(request["day"])
        )

        remote = self.make_remote(
            request=request
        )

        self.assertTrue(
            request_matches(self.job, remote)
        )

    def test_duplicate_matches_are_detected(self):
        first = self.make_remote(
            request_id="request-A"
        )

        second = self.make_remote(
            request_id="request-B"
        )

        matches = find_matches(
            self.manifest,
            [first, second],
        )

        self.assertEqual(
            len(matches["2020-08-tmax"]),
            2,
        )

    def test_existing_request_id_is_not_recovered_again(self):
        manifest = deepcopy(self.manifest)

        manifest["jobs"][0]["request_id"] = (
            "already-saved"
        )

        remote = self.make_remote()

        matches = find_matches(
            manifest,
            [remote],
        )

        self.assertEqual(len(matches), 0)

    def test_paginated_request_discovery(self):
        first_page = SimpleNamespace(
            request_ids=["request-A"],
        )

        second_page = SimpleNamespace(
            request_ids=["request-B", "request-A"],
            next=None,
        )

        first_page.next = second_page

        client = Mock()
        client.get_jobs.return_value = first_page

        def get_remote(request_id):
            return self.make_remote(
                request_id=request_id
            )

        client.get_remote.side_effect = get_remote

        remotes = discover_requests(client)

        self.assertEqual(len(remotes), 2)

        self.assertEqual(
            {remote.request_id for remote in remotes},
            {"request-A", "request-B"},
        )

        self.assertEqual(
            client.get_remote.call_count,
            2,
        )

        client.get_jobs.assert_called_once_with(
            limit=100,
            sortby="-created",
        )


if __name__ == "__main__":
    unittest.main()
