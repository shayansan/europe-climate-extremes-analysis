"""Opt-in integration test against disposable Docker MySQL."""

import os
import unittest
import uuid
from unittest.mock import patch

import mysql.connector
import numpy as np
import xarray as xr

from src.data_collection import import_era5_monthly as importer


@unittest.skipUnless(
    os.getenv("RUN_ERA5_MYSQL_TEST") == "1",
    "Docker MySQL integration test is opt-in",
)
class TestMySQLIntegration(unittest.TestCase):

    def test_import_idempotency_and_rollback(self):
        password = os.environ["ERA5_TEST_DB_PASSWORD"]

        # Never allow this test to use production connection settings.
        host = "127.0.0.1"
        port = 33307
        database = "europe_climate_test"

        connection = mysql.connector.connect(
            host=host,
            port=port,
            user="root",
            password=password,
            database=database,
            autocommit=False,
        )

        cursor = connection.cursor()
        dataset_id = None

        # Use unique metadata so repeated test runs stay isolated.
        test_dataset = "ERA5 integration " + uuid.uuid4().hex

        dates = np.array(
            ["2020-08-01", "2020-08-02"],
            dtype="datetime64[D]",
        )

        temperature = xr.DataArray(
            np.array([[[300.0]], [[301.0]]]),
            dims=("valid_time", "latitude", "longitude"),
            coords={
                "valid_time": dates,
                "latitude": [40.0],
                "longitude": [10.0],
            },
        )

        mask = np.array([[True]])
        latitudes = np.array([40.0])
        longitudes = np.array([10.0])

        def run_import():
            return importer.import_month(
                connection,
                temperature,
                mask,
                latitudes,
                longitudes,
                "tmax",
            )

        try:
            cursor.execute("SELECT DATABASE()")
            self.assertEqual(
                cursor.fetchone()[0],
                "europe_climate_test",
            )

            with patch.object(
                importer, "DATASET_NAME", test_dataset
            ):
                # First import
                dataset_id, inserted, total = run_import()
                self.assertEqual((inserted, total), (2, 2))

                # Idempotent repeated import
                _, inserted, total = run_import()
                self.assertEqual((inserted, total), (0, 2))

                # Prepare a conflict in the disposable database.
                cursor.execute(
                    """
                    DELETE FROM daily_temperatures
                    WHERE dataset_id=%s
                      AND observation_date=%s
                    """,
                    (dataset_id, "2020-08-01"),
                )

                cursor.execute(
                    """
                    UPDATE daily_temperatures
                    SET temperature_c=99.0
                    WHERE dataset_id=%s
                      AND observation_date=%s
                    """,
                    (dataset_id, "2020-08-02"),
                )

                connection.commit()

                # Import must fail and undo the earlier insertion.
                with self.assertRaisesRegex(
                    ValueError, "Conflicting temperature"
                ):
                    run_import()

                cursor.execute(
                    """
                    SELECT observation_date, temperature_c
                    FROM daily_temperatures
                    WHERE dataset_id=%s
                    ORDER BY observation_date
                    """,
                    (dataset_id,),
                )
                rows = cursor.fetchall()

                self.assertEqual(len(rows), 1)
                self.assertEqual(
                    str(rows[0][0]), "2020-08-02"
                )
                self.assertAlmostEqual(
                    rows[0][1], 99.0, places=3
                )

        finally:
            try:
                connection.rollback()

                if dataset_id is not None:
                    cursor.execute(
                        "DELETE FROM daily_temperatures "
                        "WHERE dataset_id=%s",
                        (dataset_id,),
                    )
                    cursor.execute(
                        "DELETE FROM datasets WHERE dataset_id=%s",
                        (dataset_id,),
                    )
                    connection.commit()
            finally:
                cursor.close()
                connection.close()


if __name__ == "__main__":
    unittest.main()
