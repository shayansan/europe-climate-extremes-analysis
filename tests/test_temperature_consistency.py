import unittest

import numpy as np
import xarray as xr

from src.data_processing.temperature_consistency import validate_temperature_consistency




class TestTemperatureConsistency(unittest.TestCase):

    def make_arrays(self, maximum, average):
        coordinates = {"valid_time": ["2020-08-01"]}

        tmax = xr.DataArray(
            [maximum],
            dims=("valid_time",),
            coords=coordinates,
        )

        tmean = xr.DataArray(
            [average],
            dims=("valid_time",),
            coords=coordinates,
        )

        tmax.attrs["units"] = "K"
        tmean.attrs["units"] = "K"
        return tmax, tmean

    def test_valid_temperatures(self):
        tmax, tmean = self.make_arrays(301.0, 299.0)
        self.assertEqual(
            validate_temperature_consistency(tmax, tmean),
            1,
        )

    def test_tmean_above_tmax_rejected(self):
        tmax, tmean = self.make_arrays(300.0, 301.0)

        with self.assertRaisesRegex(
            ValueError, "Tmean exceeds Tmax"
        ):
            validate_temperature_consistency(tmax, tmean)

    def test_missing_temperature_rejected(self):
        tmax, tmean = self.make_arrays(300.0, np.nan)

        with self.assertRaisesRegex(
            ValueError, "Invalid Tmean"
        ):
            validate_temperature_consistency(tmax, tmean)

    def test_mismatched_dates_rejected(self):
        tmax, tmean = self.make_arrays(300.0, 299.0)

        tmean = tmean.assign_coords(
            valid_time=["2020-08-02"]
        )

        with self.assertRaises(ValueError):
            validate_temperature_consistency(tmax, tmean)


if __name__ == "__main__":
    unittest.main()
