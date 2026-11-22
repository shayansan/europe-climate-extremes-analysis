
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely
from shapely.geometry import Point

from src.data_processing.build_refined_europe_mask import (
    COUNTRIES,
    BORDER,
    country_geometry,
    find_part,
    split_into_polygons,
)


OUTPUT = Path(
    "data/processed/europe_coverage_diagnostics.csv"
)

AREAS = {
    "old": [72, -25, 34, 45],
    "candidate": [82, -26, 34, 70],
}

REFERENCE_POINTS = {
    "Moscow": (37.6173, 55.7558, True),
    "Saint Petersburg": (30.3158, 59.9343, True),
    "Kaliningrad": (20.5, 54.7, True),
    "Simferopol": (34.10, 44.95, True),
    "Edirne": (26.5557, 41.6772, True),
    "Rome": (12.4964, 41.9028, True),
    "Berlin": (13.4050, 52.5200, True),
    "Novosibirsk": (82.9204, 55.0302, False),
    "Ankara": (32.8597, 39.9334, False),
}


def create_geometry():
    world = gpd.read_file(COUNTRIES).to_crs("EPSG:4326")
    borders = gpd.read_file(BORDER).to_crs("EPSG:4326")

    dividing_line = borders.geometry.union_all()

    original = world.loc[
        world["CONTINENT"] == "Europe"
    ].geometry.union_all()

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

    selected_parts = [
        other_europe,
        find_part(
            russian_parts, 37.6173, 55.7558, "Moscow"
        ),
        find_part(
            russian_parts, 20.5, 54.7, "Kaliningrad"
        ),
        find_part(
            russian_parts, 34.10, 44.95, "Crimea"
        ),
        find_part(
            turkish_parts, 26.5557, 41.6772, "Edirne"
        ),
    ]

    refined = shapely.union_all(selected_parts)

    if refined.is_empty or not refined.is_valid:
        raise ValueError("Invalid refined Europe geometry")

    return original, refined


def create_grid(area):
    north, west, south, east = area

    latitudes = np.linspace(
        north,
        south,
        round((north - south) / 0.25) + 1,
    )

    longitudes = np.linspace(
        west,
        east,
        round((east - west) / 0.25) + 1,
    )

    return np.meshgrid(longitudes, latitudes)


def evaluate_area(name, area, original, refined):
    lon_grid, lat_grid = create_grid(area)

    original_mask = shapely.intersects_xy(
        original, lon_grid, lat_grid
    )

    refined_mask = shapely.intersects_xy(
        refined, lon_grid, lat_grid
    )

    added = refined_mask & ~original_mask
    removed = original_mask & ~refined_mask

    print(f"\n=== {name.upper()} ===")
    print("Total grid cells:", refined_mask.size)
    print("Original selected:", int(original_mask.sum()))
    print("Refined selected:", int(refined_mask.sum()))
    print("Added:", int(added.sum()))
    print("Removed:", int(removed.sum()))

    if name == "candidate":
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

        print("\nSelected cells on bounding-box edges:")

        edge_masks = {
            "north": refined_mask[0, :],
            "south": refined_mask[-1, :],
            "west": refined_mask[:, 0],
            "east": refined_mask[:, -1],
        }

        for edge, values in edge_masks.items():
            print(f"{edge}: {int(values.sum())}")

        print("\nDiagnostic CSV:", OUTPUT)

    return int(refined_mask.sum())


def main():
    for path in (COUNTRIES, BORDER):
        if not path.is_file():
            raise FileNotFoundError(path)

    print("=== EUROPE SPATIAL COVERAGE VALIDATION ===")

    original, refined = create_geometry()

    print("\n=== REFERENCE LOCATIONS ===")

    for name, (lon, lat, expected) in REFERENCE_POINTS.items():
        actual = refined.covers(Point(lon, lat))

        if actual != expected:
            raise ValueError(
                f"{name}: expected {expected}, got {actual}"
            )

        print(f"{name}: PASS")

    old_count = evaluate_area(
        "old", AREAS["old"], original, refined
    )

    candidate_count = evaluate_area(
        "candidate",
        AREAS["candidate"],
        original,
        refined,
    )

    print("\n=== COMPARISON ===")
    print("Old selected:", old_count)
    print("Candidate selected:", candidate_count)
    print("Additional selected cells:", candidate_count - old_count)
    print(
        "Selected-cell increase:",
        f"{candidate_count / old_count:.2f}x",
    )

    print("\nCoverage diagnostic completed.")
    print("Scientific boundary approval is still pending.")


if __name__ == "__main__":
    main()
