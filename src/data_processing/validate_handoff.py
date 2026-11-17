
from pathlib import Path

import pandas as pd

# Path to exported data
DATA_FILE = Path("data/processed/era5_2020_07.tsv")

# Read TSV
df = pd.read_csv(
    DATA_FILE,
    sep="\t",
    parse_dates=["observation_date"],
    na_values=["NULL"],
)

# Expected schema
expected_columns = [
    "dataset_id",
    "observation_date",
    "latitude",
    "longitude",
    "temperature_c",
    "land_mask",
    "dataset_name",
    "variable_name",
    "statistic_type",
]

assert list(df.columns) == expected_columns, "Unexpected columns"
assert len(df) == 1_332_783, "Unexpected observation count"
assert df["observation_date"].nunique() == 31, "Unexpected date count"

# Check unique observation keys
duplicates = df.duplicated(
    subset=["dataset_id", "observation_date", "latitude", "longitude"]
).sum()

assert duplicates == 0, f"Found {duplicates} duplicate observations"

# Verify temperature values
assert df["temperature_c"].notna().all(), "Missing temperature values"

print("=== DATA HANDOFF VALIDATION ===")
print(f"Observations: {len(df):,}")
print(f"Unique dates: {df['observation_date'].nunique()}")
print(f"Duplicate observations: {duplicates}")
print(f"Minimum temperature: {df['temperature_c'].min():.2f} °C")
print(f"Maximum temperature: {df['temperature_c'].max():.2f} °C")
print(f"Missing land-mask values: {df['land_mask'].isna().sum():,}")
print("Validation passed.")
