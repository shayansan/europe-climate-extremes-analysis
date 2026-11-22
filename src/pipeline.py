
import argparse
import os
import tempfile
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely
import xarray as xr


DEFAULT_BOUNDARIES = Path(
    "data/raw/boundaries/ne_50m_admin_0_countries.zip"
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Process ERA5 daily temperature statistics."
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
        "--statistic",
        choices=["tmax", "tmean"],
        default="tmax",
        help="Input temperature statistic",
    )

    parser.add_argument(
        "--boundaries",
        type=Path,
        default=DEFAULT_BOUNDARIES,
        help="Natural Earth boundaries for legacy mode",
    )

    parser.add_argument(
        "--study-area",
        type=Path,
        default=None,
        help="Optional custom study-area GeoJSON",
    )

    parser.add_argument(
        "--mask-output",
        type=Path,
        default=None,
        help="Optional CSV containing the geographic mask",
    )

    return parser.parse_args()


def read_grid(ds):
    required_coordinates = {
        "valid_time",
        "latitude",
        "longitude",
    }

    if not required_coordinates.issubset(ds.coords):
        raise ValueError(
            "Missing required ERA5 coordinates"
        )

    if "t2m" not in ds:
        raise ValueError("Missing t2m variable")

    temperature = ds["t2m"].transpose(
        "valid_time",
        "latitude",
        "longitude",
    )

    if temperature.attrs.get("units") != "K":
        raise ValueError(
            "Expected temperature units: K"
        )

    latitudes = temperature.latitude.values.copy()
    longitudes = temperature.longitude.values.copy()

    if latitudes.size == 0 or longitudes.size == 0:
        raise ValueError("Empty geographic grid")

    return temperature, latitudes, longitudes


def load_study_geometry(boundaries, study_area):
    if study_area is not None:
        if not study_area.is_file():
            raise FileNotFoundError(study_area)

        geographic = gpd.read_file(study_area)

        if len(geographic) != 1:
            raise ValueError(
                "Study-area file must contain exactly one feature"
            )

        if geographic.crs is None:
            raise ValueError(
                "Study-area CRS is missing"
            )

        geographic = geographic.to_crs("EPSG:4326")

        geometry = geographic.geometry.iloc[0]

        print("Geographic mode: custom study area")
        print("Study area:", study_area)

    else:
        if not boundaries.is_file():
            raise FileNotFoundError(boundaries)

        world = gpd.read_file(boundaries)

        if world.crs is None:
            raise ValueError(
                "Boundary CRS is missing"
            )

        world = world.to_crs("EPSG:4326")

        if "CONTINENT" not in world.columns:
            raise ValueError(
                "Missing CONTINENT field"
            )

        europe = world.loc[
            world["CONTINENT"] == "Europe"
        ]

        if europe.empty:
            raise ValueError(
                "No European polygons found"
            )

        geometry = europe.geometry.union_all()

        print("Geographic mode: legacy Natural Earth")

    if geometry is None or geometry.is_empty:
        raise ValueError(
            "Study-area geometry is empty"
        )

    if not geometry.is_valid:
        raise ValueError(
            "Study-area geometry is invalid"
        )

    return geometry


def create_spatial_mask(
    latitudes,
    longitudes,
    geometry,
):
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
        raise ValueError(
            "No grid cells inside study area"
        )

    weights = np.cos(
        np.deg2rad(lat_grid)
    )

    if not np.all(
        np.isfinite(weights[mask])
    ):
        raise ValueError(
            "Non-finite spatial weights"
        )

    if np.any(weights[mask] <= 0):
        raise ValueError(
            "Spatial weights must be positive"
        )

    return mask, weights, lat_grid, lon_grid


def process_temperature(
    temperature,
    mask,
    weights,
    statistic,
):
    rows = []

    mean_column = (
        f"weighted_mean_{statistic}_c"
    )

    if statistic == "tmax":
        maximum_column = "maximum_tmax_c"
    else:
        maximum_column = "maximum_gridcell_tmean_c"

    for index, timestamp in enumerate(
        temperature.valid_time.values
    ):
        day = (
            temperature.isel(valid_time=index)
            .values.astype(np.float64)
            - 273.15
        )

        valid = (
            mask
            & np.isfinite(day)
        )

        if not valid.any():
            raise ValueError(
                f"No valid observations: {timestamp}"
            )

        values = day[valid]
        day_weights = weights[valid]

        weighted_mean = float(
            np.average(
                values,
                weights=day_weights,
            )
        )

        maximum_value = float(
            values.max()
        )

        rows.append(
            {
                "date": pd.Timestamp(timestamp).date(),
                "valid_cells": int(valid.sum()),
                mean_column: round(
                    weighted_mean,
                    3,
                ),
                maximum_column: round(
                    maximum_value,
                    3,
                ),
            }
        )

    if not rows:
        raise ValueError(
            "Input contains no observation days"
        )

    return pd.DataFrame(rows)


