
import csv
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
import xarray as xr

PROJECT_ROOT = Path(__file__).resolve().parents[1]

INPUT_FILE = PROJECT_ROOT / (
    "data/raw/era5/9831f09756389bd31899fc3ddad5aa5c.nc"
)

BOUNDARIES = PROJECT_ROOT / (
    "data/raw/boundaries/ne_50m_admin_0_countries.zip"
)


class TestPipelineCLI(unittest.TestCase):

    def run_pipeline(self, *arguments):
        return subprocess.run(
            [
                sys.executable,
                "-m",
                "src.pipeline",
                *map(str, arguments),
            ],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_invalid_input_file(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "result.csv"

            result = self.run_pipeline(
                "--input", Path(folder) / "missing.nc",
                "--output", output,
                "--boundaries", BOUNDARIES,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn(
                "FileNotFoundError",
                result.stderr,
            )
            self.assertFalse(output.exists())

    def test_pipeline_with_real_sample(self):
        if not INPUT_FILE.is_file():
            self.skipTest("ERA5 sample is unavailable")

        if not BOUNDARIES.is_file():
            self.skipTest("Natural Earth boundaries unavailable")

        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "summary.csv"
            mask = Path(folder) / "mask.csv"

            result = self.run_pipeline(
                "--input", INPUT_FILE,
                "--output", output,
                "--boundaries", BOUNDARIES,
                "--mask-output", mask,
            )

            self.assertEqual(
                result.returncode,
                0,
                msg=result.stderr,
            )

            self.assertTrue(output.is_file())
            self.assertTrue(mask.is_file())

            with output.open(newline="") as file:
                rows = list(csv.DictReader(file))

            self.assertEqual(len(rows), 31)
            self.assertEqual(rows[0]["date"], "2020-07-01")
            self.assertEqual(rows[-1]["date"], "2020-07-31")

            self.assertEqual(
                int(rows[0]["valid_cells"]),
                17463,
            )

            self.assertAlmostEqual(
                float(rows[0]["weighted_mean_tmax_c"]),
                23.271,
                places=3,
            )

            with mask.open(newline="") as file:
                mask_rows = list(csv.DictReader(file))

            self.assertEqual(len(mask_rows), 42993)

            selected = sum(
                row["in_study_area"] == "True"
                for row in mask_rows
            )

            self.assertEqual(selected, 17463)


    def test_overlapping_dates(self):
        if not INPUT_FILE.is_file() or not BOUNDARIES.is_file():
            self.skipTest("Required sample files unavailable")

        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)

            part_a = folder / "part_a.nc"
            part_b = folder / "part_b.nc"
            output = folder / "combined.csv"

            with xr.open_dataset(INPUT_FILE) as ds:
                ds.isel(
                    valid_time=slice(0, 15)
                ).to_netcdf(part_a)

                # Different file, but overlapping dates.
                ds.isel(
                    valid_time=slice(10, 25)
                ).to_netcdf(part_b)

            result = self.run_pipeline(
                "--input", part_a, part_b,
                "--output", output,
                "--boundaries", BOUNDARIES,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn(
                "Duplicate dates across input files",
                result.stderr,
            )
            self.assertFalse(output.exists())

    def test_incompatible_geographic_grids(self):
        if not INPUT_FILE.is_file() or not BOUNDARIES.is_file():
            self.skipTest("Required sample files unavailable")

        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)

            part_a = folder / "original_grid.nc"
            part_b = folder / "shifted_grid.nc"
            output = folder / "combined.csv"

            with xr.open_dataset(INPUT_FILE) as ds:
                ds.isel(
                    valid_time=slice(0, 5)
                ).to_netcdf(part_a)

                shifted = ds.isel(
                    valid_time=slice(5, 10)
                ).assign_coords(
                    longitude=ds.longitude + 0.25
                )

                shifted.to_netcdf(part_b)

            result = self.run_pipeline(
                "--input", part_a, part_b,
                "--output", output,
                "--boundaries", BOUNDARIES,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn(
                "incompatible geographic grids",
                result.stderr,
            )
            self.assertFalse(output.exists())

    def test_multifile_matches_single_file(self):
        if not INPUT_FILE.is_file() or not BOUNDARIES.is_file():
            self.skipTest("Required ERA5 sample files unavailable")

        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)

            part_1 = folder / "part_1.nc"
            part_2 = folder / "part_2.nc"

            single_output = folder / "single.csv"
            multi_output = folder / "multi.csv"

            with xr.open_dataset(INPUT_FILE) as ds:
                ds.isel(
                    valid_time=slice(0, 15)
                ).to_netcdf(part_1)

                ds.isel(
                    valid_time=slice(15, None)
                ).to_netcdf(part_2)

            single = self.run_pipeline(
                "--input", INPUT_FILE,
                "--output", single_output,
                "--boundaries", BOUNDARIES,
            )

            self.assertEqual(
                single.returncode, 0, msg=single.stderr
            )

            multi = self.run_pipeline(
                "--input", part_1, part_2,
                "--output", multi_output,
                "--boundaries", BOUNDARIES,
            )

            self.assertEqual(
                multi.returncode, 0, msg=multi.stderr
            )

            self.assertEqual(
                single_output.read_bytes(),
                multi_output.read_bytes(),
            )

            self.assertEqual(
                multi.stdout.count(
                    "Generating geographic mask once..."
                ),
                1,
            )



if __name__ == "__main__":
    unittest.main()
