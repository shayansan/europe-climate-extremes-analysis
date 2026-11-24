"""
Dataset: ERA5 reanalysis data (ECMWF / Copernicus Climate Data Store)
Download Source: Copernicus CDS API (https://cds.climate.copernicus.eu/)
Integration Note: Processes ERA5 NetCDF files (including the repository's validated
                  July 2020 sample or multi-year extracts) into area-weighted
                  regional summaries for downstream statistical analysis.
Expected Output CSV Schema:
    - region (str): Geographic sub-region ('Southern Europe' or 'Northern Europe')
    - year (int): Calendar year extracted from dataset timestamps (e.g., 2020)
    - weighted_mean_temp_c (float): Cosine-latitude area-weighted mean 2m temperature (°C)
    - max_temp_c (float): Peak single-observation 2m temperature intensity (°C)
    - min_temp_c (float): Minimum single-observation 2m temperature (°C)
    - weighted_std_temp_c (float): Cosine-latitude area-weighted temperature std dev (°C)
    - valid_obs_count (int): Number of non-null grid-time observations in group
"""
import argparse
from pathlib import Path
import numpy as np
import xarray as xr
import pandas as pd

DEFAULT_INPUT_PATH = Path("src/data/raw/era5/9831f09756389bd31899fc3ddad5aa5c.nc")
DEFAULT_OUTPUT_PATH = Path("data/processed/european_heat_summary.csv")
DEFAULT_LAT_SPLIT = 45.0

def parse_args() -> argparse.Namespace:
    """Parse configurable command-line arguments for input/output paths and parameters."""
    parser = argparse.ArgumentParser(
        description="Process ERA5 NetCDF 2m temperature data into area-weighted regional summaries."
    )
    parser.add_argument(
        "-i",
        "--input",
        type=Path,
        default=DEFAULT_INPUT_PATH,
        help=f"Path to input ERA5 NetCDF (.nc) file (default: {DEFAULT_INPUT_PATH})",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help=f"Path to output summary CSV file (default: {DEFAULT_OUTPUT_PATH})",
    )
    parser.add_argument(
        "--lat-split",
        type=float,
        default=DEFAULT_LAT_SPLIT,
        help="Latitude threshold (°N) separating Southern and Northern Europe (default: 45.0).",
    )
    return parser.parse_args()

def validate_dataset(ds: xr.Dataset) -> str:
    """
    Validate required variables, spatial/temporal coverage, and return the time coordinate name.
    """
    if "t2m" not in ds.data_vars:
        raise KeyError(f"Required variable 't2m' not found. Available variables: {list(ds.data_vars)}")

    time_col = "valid_time" if "valid_time" in ds.coords else "time"
    required_coords = {"latitude", "longitude", time_col}
    missing_coords = required_coords - set(ds.coords)
    if missing_coords:
        raise KeyError(f"Missing required coordinates: {missing_coords}")

    lat_min, lat_max = float(ds["latitude"].min()), float(ds["latitude"].max())
    lon_min, lon_max = float(ds["longitude"].min()), float(ds["longitude"].max())
    time_values = pd.to_datetime(ds[time_col].values)

    if not (-90.0 <= lat_min <= lat_max <= 90.0):
        raise ValueError(f"Invalid latitude bounds: [{lat_min}, {lat_max}]")
    if not (-180.0 <= lon_min <= lon_max <= 360.0):
        raise ValueError(f"Invalid longitude bounds: [{lon_min}, {lon_max}]")

    print("\nDataset Coverage Summary:")
    print(f"  Time range:      {time_values.min()} to {time_values.max()} ({len(time_values)} steps)")
    print(f"  Latitude range:  {lat_min:.2f}° to {lat_max:.2f}°")
    print(f"  Longitude range: {lon_min:.2f}° to {lon_max:.2f}°")

    return time_col

def convert_t2m_to_celsius(da: xr.DataArray) -> xr.DataArray:
    """
    Validate temperature units from NetCDF metadata and convert to degrees Celsius.
    """
    raw_units = str(da.attrs.get("units", "")).strip()

    if raw_units in {"K", "kelvin", "Kelvin"}:
        da_c = da - 273.15
    elif raw_units in {"C", "degC", "celsius", "Celsius", "°C"}:
        da_c = da.copy()
    else:
        # Fallback heuristic if metadata attribute is stripped during intermediate exports
        median_val = float(da.median())
        if median_val > 150.0:
            print(f"  [Warning] 'units' attribute missing/unrecognized ('{raw_units}'). "
                  f"Median={median_val:.2f} indicates Kelvin; converting to °C.")
            da_c = da - 273.15
        else:
            print(f"  [Warning] 'units' attribute missing/unrecognized ('{raw_units}'). "
                  f"Median={median_val:.2f} indicates Celsius; keeping values as-is.")
            da_c = da.copy()

    da_c.attrs["units"] = "degC"
    return da_c

