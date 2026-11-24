"""Validate daily ERA5 Tmax and Tmean on an identical grid."""

import argparse
from pathlib import Path

import numpy as np
import xarray as xr


def validate_temperature_consistency(tmax, tmean):
    """Return the number of observations passing consistency checks."""

    if tmax.dims != tmean.dims:
        raise ValueError("Temperature dimension order mismatch")

    if tmax.attrs.get("units") != "K":
        raise ValueError("Tmax must be in Kelvin")

    if tmean.attrs.get("units") != "K":
        raise ValueError("Tmean must be in Kelvin")

    tmax, tmean = xr.align(tmax, tmean, join="exact")

    maximum = np.asarray(tmax.values)
    average = np.asarray(tmean.values)

    if not np.isfinite(maximum).all():
        raise ValueError("Invalid Tmax values")

    if not np.isfinite(average).all():
        raise ValueError("Invalid Tmean values")

    differences = average - maximum

    violations = int(np.count_nonzero(differences > 1e-5))

    if violations:
        raise ValueError(
            f"Tmean exceeds Tmax in {violations} observations"
        )

    return maximum.size


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tmax", type=Path, required=True)
    parser.add_argument("--tmean", type=Path, required=True)
    args = parser.parse_args()

    with (
        xr.open_dataset(args.tmax) as max_ds,
        xr.open_dataset(args.tmean) as mean_ds,
    ):
        max_history = str(max_ds.attrs.get("history", "")).lower()
        mean_history = str(mean_ds.attrs.get("history", "")).lower()

        if "how=max" not in max_history:
            raise ValueError("Tmax processing metadata not confirmed")

        if "how=mean" not in mean_history:
            raise ValueError("Tmean processing metadata not confirmed")

        tmax = max_ds["t2m"]
        tmean = mean_ds["t2m"]

        count = validate_temperature_consistency(tmax, tmean)

        print("=== TEMPERATURE CONSISTENCY ===")
        print("Matched observations:", f"{count:,}")
        print("Tmean > Tmax violations: 0")
        print("RESULT: PASS")


if __name__ == "__main__":
    main()
