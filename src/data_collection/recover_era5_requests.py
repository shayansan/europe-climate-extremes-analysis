
import argparse
import json
from collections import defaultdict

from src.data_collection.manage_era5_downloads import (
    build_request,
    create_client,
    load_manifest,
    save_manifest,
)


def normalize_request(request):
    """
    Normalize request parameters for exact comparison.

    Lists representing selections are sorted, and numeric
    geographic coordinates are converted to floats.
    """
    normalized = {}

    for key, value in request.items():
        if key == "area":
            normalized[key] = [
                float(number) for number in value
            ]

        elif key in {"year", "month", "day"}:
            values = value if isinstance(value, list) else [value]

            normalized[key] = sorted(
                int(item) for item in values
            )

        elif key in {"variable", "product_type"}:
            values = value if isinstance(value, list) else [value]
            normalized[key] = sorted(str(item) for item in values)

        else:
            normalized[key] = value

    return normalized


def request_matches(job, remote):
    if remote.collection_id != job["dataset"]:
        return False

    expected = normalize_request(build_request(job))
    actual = normalize_request(remote.request)

    return expected == actual


def discover_requests(client):
    """
    Read existing requests without submitting any new jobs.
    """
    jobs = client.get_jobs(
        limit=100,
        sortby="-created",
    )

    seen_ids = set()
    remotes = []

    while jobs is not None:
        for request_id in jobs.request_ids:
            if request_id in seen_ids:
                continue

            seen_ids.add(request_id)
            remotes.append(client.get_remote(request_id))

        jobs = jobs.next

    return remotes


def find_matches(manifest, remotes):
    matches = defaultdict(list)

    for job in manifest["jobs"]:
        if job.get("request_id"):
            continue

        for remote in remotes:
            if request_matches(job, remote):
                matches[job["job_id"]].append(remote)

    return matches


def main():
    parser = argparse.ArgumentParser(
        description="Recover existing ERA5 CDS request IDs"
    )

    parser.add_argument(
        "--apply",
        action="store_true",
        help="Save unambiguous matches to the manifest",
    )

    args = parser.parse_args()

    manifest = load_manifest()
    client = create_client()

    print("=== ERA5 REQUEST RECOVERY ===")
    print("Mode:", "APPLY" if args.apply else "DRY RUN")

    remotes = discover_requests(client)

    print("Server requests discovered:", len(remotes))
    print("Manifest jobs:", len(manifest["jobs"]))

    matches = find_matches(manifest, remotes)

    recovered = 0
    ambiguous = 0

    for job in manifest["jobs"]:
        if job.get("request_id"):
            continue

        candidates = matches.get(job["job_id"], [])

        if not candidates:
            continue

        if len(candidates) > 1:
            ambiguous += 1
            print(
                "AMBIGUOUS:",
                job["job_id"],
                "matches:",
                len(candidates),
            )
            continue

        remote = candidates[0]

        print(
            "MATCH:",
            job["job_id"],
            "->",
            remote.request_id,
            f"({remote.status})",
        )

        recovered += 1

        if args.apply:
            job["request_id"] = remote.request_id
            job["status"] = remote.status

            # Persist after each recovered request.
            save_manifest(manifest)

    print("\n=== SUMMARY ===")
    print("Unambiguous matches:", recovered)
    print("Ambiguous jobs:", ambiguous)
    print(
        "Manifest updated:",
        "YES" if args.apply and recovered else "NO",
    )
    print("New requests submitted: 0")


if __name__ == "__main__":
    main()