def weighted_stats(group: pd.DataFrame) -> pd.Series:
    """
    Compute cosine-latitude area-weighted mean and standard deviation alongside
    unweighted extremes (max/min temperature intensity).
    """
    temps = group["temperature_celsius"].to_numpy()
    weights = group["spatial_weight"].to_numpy()

    w_mean = np.average(temps, weights=weights)
    w_var = np.average((temps - w_mean) ** 2, weights=weights)
    w_std = np.sqrt(w_var)

    return pd.Series(
        {
            "weighted_mean_temp_c": round(float(w_mean), 4),
            "max_temp_c": round(float(np.max(temps)), 4),
            "min_temp_c": round(float(np.min(temps)), 4),
            "weighted_std_temp_c": round(float(w_std), 4),
            "valid_obs_count": int(len(temps)),
        }
    )

def main() -> None:
    args = parse_args()

    if not args.input.exists():
        raise FileNotFoundError(f"Input NetCDF file not found at: {args.input}")

    print("--- Starting Climate Data Processing Pipeline ---")
    print(f"Input file:  {args.input}")
    print(f"Output file: {args.output}")

    with xr.open_dataset(args.input) as ds:
        time_col = validate_dataset(ds)
        t2m_celsius = convert_t2m_to_celsius(ds["t2m"])
        df = t2m_celsius.rename("temperature_celsius").to_dataframe().reset_index()

    # Data quality checks
    print("\n" + "=" * 45)
    print("DATA QUALITY SUMMARY REPORT")
    print("=" * 45)

    rows_before_clean = len(df)
    missing_count = int(df["temperature_celsius"].isnull().sum())
    duplicate_count = int(df.duplicated().sum())

    df_cleaned = df.dropna(subset=["temperature_celsius"]).drop_duplicates().copy()
    rows_after_clean = len(df_cleaned)

    print(f"Record count before cleaning: {rows_before_clean:,}")
    print(f"Record count after cleaning:  {rows_after_clean:,}")
    print(f"Missing temperature values:   {missing_count:,}")
    print(f"Duplicate rows removed:       {duplicate_count:,}")
    print(
        f"Temperature Range (Celsius):  Min = {df_cleaned['temperature_celsius'].min():.2f}°C, "
        f"Max = {df_cleaned['temperature_celsius'].max():.2f}°C"
    )

    # Physical plausibility check (-90°C to +60°C for surface air temperature)
    if (df_cleaned["temperature_celsius"] < -90.0).any() or (df_cleaned["temperature_celsius"] > 60.0).any():
        raise ValueError("Temperature values outside physically plausible surface range (-90°C to 60°C).")

    # Temporal & Spatial Preparation
    df_cleaned["year"] = pd.to_datetime(df_cleaned[time_col]).dt.year

    # Geographic Sub-region Classification:
    # Uses a configurable latitude threshold (default 45°N) as a broad climatic proxy
    # separating Mediterranean/Southern Europe from Continental/Northern Europe.
    # Note: Country/mask polygons can replace this threshold if sub-national boundaries are required.
    df_cleaned["region"] = np.where(
        df_cleaned["latitude"] < args.lat_split,
        "Southern Europe",
        "Northern Europe",
    )

    # Cosine-latitude weights correct for meridian convergence on regular lat/lon grids
    df_cleaned["spatial_weight"] = np.cos(np.deg2rad(df_cleaned["latitude"]))

    # Aggregation:
    # - weighted_mean_temp_c: area-weighted baseline temperature
    # - max_temp_c: peak single-timestep temperature intensity (NOT a count/frequency of multi-day heatwaves)
    # - min_temp_c: minimum single-timestep temperature
    # - weighted_std_temp_c: area-weighted spatial/temporal temperature dispersion
    summary_df = (
        df_cleaned.groupby(["region", "year"], sort=True)
        .apply(weighted_stats, include_groups=False)
        .reset_index()
    )

    # Enforce deterministic column order and types for downstream analysis
    expected_columns = [
        "region",
        "year",
        "weighted_mean_temp_c",
        "max_temp_c",
        "min_temp_c",
        "weighted_std_temp_c",
        "valid_obs_count",
    ]
    summary_df = summary_df[expected_columns]
    summary_df["year"] = summary_df["year"].astype(int)
    summary_df["valid_obs_count"] = summary_df["valid_obs_count"].astype(int)

    print("\nProcessed Summary Preview:")
    print(summary_df.to_string(index=False))

    # Export to configured output path
    args.output.parent.mkdir(parents=True, exist_ok=True)
    summary_df.to_csv(args.output, index=False)
    print(f"\nSuccessfully exported analysis-ready dataset to '{args.output}'!")
    print("=" * 45)


if __name__ == "__main__":
    main()
