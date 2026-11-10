import os
import mysql.connector
import pandas as pd 
import xarray as xr
from dotenv import load_dotenv

# Load database environment variables
load_dotenv()

def load_data_from_db():
    connection = mysql.connector.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        port=int(os.environ.get("DB_PORT", 3306)),
        database=os.environ.get("DB_NAME", "europe_climate"),
        user=os.environ.get("DB_USER", "root"),
        password=os.environ.get("DB_PASSWORD", "")
    )
    query = """
    SELECT 
        dt.observation_date,
        dt.temperature_c,
        gc.latitude,
        gc.longitude
    FROM daily_temperatures dt
    JOIN grid_cells gc ON dt.grid_cell_id = gc.grid_cell_id;
    """
    df = pd.read_sql(query, connection)
    connection.close()
    return df

# --- 1. Load Data (with automatic fallback to local file if MySQL isn't running) ---
try:
    print("Attempting to connect to MySQL database...")
    df = load_data_from_db()
    print(f"Successfully loaded {len(df):,} records from database.")
except Exception as e:
    print("\n[Notice] MySQL service not active on this PC. Switching to local NetCDF file fallback...")
    ds = xr.open_dataset('573d10cc551975fd607cb248c49b6865.nc')
    df = ds['t2m'].to_dataframe().reset_index()
    df['temperature_c'] = df['t2m'] - 273.15
    df['observation_date'] = df['valid_time']
    print(f"Successfully loaded {len(df):,} records from local NetCDF file.")

# --- 2. ISSUE #7: DATA QUALITY CHECKS ---
print("\n--- Data Quality Checks ---")
print(f"Missing temperatures: {df['temperature_c'].isnull().sum()}")
print(f"Duplicate records: {df.duplicated().sum()}")
print(f"Latitude range: {df['latitude'].min()} to {df['latitude'].max()}")
print(f"Longitude range: {df['longitude'].min()} to {df['longitude'].max()}")
print(f"Temperature bounds check (°C): Min = {df['temperature_c'].min():.2f}°C, Max = {df['temperature_c'].max():.2f}°C")

# --- 3. ISSUE #11: DESCRIPTIVE STATISTICS & REGIONAL ANALYSIS ---
df['observation_date'] = pd.to_datetime(df['observation_date'])
df['year'] = df['observation_date'].dt.year
df['region'] = df['latitude'].apply(lambda lat: 'Southern Europe' if lat < 45 else 'Northern Europe')

summary_df = df.groupby(['region', 'year'])['temperature_c'].agg(
    mean_temp='mean',
    max_temp='max',
    min_temp='min',
    std_temp='std'
).reset_index()

print("\nProcessed Summary Statistics:")
print(summary_df)

# --- 4. ISSUE #12: EXPORT ---
summary_df.to_csv('european_heat_summary_july_2020.csv', index=False)
print("\nSummary statistics exported to european_heat_summary_july_2020.csv!")