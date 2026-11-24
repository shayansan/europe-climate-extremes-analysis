
from pathlib import Path

import geopandas as gpd
import numpy as np
import shapely
from shapely.geometry import Point, box

from src.data_processing.build_refined_europe_mask import (
    COUNTRIES,
    BORDER,
    country_geometry,
    split_into_polygons,
)

from src.data_processing.validate_europe_coverage import (
    AREAS,
    create_grid,
)


INPUT = Path(
    "data/processed/geography/"
    "europe_geographic_candidate_v1.geojson"
)

OUTPUT = Path(
    "data/processed/geography/"
    "europe_geographic_candidate_v2.geojson"
)

ARCTIC_ISLANDS = {
    "Novaya Zemlya North": (58.80, 75.15),
    "Novaya Zemlya South": (53.39, 71.96),
    "Vaygach": (49.17, 69.11),
}


def load_island_geometries():
    world = gpd.read_file(COUNTRIES).to_crs("EPSG:4326")
    borders = gpd.read_file(BORDER).to_crs("EPSG:4326")

    russia = country_geometry(world, "Russia")

    parts = split_into_polygons(
        russia,
        borders.geometry.union_all(),
    )

    selected = {}

    for name, (longitude, latitude) in ARCTIC_ISLANDS.items():
        point = Point(longitude, latitude)

        matches = [
            polygon
            for polygon in parts
            if polygon.covers(point)
        ]

        if len(matches) != 1:
            raise ValueError(
                f"{name}: expected one polygon, "
                f"found {len(matches)}"
            )

        selected[name] = matches[0]

    return selected


def main():
    if not INPUT.is_file():
        raise FileNotFoundError(INPUT)

    frame = gpd.read_file(INPUT).to_crs("EPSG:4326")

    if len(frame) != 1:
        raise ValueError("Expected one V1 study-area feature")

    previous = frame.geometry.iloc[0]

    if not previous.is_valid:
        raise ValueError("Invalid V1 geometry")

    islands = load_island_geometries()

    north, west, south, east = AREAS["candidate"]
    bbox = box(west, south, east, north)

    updated = shapely.union_all(
        [previous, *islands.values()]
    ).intersection(bbox)

    if updated.is_empty or not updated.is_valid:
        raise ValueError("Invalid V2 geometry")

    lon_grid, lat_grid = create_grid(AREAS["candidate"])

    old_mask = shapely.intersects_xy(
        previous,
        lon_grid,
        lat_grid,
    )

    new_mask = shapely.intersects_xy(
        updated,
        lon_grid,
        lat_grid,
    )

    added = new_mask & ~old_mask
    removed = old_mask & ~new_mask

    print("=== EUROPE CANDIDATE V2 ===")
    print("Grid cells:", old_mask.size)
    print("V1 selected:", int(old_mask.sum()))
    print("V2 selected:", int(new_mask.sum()))
    print("New cells:", int(added.sum()))
    print("Removed cells:", int(removed.sum()))

    if removed.any():
        raise ValueError(
            "V2 unexpectedly removed V1 grid cells"
        )

    expected_additions = np.zeros_like(old_mask)

    print("\n=== ISLAND CONTRIBUTIONS ===")

    for name, polygon in islands.items():
        island_mask = shapely.intersects_xy(
            polygon,
            lon_grid,
            lat_grid,
        )

        new_island_cells = island_mask & ~old_mask
        expected_additions |= new_island_cells

        print(
            f"{name}: {int(new_island_cells.sum())} "
            "new cells"
        )

    if not np.array_equal(added, expected_additions):
        raise ValueError(
            "Unexpected cells added outside selected islands"
        )

    output = gpd.GeoDataFrame(
        {
            "study_area": ["Geographical Europe"],
            "version": ["candidate_v2"],
            "status": ["provisional"],
            "description": [
                "Candidate V1 plus selected Russian Arctic islands"
            ],
        },
        geometry=[updated],
        crs="EPSG:4326",
    )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    output.to_file(OUTPUT, driver="GeoJSON")

    reloaded = gpd.read_file(OUTPUT).geometry.iloc[0]

    if not reloaded.is_valid:
        raise ValueError("Exported geometry is invalid")

    reloaded_mask = shapely.intersects_xy(
        reloaded,
        lon_grid,
        lat_grid,
    )

    if not np.array_equal(new_mask, reloaded_mask):
        raise ValueError(
            "Export changed study-area grid membership"
        )

    print("\nExport verification: PASS")
    print("Output:", OUTPUT)
    print("Status: PROVISIONAL")


if __name__ == "__main__":
    main()
