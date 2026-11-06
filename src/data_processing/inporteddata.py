import xarray as xr
import pandas as pd

# 1. Downloaded NetCDF file from Copernicus
ds = xr.open_dataset('573d10cc551975fd607cb248c49b6865.nc')

print("Dataset Overview:")
print(ds)

# 2. Convert the NetCDF dataset into a Pandas DataFrame
# 't2m' is the standard Copernicus variable name for 2m temperature
df = ds['t2m'].to_dataframe().reset_index()

# 3. Clean and format the data
# Convert temperature from Kelvin to Celsius
df['temperature_celsius'] = df['t2m'] - 273.15

# 4. Extract year from the timestamp
df['year'] = pd.to_datetime(df['valid_time']).dt.year

# 5. Split regions (e.g., Southern Europe vs Northern Europe based on Latitude)
df['region'] = df['latitude'].apply(lambda lat: 'Southern Europe' if lat < 45 else 'Northern Europe')

# 5. Calculate summary statistics (annual means/extremes for each region)
summary_df = df.groupby(['region', 'year'])['temperature_celsius'].agg(
    mean_temp='mean',
    max_temp='max',
    std_temp='std'
).reset_index()

print("\nProcessed Summary Preview:")
print(summary_df.head())

# 6. Export clean CSV 
summary_df.to_csv('european_heat_summary_1940_2026.csv', index=False)
print("\nClean summary CSV successfully exported!")