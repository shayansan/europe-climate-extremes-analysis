"""
Dataset: ERA5 reanalysis data (ECMWF / Copernicus Climate Data Store)
Download Source: Copernicus CDS API (https://cds.climate.copernicus.eu/)
Integration Note: Processes NetCDF exports or files ingested via SQL database pipeline.
"""
import xarray as xr
import pandas as pd

# 1. CONFIGURABLE FILE PATHS
INPUT_FILE = 'src/data_processing/573d10cc551975fd607cb248c49b6865.nc'
OUTPUT_FILE = 'european_heat_summary_1940_2026.csv'

print("--- Starting Climate Data Processing Pipeline ---")

# 2. LOAD DATA (helps how it will work with SQL & documenting ERA5 Dataset)
## the exported climate variables ('t2m' for 2-meter temperature).
ds = xr.open_dataset(INPUT_FILE)

print("\nDataset Overview:")
print(ds)

### Convert the NetCDF dataset into a Pandas DataFrame
df = ds['t2m'].to_dataframe().reset_index()

# 3. DATA QUALITY CHECKS
print("\n" + "="*40)
print("DATA QUALITY SUMMARY REPORT")
print("="*40)

rows_before_clean = len(df)
missing_count_before = df['t2m'].isnull().sum()
duplicate_count = df.duplicated().sum()

# Drop rows with missing temperature values
df_cleaned = df.dropna(subset=['t2m']).copy()
rows_after_clean = len(df_cleaned)

print(f"Record count before cleaning: {rows_before_clean:,}")
print(f"Record count after cleaning: {rows_after_clean:,}")
print(f"Missing temperature values:   {missing_count_before}")
print(f"Duplicate rows detected:      {duplicate_count}")

# 4. CLEANING AND TRANSFORMATION
# Convert temperature from Kelvin to Celsius (Standard metric conversion)
df_cleaned['temperature_celsius'] = df_cleaned['t2m'] - 273.15

print(f"Temperature Range (Celsius): Min = {df_cleaned['temperature_celsius'].min():.2f}°C, Max = {df_cleaned['temperature_celsius'].max():.2f}°C")

# Extract year from the timestamp for annual aggregation
df_cleaned['year'] = pd.to_datetime(df_cleaned['valid_time']).dt.year

# Geographic Assumption:
# Splitting regions at latitude 45°N to roughly separate Southern Europe 
# (Mediterranean climate zone, highly prone to heatwaves) from Northern Europe.
df_cleaned['region'] = df_cleaned['latitude'].apply(lambda lat: 'Southern Europe' if lat < 45 else 'Northern Europe')

# 5. TEMPORAL RESOLUTION & EXTREME HEAT AGGREGATION
# ==========================================
# Temporal Resolution Note: ERA5 hourly/daily data is aggregated to yearly statistics.
# - mean_temp: captures baseline warming trends.
# - max_temp: serves as our primary proxy metric for extreme heat events.
# - min_temp: tracks the lowest annual temperatures to evaluate seasonal lows.
# - std_temp: measures temperature variability and dispersion around the mean each year.
summary_df = df_cleaned.groupby(['region', 'year'])['temperature_celsius'].agg(
    mean_temp='mean',
    max_temp='max',
    min_temp='min',
    std_temp='std'
).reset_index()

print("\nProcessed Summary Preview:")
print(summary_df.head())

# 6. EXPORT FINAL DATASET FOR VISUALIZATION
summary_df.to_csv(OUTPUT_FILE, index=False)
print(f"\nSuccessfully exported analysis-ready dataset to '{OUTPUT_FILE}'!")
print("="*40)