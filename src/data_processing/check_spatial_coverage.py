
from pathlib import Path

import geopandas as gpd
from shapely.geometry import box

BOUNDARIES = Path(
    "data/raw/boundaries/ne_50m_admin_0_countries.zip"
)

# Current ERA5 spatial extent
era5_bbox = box(-25, 34, 45, 72)

world = gpd.read_file(BOUNDARIES).to_crs("EPSG:4326")

# Preliminary European definition
europe = world[world["CONTINENT"] == "Europe"].copy()

# Check whether European polygons extend beyond
# the downloaded ERA5 bounding box.
outside = europe.geometry.difference(era5_bbox)

affected = europe.loc[
    ~outside.is_empty,
    ["ADMIN"]
].copy()

print("=== ERA5 SPATIAL COVERAGE CHECK ===")
print("ERA5 bounds:", era5_bbox.bounds)
print("Countries with areas outside ERA5 coverage:")
print(affected["ADMIN"].sort_values().to_string(index=False))

# Report approximate uncovered surface using an
# equal-area projection.
outside_gdf = gpd.GeoDataFrame(
    geometry=outside,
    crs="EPSG:4326",
).to_crs("EPSG:6933")

europe_gdf = gpd.GeoDataFrame(
    geometry=europe.geometry,
    crs="EPSG:4326",
).to_crs("EPSG:6933")

total_area = europe_gdf.area.sum()
outside_area = outside_gdf.area.sum()

print()
print(f"Total polygon area: {total_area / 1e6:,.0f} km²")
print(f"Outside ERA5 bounds: {outside_area / 1e6:,.0f} km²")
print(f"Uncovered fraction: {outside_area / total_area:.2%}")
