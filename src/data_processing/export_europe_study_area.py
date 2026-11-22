
from pathlib import Path

import geopandas as gpd
from shapely.geometry import Point, box

from src.data_processing.validate_europe_coverage import (
    AREAS,
    create_geometry,
)


OUTPUT = Path(
    "data/processed/geography/"
    "europe_geographic_candidate_v1.geojson"
)

VERSION = "candidate_v1"

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
    "French Guiana": (-53.04, 3.96, False),
    "Reunion": (55.53, -21.10, False),
    "Canary Islands": (-16.61, 28.22, False),
    "Madeira": (-16.97, 32.76, False),
    "Azores": (-28.39, 38.49, False),
}


def area_km2(geometry):
    series = gpd.GeoSeries(
        [geometry],
        crs="EPSG:4326",
    ).to_crs("EPSG:6933")

    return float(series.area.iloc[0]) / 1_000_000


def main():
    _, refined = create_geometry()

    north, west, south, east = AREAS["candidate"]

    download_bbox = box(
        west,
        south,
        east,
        north,
    )

    # Explicit geographic scope for the candidate study area.
    study_area = refined.intersection(download_bbox)

    if study_area.is_empty:
        raise ValueError("Study area is empty")

    if not study_area.is_valid:
        raise ValueError("Study area geometry is invalid")

    print("=== EUROPE STUDY AREA EXPORT ===")
    print("Version:", VERSION)
    print("Bounding box:", AREAS["candidate"])

    for name, (lon, lat, expected) in REFERENCE_POINTS.items():
        actual = study_area.covers(Point(lon, lat))

        if actual != expected:
            raise ValueError(
                f"{name}: expected {expected}, got {actual}"
            )

        print(f"{name}: PASS")

    original_area = area_km2(refined)
    selected_area = area_km2(study_area)

    print("\n=== AREA SUMMARY ===")
    print("Original area (km2):", round(original_area))
    print("Selected area (km2):", round(selected_area))
    print(
        "Outside area (km2):",
        round(original_area - selected_area),
    )

    output = gpd.GeoDataFrame(
        {
            "study_area": ["Geographical Europe"],
            "version": [VERSION],
            "status": ["provisional"],
            "boundary_method": [
                "Natural Earth + Europe-Asia split "
                "+ geographic bounding box"
            ],
        },
        geometry=[study_area],
        crs="EPSG:4326",
    )

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output.to_file(
        OUTPUT,
        driver="GeoJSON",
    )

    # Verify that the exported geometry can be read again.
    loaded = gpd.read_file(OUTPUT)

    if len(loaded) != 1:
        raise ValueError("Unexpected number of features")

    loaded_geometry = loaded.geometry.iloc[0]

    if not loaded_geometry.is_valid:
        raise ValueError("Exported geometry is invalid")

    difference = study_area.symmetric_difference(loaded_geometry)

    if not difference.is_empty:
        raise ValueError(
           "Exported geometry differs spatially from source"
    )

    print("\nExport verification: PASS")
    print("Output:", OUTPUT)
    print("Status: PROVISIONAL")


if __name__ == "__main__":
    main()
