
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import xarray as xr
from shapely.geometry import box

from src.pipeline import (
    create_spatial_mask,
    load_study_geometry,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class TestPipelineStudyArea(unittest.TestCase):

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)

        self.root = Path(temporary.name)
        self.study_area = self.root / "study_area.geojson"

        self.geometry = box(10.5, 40.5, 12.5, 42.5)

        self.write_geojson([self.geometry])

    def write_geojson(self, geometries):
        data = gpd.GeoDataFrame(
            {"name": [f"area_{i}" for i in range(len(geometries))]},
            geometry=geometries,
            crs="EPSG:4326",
        )

        data.to_file(
            self.study_area,
            driver="GeoJSON",
        )

    def create_sample(self, filename, dates):
        path = self.root / filename

        latitudes = np.array([43.0, 42.0, 41.0])
        longitudes = np.array([10.0, 11.0, 12.0, 13.0])

        values = np.full(
            (len(dates), len(latitudes), len(longitudes)),
            293.15,
        )

        dataset = xr.Dataset(
            {
                "t2m": (
                    ("valid_time", "latitude", "longitude"),
                    values,
                    {"units": "K"},
                )
            },
            coords={
                "valid_time": np.array(dates, dtype="datetime64[D]"),
                "latitude": latitudes,
                "longitude": longitudes,
            },
        )

        dataset.to_netcdf(path)

        return path

    def run_pipeline(self, inputs, output):
        command = [
            sys.executable,
            "-m",
            "src.pipeline",
            "--input",
            *[str(path) for path in inputs],
            "--statistic",
            "tmax",
            "--study-area",
            str(self.study_area),
            "--output",
            str(output),
        ]

        return subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_custom_geometry_selects_correct_cells(self):
        geometry = load_study_geometry(
            PROJECT_ROOT / "unused_boundaries.zip",
            self.study_area,
        )

        latitudes = np.array([43.0, 42.0, 41.0])
        longitudes = np.array([10.0, 11.0, 12.0, 13.0])

        mask, weights, _, _ = create_spatial_mask(
            latitudes,
            longitudes,
            geometry,
        )

        expected = np.array([
            [False, False, False, False],
            [False, True, True, False],
            [False, True, True, False],
        ])

        np.testing.assert_array_equal(mask, expected)

        self.assertEqual(int(mask.sum()), 4)
        self.assertTrue(np.all(weights[mask] > 0))

    def test_multiple_geojson_features_rejected(self):
        self.write_geojson([
            box(10, 40, 11, 41),
            box(12, 42, 13, 43),
        ])

        with self.assertRaisesRegex(
            ValueError,
            "exactly one feature",
        ):
            load_study_geometry(
                PROJECT_ROOT / "unused_boundaries.zip",
                self.study_area,
            )

    def test_missing_study_area_rejected(self):
        with self.assertRaises(FileNotFoundError):
            load_study_geometry(
                PROJECT_ROOT / "unused_boundaries.zip",
                self.root / "missing.geojson",
            )

    def test_multifile_custom_mask_created_once(self):
        first = self.create_sample(
            "first.nc",
            ["2020-08-01", "2020-08-02"],
        )

        second = self.create_sample(
            "second.nc",
            ["2020-08-03"],
        )

        output = self.root / "processed.csv"

        result = self.run_pipeline(
            [first, second],
            output,
        )

        self.assertEqual(
            result.returncode,
            0,
            msg=result.stderr,
        )

        self.assertEqual(
            result.stdout.count(
                "Generating geographic mask once..."
            ),
            1,
        )

        dataframe = pd.read_csv(output)

        self.assertEqual(len(dataframe), 3)
        self.assertTrue(
            (dataframe["valid_cells"] == 4).all()
        )

        np.testing.assert_allclose(
            dataframe["weighted_mean_tmax_c"].to_numpy(),
            [20.0, 20.0, 20.0],
            atol=0.001,
        )


if __name__ == "__main__":
    unittest.main()
