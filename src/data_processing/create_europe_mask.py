
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely
import xarray as xr

BOUNDARIES = Path(
    "data/raw/boundaries/ne_110m_admin_0_countries.zip"
)
ERA5_DIR = Path("data/raw/era5")
OUTPUT = Path("data/processed/europe_mask_preview.csv")


def main():
    # 1. Load geographic boundaries
    world = gpd.read_file(BOUNDARIES)

    if world.crs is None:
        raise ValueError("Boundary CRS is missing")

    world = world.to_crs("EPSG:4326")

    # Provisional country-based definition of Europe
    europe = world[world["CONTINENT"] == "Europe"].copy()

    # Combine European country polygons
    europe_geometry = europe.geometry.union_all()

    # 2. Load ERA5 geographic grid
    files = sorted(ERA5_DIR.glob("*.nc"))

    if len(files) != 1:
        raise ValueError(
            f"Expected exactly one ERA5 sample; found {len(files)}"
        )

    with xr.open_dataset(files[0]) as ds:
        latitudes = ds.latitude.values
        longitudes = ds.longitude.values

    # 3. Create coordinate grid
    longitude_grid, latitude_grid = np.meshgrid(
        longitudes,
        latitudes,
        indexing="xy",
    )

    # 4. Check whether each point is inside Europe
    mask = shapely.contains_xy(
        europe_geometry,
        longitude_grid,
        latitude_grid,
    )

    # 5. Count selected and excluded grid cells
    total = mask.size
    selected = int(mask.sum())
    excluded = total - selected

    print("=== EUROPE GEOGRAPHIC MASK ===")
    print(f"Total ERA5 cells: {total:,}")
    print(f"Selected cells: {selected:,}")
    print(f"Excluded cells: {excluded:,}")
    print(f"Selected percentage: {selected / total:.2%}")

    # 6. Verify known locations
    print("\nLocation checks:")

    locations = {
        "Rome, Italy": (12.50, 41.90),
        "Iraq": (44.75, 34.00),
    }

    for name, (lon, lat) in locations.items():
        included = bool(
            shapely.contains_xy(europe_geometry, lon, lat)
        )
        print(f"{name}: {'Included' if included else 'Excluded'}")

    assert shapely.contains_xy(
        europe_geometry, 12.50, 41.90
    ), "Rome should be included"

    assert not shapely.contains_xy(
        europe_geometry, 44.75, 34.00
    ), "Iraq should be excluded"

    # 7. Export grid mask for inspection
    result = pd.DataFrame({
        "latitude": latitude_grid.ravel(),
        "longitude": longitude_grid.ravel(),
        "in_europe_preview": mask.ravel(),
    })

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUTPUT, index=False)

    print(f"\nMask preview saved to: {OUTPUT}")


if __name__ == "__main__":
    main()
