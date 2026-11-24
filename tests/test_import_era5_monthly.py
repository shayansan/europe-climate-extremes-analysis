import calendar
import io
import tempfile
import unittest

from argparse import Namespace
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import xarray as xr

from src.data_collection import import_era5_monthly as importer


class TestERA5MonthlyImporter(unittest.TestCase):

    def make_temperature(self, days=1):
        dates = np.arange(
            np.datetime64("2020-08-01"),
            np.datetime64("2020-08-01")
            + np.timedelta64(days, "D"),
        )
        return xr.DataArray(
            np.full((days, 1, 1), 300.0),
            dims=("valid_time", "latitude", "longitude"),
            coords={
                "valid_time": dates,
                "latitude": [40.0],
                "longitude": [10.0],
            },
        )

    def test_dry_run_never_connects_to_database(self):
        temperature = self.make_temperature(
            calendar.monthrange(2020, 8)[1]
        )

        with tempfile.TemporaryDirectory() as directory:
            input_file = Path(directory) / "sample.nc"
            study_area = Path(directory) / "mask.geojson"
            input_file.touch()
            study_area.touch()

            args = Namespace(
                input=input_file,
                statistic="tmax",
                study_area=study_area,
                commit=False,
            )

            dataset = MagicMock()
            dataset.attrs = {"history": "how=max"}

            dataset_context = MagicMock()
            dataset_context.__enter__.return_value = dataset

            with (
                patch.object(importer, "parse_args",
                             return_value=args),
                patch.object(importer, "load_study_geometry",
                             return_value=object()),
                patch.object(importer.xr, "open_dataset",
                             return_value=dataset_context),
                patch.object(importer, "read_grid",
                             return_value=(
                                 temperature,
                                 np.array([40.0]),
                                 np.array([10.0]),
                             )),
                patch.object(importer, "create_spatial_mask",
                             return_value=(
                                 np.array([[True]]),
                                 None, None, None,
                             )),
                patch.object(importer, "connect_database") as connect,
            ):
                with redirect_stdout(io.StringIO()) as output:
                    importer.main()

                connect.assert_not_called()
                self.assertIn(
                    "DRY RUN PASS",
                    output.getvalue(),
                )

    def make_database(self, stored_count, inserted_count):
        connection = MagicMock()
        cursor = connection.cursor.return_value
        cursor.rowcount = inserted_count
        cursor.fetchone.return_value = (stored_count,)

        # Simulate one existing temperature, when present.
        cursor.fetchall.return_value = (
            [(4, 26.85)] if stored_count == 1 else []
        )

        return connection

    def run_import(self, connection):
        temperature = self.make_temperature()
        mask = np.array([[True]])

        with (
            patch.object(importer, "get_or_insert_dataset",
                         return_value=2),
            patch.object(importer, "prepare_grid_ids",
                         return_value=[4]),
        ):
            return importer.import_month(
                connection,
                temperature,
                mask,
                np.array([40.0]),
                np.array([10.0]),
                "tmax",
            )

    def test_incomplete_import_rolls_back(self):
        connection = self.make_database(
            stored_count=0,
            inserted_count=1,
        )

        with self.assertRaises(ValueError):
            self.run_import(connection)

        connection.rollback.assert_called_once()
        connection.commit.assert_not_called()

    def test_complete_existing_month_is_idempotent(self):
        connection = self.make_database(
            stored_count=1,
            inserted_count=0,
        )

        dataset_id, inserted, total = self.run_import(
            connection
        )

        self.assertEqual(dataset_id, 2)
        self.assertEqual(inserted, 0)
        self.assertEqual(total, 1)

        connection.commit.assert_called_once()
        connection.rollback.assert_not_called()


    def test_conflicting_existing_temperature_rolls_back(self):
        connection = self.make_database(
            stored_count=1,
            inserted_count=0,
        )

        cursor = connection.cursor.return_value

        # Existing SQL row has a different temperature.
        cursor.fetchall.return_value = [(4, 18.0)]

        # Incoming NetCDF contains 300 K = 26.85 C.
        with self.assertRaises(ValueError):
            self.run_import(connection)

        connection.rollback.assert_called_once()
        connection.commit.assert_not_called()



    def test_small_float_difference_is_accepted(self):
        connection = self.make_database(
            stored_count=1,
            inserted_count=0,
        )

        cursor = connection.cursor.return_value

        # Incoming temperature is approximately 26.85 C.
        # Stored FLOAT differs by just 0.0005 C.
        cursor.fetchall.return_value = [(4, 26.8505)]

        dataset_id, inserted, total = self.run_import(
            connection
        )

        self.assertEqual((dataset_id, inserted, total), (2, 0, 1))
        connection.commit.assert_called_once()
        connection.rollback.assert_not_called()
        cursor.executemany.assert_not_called()

    def test_sql_insert_failure_rolls_back(self):
        connection = self.make_database(
            stored_count=1,
            inserted_count=1,
        )

        cursor = connection.cursor.return_value
        cursor.fetchall.return_value = []
        cursor.executemany.side_effect = RuntimeError(
            "Simulated SQL insertion failure"
        )

        with self.assertRaisesRegex(
            RuntimeError,
            "Simulated SQL insertion failure",
        ):
            self.run_import(connection)

        connection.rollback.assert_called_once()
        connection.commit.assert_not_called()



if __name__ == "__main__":
    unittest.main()
