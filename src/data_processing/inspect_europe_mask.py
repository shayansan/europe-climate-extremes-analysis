
from pathlib import Path

import geopandas as gpd
import pandas as pd

BOUNDARIES = Path(
    "data/raw/boundaries/ne_110m_admin_0_countries.zip"
)

MASK_FILE = Path(
    "data/processed/europe_mask_preview.csv"
)

# Load country boundaries
world = gpd.read_file(BOUNDARIES).to_crs("EPSG:4326")
europe = world[world["CONTINENT"] == "Europe"].copy()

# Load existing ERA5 mask
df = pd.read_csv(MASK_FILE)

# Convert grid coordinates to geographic points
points = gpd.GeoDataFrame(
    df,
    geometry=gpd.points_from_xy(
        df["longitude"],
        df["latitude"],
    ),
    crs="EPSG:4326",
)

# Identify the country containing each grid-cell centre
matched = gpd.sjoin(
    points,
    europe[["ADMIN", "geometry"]],
    how="left",
    predicate="within",
)

# Check for overlapping country assignments
if matched.index.duplicated().any():
    raise ValueError("Some grid cells matched multiple countries")

# Compare country assignments with preview mask
actual = matched["ADMIN"].notna()

if not actual.equals(matched["in_europe_preview"]):
    raise ValueError("Country assignments disagree with preview mask")

# Count cells per country
country_counts = (
    matched.dropna(subset=["ADMIN"])
    .groupby("ADMIN")
    .size()
    .sort_values(ascending=False)
)

print("=== GRID CELLS BY COUNTRY ===")
print(country_counts.to_string())

print("\n=== SUMMARY ===")
print("Selected cells:", int(actual.sum()))
print("Countries with selected cells:", len(country_counts))

# Inspect Russian grid cells
russia = matched[matched["ADMIN"] == "Russia"]

print("\n=== RUSSIA CHECK ===")
print("Russian grid cells:", len(russia))

if not russia.empty:
    print(
        "Longitude range:",
        russia["longitude"].min(),
        "to",
        russia["longitude"].max(),
    )

print("\n=== EXCLUDED COUNTRIES ===")
for country in ["Turkey", "Cyprus"]:
    print(
        f"{country}:",
        world.loc[
            world["ADMIN"] == country,
            "CONTINENT",
        ].tolist(),
    )