def write_csv_atomic(
    dataframe,
    output_path,
):
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_path = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            suffix=".csv",
            prefix=".era5_tmp_",
            dir=output_path.parent,
            delete=False,
        ) as temporary:
            temporary_path = Path(
                temporary.name
            )

            dataframe.to_csv(
                temporary,
                index=False,
            )

        os.replace(
            temporary_path,
            output_path,
        )

    finally:
        if (
            temporary_path is not None
            and temporary_path.exists()
        ):
            temporary_path.unlink()


def main():
    args = parse_args()

    resolved_inputs = [
        path.resolve()
        for path in args.input
    ]

    if len(set(resolved_inputs)) != len(resolved_inputs):
        raise ValueError(
            "Duplicate input file paths"
        )

    for path in args.input:
        if not path.is_file():
            raise FileNotFoundError(path)

    print(
        "=== ERA5 TEMPERATURE PIPELINE ===",
        flush=True,
    )

    print("Statistic:", args.statistic)
    print("Number of files:", len(args.input))

    geometry = load_study_geometry(
        args.boundaries,
        args.study_area,
    )

    reference_latitudes = None
    reference_longitudes = None

    mask = None
    weights = None
    lat_grid = None
    lon_grid = None

    results = []

    for index, path in enumerate(
        args.input,
        start=1,
    ):
        print(
            f"\n[{index}/{len(args.input)}] {path}",
            flush=True,
        )

        with xr.open_dataset(path) as ds:
            (
                temperature,
                latitudes,
                longitudes,
            ) = read_grid(ds)

            if reference_latitudes is None:
                reference_latitudes = latitudes
                reference_longitudes = longitudes

                print(
                    "Generating geographic mask once...",
                    flush=True,
                )

                (
                    mask,
                    weights,
                    lat_grid,
                    lon_grid,
                ) = create_spatial_mask(
                    latitudes,
                    longitudes,
                    geometry,
                )

                print(
                    "Selected grid cells:",
                    int(mask.sum()),
                )

            else:
                latitude_matches = np.array_equal(
                    latitudes,
                    reference_latitudes,
                )

                longitude_matches = np.array_equal(
                    longitudes,
                    reference_longitudes,
                )

                if not (
                    latitude_matches
                    and longitude_matches
                ):
                    raise ValueError(
                        "Input files have incompatible geographic grids"
                    )

            result = process_temperature(
                temperature,
                mask,
                weights,
                args.statistic,
            )

            results.append(result)

            print(
                "Processed days:",
                len(result),
            )

    combined = pd.concat(
        results,
        ignore_index=True,
    )

    duplicate_dates = combined.loc[
        combined["date"].duplicated(
            keep=False
        ),
        "date",
    ].drop_duplicates()

    if not duplicate_dates.empty:
        raise ValueError(
            "Duplicate dates across input files: "
            + ", ".join(
                map(
                    str,
                    sorted(duplicate_dates),
                )
            )
        )

    combined = (
        combined.sort_values("date")
        .reset_index(drop=True)
    )

    if args.mask_output is not None:
        mask_dataframe = pd.DataFrame(
            {
                "latitude": lat_grid.ravel(),
                "longitude": lon_grid.ravel(),
                "in_study_area": mask.ravel(),
            }
        )

        write_csv_atomic(
            mask_dataframe,
            args.mask_output,
        )

    write_csv_atomic(
        combined,
        args.output,
    )

    print(
        "\n=== PROCESSING SUMMARY ==="
    )

    print("Statistic:", args.statistic)
    print(
        "Files processed:",
        len(args.input),
    )
    print("Total days:", len(combined))
    print(
        "First date:",
        combined["date"].min(),
    )
    print(
        "Last date:",
        combined["date"].max(),
    )
    print("Output:", args.output)

    print(
        "\n=== PIPELINE COMPLETED SUCCESSFULLY ==="
    )


if __name__ == "__main__":
    main()
