
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

ERA5_DIR = Path("data/raw/era5")

MASK_FILE = Path(
    "data/processed/study_area_mask_50m_preview.csv"
)

OUTPUT_FILE = Path(
    "data/processed/area_weighted_daily_tmax_preview.csv"
)


def main():
    files = sorted(ERA5_DIR.glob("*.nc"))

    if len(files) != 1:
        raise ValueError(
            f"Expected one NetCDF file, found {len(files)}"
        )

    # Load the geographic mask.
    mask_df = pd.read_csv(MASK_FILE)

    required = {
        "latitude",
        "longitude",
        "in_study_area",
    }

    if not required.issubset(mask_df.columns):
        raise ValueError("Invalid mask columns")

    if mask_df["in_study_area"].isna().any():
        raise ValueError("Mask contains missing values")

    with xr.open_dataset(files[0]) as ds:
        temperature = ds["t2m"].transpose(
            "valid_time",
            "latitude",
            "longitude",
        )

        if temperature.attrs.get("units") != "K":
            raise ValueError("Expected Kelvin temperature")

        latitudes = temperature.latitude.values
        longitudes = temperature.longitude.values

        lon_grid, lat_grid = np.meshgrid(
            longitudes, latitudes
        )

        # Verify the mask matches this exact ERA5 grid.
        if len(mask_df) != lon_grid.size:
            raise ValueError("Mask/grid size mismatch")

        if not np.allclose(
            mask_df["latitude"].to_numpy(),
            lat_grid.ravel(),
        ):
            raise ValueError("Latitude order mismatch")

        if not np.allclose(
            mask_df["longitude"].to_numpy(),
            lon_grid.ravel(),
        ):
            raise ValueError("Longitude order mismatch")

        mask = mask_df["in_study_area"].to_numpy()
        mask = mask.reshape(lat_grid.shape).astype(bool)

        # Approximate grid-cell area weighting.
        weights = np.cos(np.deg2rad(lat_grid))
        weights = np.where(mask, weights, 0.0)

        rows = []

        for index, timestamp in enumerate(
            temperature.valid_time.values
        ):
            celsius = temperature.isel(
                valid_time=index
            ).values - 273.15

            valid = mask & np.isfinite(celsius)

            if not valid.any():
                raise ValueError(
                    f"No valid observations for {timestamp}"
                )

            day_weights = weights[valid]
            day_temps = celsius[valid]

            weighted_mean = np.average(
                day_temps,
                weights=day_weights,
            )

            rows.append({
                "date": pd.Timestamp(timestamp).date(),
                "valid_cells": int(valid.sum()),
                "weighted_mean_tmax_c": round(
                    float(weighted_mean), 3
                ),
                "maximum_tmax_c": round(
                    float(day_temps.max()), 3
                ),
            })

    result = pd.DataFrame(rows)

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    result.to_csv(OUTPUT_FILE, index=False)

    print("=== AREA-WEIGHTED ERA5 ANALYSIS ===")
    print("Mask: Natural Earth 50m preview")
    print("Days processed:", len(result))
    print("Selected grid cells:", int(mask.sum()))
    print("\nFirst five days:")
    print(result.head().to_string(index=False))
    print("\nOutput:", OUTPUT_FILE)


if __name__ == "__main__":
    main()
