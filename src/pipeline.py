
import argparse
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely
import xarray as xr


def parse_args():
    parser = argparse.ArgumentParser(
        description="Process ERA5 daily maximum temperatures."
    )

    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Path to the input ERA5 NetCDF file",
    )

    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Path to the output daily summary CSV",
    )

    parser.add_argument(
        "--boundaries",
        type=Path,
        default=Path(
            "data/raw/boundaries/"
            "ne_50m_admin_0_countries.zip"
        ),
    )

    parser.add_argument(
        "--mask-output",
        type=Path,
        default=None,
        help="Optional path to save the geographic mask",
    )

    return parser.parse_args()


def build_mask(latitudes, longitudes, boundary_path):
    world = gpd.read_file(boundary_path)

    if world.crs is None:
        raise ValueError("Boundary CRS is missing")

    world = world.to_crs("EPSG:4326")

    europe = world.loc[world["CONTINENT"] == "Europe"]

    if europe.empty:
        raise ValueError("No European polygons found")

    geometry = europe.geometry.union_all()

    lon_grid, lat_grid = np.meshgrid(
        longitudes,
        latitudes,
        indexing="xy",
    )

    mask = shapely.intersects_xy(
        geometry,
        lon_grid,
        lat_grid,
    )

    if not mask.any():
        raise ValueError("No grid cells inside study area")

    return mask, lat_grid, lon_grid


def process_file(input_path, boundary_path, mask_output):
    with xr.open_dataset(input_path) as ds:
        if "t2m" not in ds:
            raise ValueError("Missing t2m variable")

        temperature = ds["t2m"].transpose(
            "valid_time",
            "latitude",
            "longitude",
        )

        if temperature.attrs.get("units") != "K":
            raise ValueError("Expected temperature units: K")

        latitudes = temperature.latitude.values
        longitudes = temperature.longitude.values

        mask, lat_grid, lon_grid = build_mask(
            latitudes,
            longitudes,
            boundary_path,
        )

        if mask_output is not None:
            mask_output.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            pd.DataFrame({
                "latitude": lat_grid.ravel(),
                "longitude": lon_grid.ravel(),
                "in_study_area": mask.ravel(),
            }).to_csv(mask_output, index=False)

        weights = np.cos(np.deg2rad(lat_grid))

        if not np.all(np.isfinite(weights[mask])):
            raise ValueError("Invalid spatial weights")

        rows = []

        for timestamp in temperature.valid_time.values:
            day = temperature.sel(
                valid_time=timestamp
            ).values.astype(np.float64) - 273.15

            valid = mask & np.isfinite(day)

            if not valid.any():
                raise ValueError(
                    f"No valid temperature data: {timestamp}"
                )

            values = day[valid]
            day_weights = weights[valid]

            date = pd.Timestamp(timestamp).date()

            rows.append({
                "date": date,
                "valid_cells": int(valid.sum()),
                "weighted_mean_tmax_c": round(
                    float(np.average(
                        values,
                        weights=day_weights,
                    )),
                    3,
                ),
                "maximum_tmax_c": round(
                    float(values.max()),
                    3,
                ),
            })

    result = pd.DataFrame(rows)

    if result.empty:
        raise ValueError("Input contains no observation days")

    if result["date"].duplicated().any():
        raise ValueError("Duplicate observation dates")

    return result, int(mask.sum())


def main():
    args = parse_args()

    for path in (args.input, args.boundaries):
        if not path.is_file():
            raise FileNotFoundError(f"File not found: {path}")

    print("=== ERA5 CLIMATE PIPELINE ===", flush=True)
    print(f"Input: {args.input}")
    print(f"Boundaries: {args.boundaries}")

    result, selected_cells = process_file(
        args.input,
        args.boundaries,
        args.mask_output,
    )

    args.output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    result.to_csv(args.output, index=False)

    print(f"Selected grid cells: {selected_cells:,}")
    print(f"Days processed: {len(result)}")
    print(f"First date: {result['date'].min()}")
    print(f"Last date: {result['date'].max()}")
    print(f"Output: {args.output}")
    print("\n=== PIPELINE COMPLETED SUCCESSFULLY ===")


if __name__ == "__main__":
    main()
