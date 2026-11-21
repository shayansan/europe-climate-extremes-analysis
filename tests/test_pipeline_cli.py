
import csv
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


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


if __name__ == "__main__":
    unittest.main()
