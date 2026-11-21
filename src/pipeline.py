
import subprocess
import sys
from pathlib import Path

# Resolve the project root from this file's location.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

STEPS = [
    (
        "Generate geographic mask",
        "src/data_processing/build_study_area_mask.py",
    ),
    (
        "Calculate area-weighted temperatures",
        "src/data_processing/area_weighted_temperature.py",
    ),
    (
        "Validate pipeline outputs",
        "tests/test_pipeline_integration.py",
    ),
]


def main():
    print("=== ERA5 PIPELINE RUNNER ===", flush=True)

    for name, script in STEPS:
        script_path = PROJECT_ROOT / script

        if not script_path.is_file():
            raise FileNotFoundError(
                f"Missing pipeline script: {script_path}"
            )

        print(f"\n[RUNNING] {name}", flush=True)

        subprocess.run(
            [sys.executable, str(script_path)],
            cwd=PROJECT_ROOT,
            check=True,
        )

        print(f"[PASSED] {name}", flush=True)

    print("\n=== PIPELINE COMPLETED SUCCESSFULLY ===")


if __name__ == "__main__":
    main()
