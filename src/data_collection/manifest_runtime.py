"""Shared manifest selection, validation and interprocess lock for ERA5 CLIs."""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
import fcntl

_active_manifest = ContextVar("era5_active_manifest", default=None)


def current_manifest_path(default_path):
    selected = _active_manifest.get()
    return Path(selected) if selected is not None else Path(default_path)


@contextmanager
def manifest_session(path):
    """Serialize ALL manifest CLI operations, including remote API calls.

    The lock uses an adjacent .lock file; do not delete it while running.
    Supported on Linux (fcntl.flock). Other processes must use these CLIs
    to participate in locking. The existing Python API is not lock-aware.
    """
    path = Path(path).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(path)
    lock_path = path.with_name(path.name + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+b") as lock_handle:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
        token = _active_manifest.set(path)
        try:
            yield path
        finally:
            _active_manifest.reset(token)
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)


def validate_manifest_scope(manifest):
    """Reject mismatched scopes/areas before contacting CDS."""
    configs = {
        "pilot_bbox_not_final_europe": [72, -25, 34, 45],
        "europe_candidate_v2": [82, -26, 34, 70],
    }
    scope = manifest.get("geographic_scope")
    if scope not in configs:
        raise ValueError(f"Unrecognized geographic scope: {scope!r}")
    jobs = manifest.get("jobs")
    if not isinstance(jobs, list) or not jobs:
        raise ValueError("Manifest has no jobs")
    expected = configs[scope]
    ids = set()
    targets = set()
    for job in jobs:
        job_id = job.get("job_id")
        target = job.get("target")
        if not isinstance(job_id, str) or not job_id:
            raise ValueError("Manifest job has an invalid job_id")
        if job_id in ids:
            raise ValueError(f"Duplicate job ID: {job_id}")
        ids.add(job_id)
        if not isinstance(target, str) or not target:
            raise ValueError(f"Missing target for {job_id}")
        if target in targets:
            raise ValueError(f"Duplicate output target: {target}")
        targets.add(target)
        if job.get("area") != expected:
            raise ValueError(f"{job_id}: geographic area does not match {scope}")
        statistic = job.get("statistic")
        expected_statistic = {"tmax": "daily_maximum", "tmean": "daily_mean"}.get(statistic)
        if expected_statistic is None or job.get("daily_statistic") != expected_statistic:
            raise ValueError(f"{job_id}: statistic mismatch")
    if scope == "europe_candidate_v2":
        expected_area = "data/processed/geography/europe_geographic_candidate_v2.geojson"
        if manifest.get("study_area") != expected_area:
            raise ValueError("Candidate V2 study area does not match expected geometry")
    return True
