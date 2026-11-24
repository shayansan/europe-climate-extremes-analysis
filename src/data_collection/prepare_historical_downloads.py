
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


OUTPUT_DIR = Path("data/raw/era5/historical")
MANIFEST_PATH = Path(
    "data/interim/era5_download_manifest.json"
)

STATISTICS = {
    "tmax": "daily_maximum",
    "tmean": "daily_mean",
}

DATASET = "derived-era5-single-levels-daily-statistics"

# Pilot geographic extent; not final European coverage.
AREA = [72, -25, 34, 45]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Prepare a historical ERA5 download plan"
    )

    parser.add_argument("--start-year", type=int, required=True)
    parser.add_argument("--end-year", type=int, required=True)

    return parser.parse_args()


def main():
    args = parse_args()

    if not 1940 <= args.start_year <= args.end_year <= 2025:
        raise ValueError("Invalid historical year range")

    jobs = []

    for year in range(args.start_year, args.end_year + 1):
        for month in range(1, 13):
            for label, statistic in STATISTICS.items():
                job_id = f"{year}-{month:02d}-{label}"

                target = (
                    OUTPUT_DIR
                    / label
                    / str(year)
                    / f"era5_{label}_{year}_{month:02d}.nc"
                )

                jobs.append({
                    "job_id": job_id,
                    "dataset": DATASET,
                    "year": year,
                    "month": month,
                    "statistic": label,
                    "daily_statistic": statistic,
                    "area": AREA,
                    "time_zone": "utc+00:00",
                    "frequency": "1_hourly",
                    "target": str(target),
                    "status": "planned",
                    "request_id": None,
                    "submitted_at": None,
                    "completed_at": None,
                })

    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "version": 1,
        "geographic_scope": "pilot_bbox_not_final_europe",
        "jobs": jobs,
    }

    MANIFEST_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if MANIFEST_PATH.exists():
        raise FileExistsError(
            f"Manifest already exists: {MANIFEST_PATH}"
        )

    MANIFEST_PATH.write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )

    print("=== ERA5 HISTORICAL DOWNLOAD PLAN ===")
    print("Start year:", args.start_year)
    print("End year:", args.end_year)
    print("Total monthly jobs:", len(jobs))
    print("Tmax jobs:", sum(j["statistic"] == "tmax" for j in jobs))
    print("Tmean jobs:", sum(j["statistic"] == "tmean" for j in jobs))
    print("Output:", MANIFEST_PATH)
    print("No download requests were submitted.")


if __name__ == "__main__":
    main()
