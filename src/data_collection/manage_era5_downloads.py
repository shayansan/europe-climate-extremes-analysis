
import argparse
import calendar
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import xarray as xr
from ecmwf.datastores import Client

from src.data_collection.manifest_runtime import (
    current_manifest_path,
    manifest_session,
    validate_manifest_scope,
)


MANIFEST_PATH = Path(
    "data/interim/era5_download_manifest.json"
)

CONFIG_PATH = Path.home() / ".cdsapirc"


def now_utc():
    return datetime.now(timezone.utc).isoformat()


def load_manifest():
    path = current_manifest_path(MANIFEST_PATH)
    if not path.exists():
        raise FileNotFoundError(path)

    with path.open(encoding="utf-8") as f:
        return json.load(f)


def save_manifest(manifest):
    path = current_manifest_path(MANIFEST_PATH)
    path.parent.mkdir(
        parents=True, exist_ok=True
    )

    temporary = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=".manifest_",
            suffix=".json",
            delete=False,
        ) as f:
            temporary = Path(f.name)
            json.dump(manifest, f, indent=2)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())

        os.replace(temporary, path)

    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def get_job(manifest, job_id):
    matches = [
        job for job in manifest["jobs"]
        if job["job_id"] == job_id
    ]

    if len(matches) != 1:
        raise ValueError(
            f"Expected exactly one job: {job_id}"
        )

    return matches[0]


def create_client():
    config = {}

    for line in CONFIG_PATH.read_text(
        encoding="utf-8"
    ).splitlines():
        if ":" not in line:
            continue

        key, value = line.split(":", 1)
        config[key.strip()] = value.strip()

    if not config.get("url") or not config.get("key"):
        raise ValueError("Incomplete CDS configuration")

    return Client(
        url=config["url"],
        key=config["key"],
        cleanup=False,
    )


def build_request(job):
    year = int(job["year"])
    month = int(job["month"])

    number_of_days = calendar.monthrange(
        year, month
    )[1]

    days = [
        f"{day:02d}"
        for day in range(1, number_of_days + 1)
    ]

    return {
        "product_type": "reanalysis",
        "variable": ["2m_temperature"],
        "year": str(year),
        "month": [f"{month:02d}"],
        "day": days,
        "daily_statistic": job["daily_statistic"],
        "time_zone": job["time_zone"],
        "frequency": job["frequency"],
        "area": job["area"],
    }


def validate_netcdf(path, job):
    with path.open("rb") as f:
        signature = f.read(8)

    if not (
        signature.startswith(b"CDF")
        or signature == b"\x89HDF\r\n\x1a\n"
    ):
        raise ValueError(
            "Downloaded data is not a NetCDF file"
        )

    year = int(job["year"])
    month = int(job["month"])

    expected_days = calendar.monthrange(
        year, month
    )[1]

    with xr.open_dataset(path) as ds:
        if "t2m" not in ds:
            raise ValueError("Missing t2m variable")

        if ds["t2m"].attrs.get("units") != "K":
            raise ValueError("Expected Kelvin units")

        if ds.sizes.get("valid_time") != expected_days:
            raise ValueError(
                "Unexpected number of observation days"
            )

        if (
            ds.sizes.get("latitude", 0) == 0
            or ds.sizes.get("longitude", 0) == 0
        ):
            raise ValueError("Empty geographic grid")

        dates = ds["valid_time"].values.astype(
            "datetime64[D]"
        )

        expected = np.arange(
            np.datetime64(f"{year}-{month:02d}-01"),
            np.datetime64(
                f"{year}-{month:02d}-01"
            ) + np.timedelta64(expected_days, "D"),
            dtype="datetime64[D]",
        )

        if not np.array_equal(dates, expected):
            raise ValueError(
                "Observation dates do not match requested month"
            )

    return True


def show_jobs(manifest):
    for job in manifest["jobs"]:
        print(
            f"{job['job_id']:15} "
            f"{job['status']:12} "
            f"{job.get('request_id') or '-'}"
        )


def submit_job(client, manifest, job):
    if job.get("request_id"):
        print("Existing request:", job["request_id"])
        print("Not submitting a duplicate.")
        return

    if job["status"] != "planned":
        raise ValueError(
            f"Cannot submit job with status {job['status']}"
        )

    request = build_request(job)

    print("Submitting:", job["job_id"])
    print("Dataset:", job["dataset"])
    print("Days:", len(request["day"]))

    remote = client.submit(
        job["dataset"],
        request,
    )

    job["request_id"] = remote.request_id
    job["submitted_at"] = now_utc()
    job["status"] = remote.status

    save_manifest(manifest)

    print("Request ID:", remote.request_id)
    print("Status:", remote.status)


def check_job(client, manifest, job):
    request_id = job.get("request_id")

    if not request_id:
        print("Job has not been submitted.")
        return

    remote = client.get_remote(request_id)

    job["status"] = remote.status
    job["last_checked_at"] = now_utc()

    if remote.status == "successful":
        job["completed_at"] = (
            job.get("completed_at") or now_utc()
        )

    save_manifest(manifest)

    print("Job:", job["job_id"])
    print("Request ID:", request_id)
    print("Status:", remote.status)
    print("Results ready:", remote.results_ready)


def download_job(client, manifest, job):
    request_id = job.get("request_id")

    if not request_id:
        raise ValueError("Job has not been submitted")

    target = Path(job["target"])

    if target.exists():
        validate_netcdf(target, job)

        job["status"] = "downloaded"
        job["downloaded_at"] = (
            job.get("downloaded_at") or now_utc()
        )
        save_manifest(manifest)

        print("Valid file already exists:", target)
        return

    remote = client.get_remote(request_id)

    if remote.status != "successful":
        job["status"] = remote.status
        save_manifest(manifest)
        print("Not ready:", remote.status)
        return

    target.parent.mkdir(
        parents=True, exist_ok=True
    )

    temporary = target.with_suffix(".part")

    if temporary.exists():
        print("Removing incomplete previous download.")
        temporary.unlink()

    print("Downloading existing request:", request_id)

    remote.download(str(temporary))

    try:
        validate_netcdf(temporary, job)
        os.replace(temporary, target)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise

    job["status"] = "downloaded"
    job["downloaded_at"] = now_utc()
    job["completed_at"] = (
        job.get("completed_at") or now_utc()
    )

    save_manifest(manifest)

    print("Validated download:", target)


def main():
    parser = argparse.ArgumentParser(
        description="Manage ERA5 CDS download jobs"
    )

    parser.add_argument(
        "action",
        choices=["list", "submit", "status", "download"],
    )

    parser.add_argument("--job", type=str)
    parser.add_argument(
        "--manifest", type=Path, default=MANIFEST_PATH,
        help="Manifest JSON path (default: original pilot manifest)",
    )

    args = parser.parse_args()

    with manifest_session(args.manifest):
        manifest = load_manifest()
        validate_manifest_scope(manifest)

        if args.action == "list":
            show_jobs(manifest)
            return

        if not args.job:
            parser.error("--job is required for this action")

        job = get_job(manifest, args.job)
        client = create_client()

        if args.action == "submit":
            # The CLI MUST NOT invoke the unsafe submit_job directly.
            from src.data_collection.safe_submit_era5 import safe_submit
            outcome = safe_submit(client, manifest, job)
            print("Outcome:", outcome)
        elif args.action == "status":
            check_job(client, manifest, job)
        elif args.action == "download":
            download_job(client, manifest, job)



if __name__ == "__main__":
    main()
