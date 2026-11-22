
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely
import xarray as xr
from shapely.geometry import Point
from shapely.ops import split


COUNTRIES = Path(
    "data/raw/boundaries/ne_50m_admin_0_countries.zip"
)

BORDER = Path(
    "data/raw/boundaries/asia_europe_border.geojson"
)

ERA5 = Path(
    "data/raw/era5/9831f09756389bd31899fc3ddad5aa5c.nc"
)

OUTPUT = Path(
    "data/processed/refined_europe_mask_preview.csv"
)


def country_geometry(world, name):
    rows = world.loc[world["ADMIN"] == name]

    if rows.empty:
        raise ValueError(f"Country not found: {name}")

    return rows.geometry.union_all()


def find_part(parts, longitude, latitude, label):
    point = Point(longitude, latitude)

    matches = [
        part for part in parts
        if part.covers(point)
    ]

    if len(matches) != 1:
        raise ValueError(
            f"{label}: expected one polygon, found {len(matches)}"
        )

    return matches[0]


def split_into_polygons(geometry, dividing_line):
    return [
        part
        for part in split(geometry, dividing_line).geoms
        if part.geom_type == "Polygon"
        and not part.is_empty
    ]


def main():
    for path in (COUNTRIES, BORDER, ERA5):
        if not path.is_file():
            raise FileNotFoundError(path)

    world = gpd.read_file(COUNTRIES).to_crs("EPSG:4326")
    lines = gpd.read_file(BORDER).to_crs("EPSG:4326")
    dividing_line = lines.geometry.union_all()

    # Original country-based study area.
    original = world.loc[
        world["CONTINENT"] == "Europe"
    ].geometry.union_all()

    # European countries except full Russian territory.
    other_europe = world.loc[
        (world["CONTINENT"] == "Europe")
        & (world["ADMIN"] != "Russia")
    ].geometry.union_all()

    russia = country_geometry(world, "Russia")
    turkey = country_geometry(world, "Turkey")

    russian_parts = split_into_polygons(
        russia, dividing_line
    )

    turkish_parts = split_into_polygons(
        turkey, dividing_line
    )

    # Identify geographic components by reference points,
    # never by unstable polygon indices.
    moscow_part = find_part(
        russian_parts, 37.6173, 55.7558, "Moscow"
    )

    kaliningrad_part = find_part(
        russian_parts, 20.5, 54.7, "Kaliningrad"
    )

    crimea_part = find_part(
        russian_parts, 34.10, 44.95, "Crimea"
    )

    thrace_part = find_part(
        turkish_parts, 26.5557, 41.6772, "Edirne"
    )

    selected_parts = [
        other_europe,
        moscow_part,
        kaliningrad_part,
        crimea_part,
        thrace_part,
    ]

    refined = shapely.union_all(selected_parts)

    if not refined.is_valid or refined.is_empty:
        raise ValueError("Invalid refined study-area geometry")

    reference_checks = {
        "Moscow": (37.6173, 55.7558, True),
        "Saint Petersburg": (30.3158, 59.9343, True),
        "Kaliningrad": (20.5, 54.7, True),
        "Simferopol": (34.10, 44.95, True),
        "Edirne": (26.5557, 41.6772, True),
        "Novosibirsk": (82.9204, 55.0302, False),
        "Ankara": (32.8597, 39.9334, False),
        "Rome": (12.4964, 41.9028, True),
        "Berlin": (13.4050, 52.5200, True),
    }

    print("=== GEOGRAPHIC REFERENCE CHECKS ===")

    for name, (lon, lat, expected) in reference_checks.items():
        actual = refined.covers(Point(lon, lat))

        if actual != expected:
            raise ValueError(f"Reference check failed: {name}")

        print(f"{name}: PASS")

    with xr.open_dataset(ERA5) as ds:
        latitudes = ds.latitude.values
        longitudes = ds.longitude.values

    lon_grid, lat_grid = np.meshgrid(
        longitudes, latitudes
    )

    original_mask = shapely.intersects_xy(
        original, lon_grid, lat_grid
    )

    refined_mask = shapely.intersects_xy(
        refined, lon_grid, lat_grid
    )

    added = refined_mask & ~original_mask
    removed = original_mask & ~refined_mask

    result = pd.DataFrame({
        "latitude": lat_grid.ravel(),
        "longitude": lon_grid.ravel(),
        "original_mask": original_mask.ravel(),
        "refined_mask": refined_mask.ravel(),
        "added": added.ravel(),
        "removed": removed.ravel(),
    })

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUTPUT, index=False)

    print("\n=== REFINED MASK COMPARISON ===")
    print("Total cells:", refined_mask.size)
    print("Original selected:", int(original_mask.sum()))
    print("Refined selected:", int(refined_mask.sum()))
    print("Added:", int(added.sum()))
    print("Removed:", int(removed.sum()))
    print(
        "Net change:",
        int(refined_mask.sum() - original_mask.sum()),
    )
    print("Output:", OUTPUT)


if __name__ == "__main__":
    main()
