
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely
import xarray as xr

BOUNDARIES = Path(
    "data/raw/boundaries/ne_50m_admin_0_countries.zip"
)
ERA5_DIR = Path("data/raw/era5")
OUTPUT = Path("data/processed/study_area_mask_50m_preview.csv")


def main():
    # Load the source boundaries.
    world = gpd.read_file(BOUNDARIES).to_crs("EPSG:4326")

    # Provisional definition, not the final study area.
    europe = world.loc[world["CONTINENT"] == "Europe"]

    if europe.empty:
        raise ValueError("No European polygons found")

    geometry = europe.geometry.union_all()

    # Load the sample ERA5 grid.
    files = sorted(ERA5_DIR.glob("*.nc"))

    if len(files) != 1:
        raise ValueError(
            f"Expected one NetCDF sample, found {len(files)}"
        )

    with xr.open_dataset(files[0]) as ds:
        latitudes = ds["latitude"].values
        longitudes = ds["longitude"].values

    lon_grid, lat_grid = np.meshgrid(
        longitudes,
        latitudes,
        indexing="xy",
    )

    # Classify grid-cell centres.
    mask = shapely.intersects_xy(
        geometry,
        lon_grid,
        lat_grid,
    )

    result = pd.DataFrame({
        "latitude": lat_grid.ravel(),
        "longitude": lon_grid.ravel(),
        "in_study_area": mask.ravel(),
    })

    # Basic validation.
    assert len(result) == len(latitudes) * len(longitudes)
    assert not result.duplicated(
        ["latitude", "longitude"]
    ).any()

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUTPUT, index=False)

    selected = int(result["in_study_area"].sum())

    print("=== STUDY AREA MASK ===")
    print("Boundary source: Natural Earth 50m")
    print("Selection: CONTINENT == Europe")
    print("Total cells:", len(result))
    print("Selected cells:", selected)
    print("Excluded cells:", len(result) - selected)
    print("Output:", OUTPUT)


if __name__ == "__main__":
    main()
