
import argparse
from pathlib import Path

from src.data_collection.manifest_runtime import (
    manifest_session,
    validate_manifest_scope,
)

from src.data_collection.manage_era5_downloads import (
    create_client,
    get_job,
    load_manifest,
    save_manifest,
    submit_job,
)

from src.data_collection.recover_era5_requests import (
    discover_requests,
    request_matches,
)


class SubmissionNeedsReview(RuntimeError):
    """Submission state requires manual verification."""


def safe_submit(client, manifest, job):
    job_id = job["job_id"]

    print(f"Checking existing requests for {job_id}...")

    # Never submit again if a request ID is already known.
    if job.get("request_id"):
        print("Request already recorded:", job["request_id"])
        print("No new request submitted.")
        return "already_recorded"

    # This operation must succeed before any new submission.
    remotes = discover_requests(client)

    matches = [
        remote
        for remote in remotes
        if request_matches(job, remote)
    ]

    if len(matches) > 1:
        raise SubmissionNeedsReview(
            f"{job_id}: multiple matching server requests. "
            "Resolve manually before continuing."
        )

    if len(matches) == 1:
        remote = matches[0]

        job["request_id"] = remote.request_id
        job["status"] = remote.status

        save_manifest(manifest)

        print("Recovered existing request:", remote.request_id)
        print("Status:", remote.status)
        print("No new request submitted.")

        return "recovered"

    # If a previous submission was interrupted, do not
    # assume the server never received it.
    if job["status"] == "submission_pending":
        raise SubmissionNeedsReview(
            f"{job_id}: previous submission is uncertain. "
            "No matching request was found in the server "
            "listing. Do not submit again automatically."
        )

    if job["status"] != "planned":
        raise SubmissionNeedsReview(
            f"{job_id}: unexpected status {job['status']}. "
            "Manual review required."
        )

    # Persist the uncertain state BEFORE calling the API.
    job["status"] = "submission_pending"
    save_manifest(manifest)

    print("Submission intent saved in manifest.")
    print("Submitting one request...")

    # Existing submit_job accepts planned status.
    # Change only the in-memory status; the on-disk manifest
    # remains submission_pending until the request ID is saved.
    job["status"] = "planned"

    try:
        submit_job(client, manifest, job)
    except Exception:
        # Never silently retry an uncertain submission.
        job["status"] = "submission_pending"
        save_manifest(manifest)

        print(
            "Submission outcome uncertain. "
            "Recovery is required before any retry."
        )
        raise

    print("Request ID safely recorded.")
    return "submitted"


def main():
    parser = argparse.ArgumentParser(
        description="Safely submit an ERA5 request"
    )

    parser.add_argument(
        "--job",
        required=True,
        help="Manifest job ID, e.g. 2020-01-tmax",
    )

    parser.add_argument(
        "--manifest", type=Path,
        default=Path("data/interim/era5_download_manifest.json"),
        help="Manifest JSON path",
    )

    args = parser.parse_args()

    with manifest_session(args.manifest):
        manifest = load_manifest()
        validate_manifest_scope(manifest)
        job = get_job(manifest, args.job)
        client = create_client()
        outcome = safe_submit(client, manifest, job)
        print("Outcome:", outcome)


if __name__ == "__main__":
    main()
