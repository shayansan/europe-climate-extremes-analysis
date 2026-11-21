
import argparse
import os
import tempfile
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
        nargs="+",
        required=True,
        help="One or more ERA5 NetCDF files",
    )

    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Output CSV path",
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
        help="Optional geographic mask CSV",
    )

    return parser.parse_args()


def read_grid(ds):
    required = {"valid_time", "latitude", "longitude"}

    if not required.issubset(ds.coords):
        raise ValueError("Missing required ERA5 coordinates")

    if "t2m" not in ds:
        raise ValueError("Missing t2m variable")

    temperature = ds["t2m"].transpose(
        "valid_time",
        "latitude",
        "longitude",
    )

    if temperature.attrs.get("units") != "K":
        raise ValueError("Expected temperature units: K")

    latitudes = temperature.latitude.values.copy()
    longitudes = temperature.longitude.values.copy()

    return temperature, latitudes, longitudes


def create_spatial_mask(latitudes, longitudes, boundaries):
    world = gpd.read_file(boundaries)

    if world.crs is None:
        raise ValueError("Boundary CRS is missing")

    world = world.to_crs("EPSG:4326")

    if "CONTINENT" not in world.columns:
        raise ValueError("Missing CONTINENT field")

    europe = world.loc[
        world["CONTINENT"] == "Europe"
    ]

    if europe.empty:
        raise ValueError("No European polygons found")

    geometry = europe.geometry.union_all()

    lon_grid, lat_grid = np.meshgrid(
        longitudes,
        latitudes,
    )

    mask = shapely.intersects_xy(
        geometry,
        lon_grid,
        lat_grid,
    )

    if not mask.any():
        raise ValueError("No cells inside study area")

    weights = np.cos(
        np.deg2rad(lat_grid)
    )

    return mask, weights, lat_grid, lon_grid


def process_temperature(temperature, mask, weights):
    rows = []

    for index, timestamp in enumerate(
        temperature.valid_time.values
    ):
        day = (
            temperature.isel(valid_time=index)
            .values.astype(np.float64)
            - 273.15
        )

        valid = mask & np.isfinite(day)

        if not valid.any():
            raise ValueError(
                f"No valid observations: {timestamp}"
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

    if not rows:
        raise ValueError("Input contains no observation days")

    return pd.DataFrame(rows)


def write_csv_atomic(dataframe, output_path):
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_path = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".csv",
            prefix=".era5_tmp_",
            dir=output_path.parent,
            delete=False,
            encoding="utf-8",
            newline="",
        ) as temporary:
            temporary_path = Path(temporary.name)
            dataframe.to_csv(temporary, index=False)

        os.replace(temporary_path, output_path)

    finally:
        if (
            temporary_path is not None
            and temporary_path.exists()
        ):
            temporary_path.unlink()


def main():
    args = parse_args()

    paths = [*args.input, args.boundaries]

    for path in paths:
        if not path.is_file():
            raise FileNotFoundError(
                f"File not found: {path}"
            )

    resolved_paths = [
        path.resolve() for path in args.input
    ]

    if len(set(resolved_paths)) != len(resolved_paths):
        raise ValueError(
            "The same input file was provided more than once"
        )

    print("=== OPTIMIZED ERA5 PIPELINE ===", flush=True)

    reference_latitudes = None
    reference_longitudes = None

    mask = None
    weights = None
    lat_grid = None
    lon_grid = None

    results = []

    for index, path in enumerate(args.input, start=1):
        print(
            f"\n[{index}/{len(args.input)}] {path}",
            flush=True,
        )

        with xr.open_dataset(path) as ds:
            temperature, latitudes, longitudes = read_grid(ds)

            if reference_latitudes is None:
                reference_latitudes = latitudes
                reference_longitudes = longitudes

                print("Generating geographic mask once...")

                mask, weights, lat_grid, lon_grid = (
                    create_spatial_mask(
                        latitudes,
                        longitudes,
                        args.boundaries,
                    )
                )

                print(
                    f"Selected grid cells: {int(mask.sum()):,}"
                )

            else:
                if (
                    not np.array_equal(
                        latitudes, reference_latitudes
                    )
                    or not np.array_equal(
                        longitudes, reference_longitudes
                    )
                ):
                    raise ValueError(
                        "Input files have incompatible geographic grids"
                    )

            result = process_temperature(
                temperature,
                mask,
                weights,
            )

            results.append(result)

            print(f"Processed days: {len(result)}")

    combined = pd.concat(
        results,
        ignore_index=True,
    )

    duplicates = combined.loc[
        combined["date"].duplicated(keep=False),
        "date",
    ].drop_duplicates()

    if not duplicates.empty:
        raise ValueError(
            "Duplicate dates across input files: "
            + ", ".join(map(str, sorted(duplicates)))
        )

    combined = combined.sort_values(
        "date"
    ).reset_index(drop=True)

    # Write outputs only after processing and validation.
    if args.mask_output is not None:
        mask_df = pd.DataFrame({
            "latitude": lat_grid.ravel(),
            "longitude": lon_grid.ravel(),
            "in_study_area": mask.ravel(),
        })

        write_csv_atomic(
            mask_df,
            args.mask_output,
        )

    write_csv_atomic(
        combined,
        args.output,
    )

    print("\n=== PROCESSING SUMMARY ===")
    print(f"Files processed: {len(args.input)}")
    print(f"Total days: {len(combined)}")
    print(f"First date: {combined['date'].min()}")
    print(f"Last date: {combined['date'].max()}")
    print(f"Output: {args.output}")
    print("\n=== PIPELINE COMPLETED SUCCESSFULLY ===")


if __name__ == "__main__":
    main()
