# ERA5 Dataset — Technical Documentation

## 1. Dataset Overview

**Dataset:** ERA5 post-processed daily statistics on single levels
**Provider:** ECMWF / Copernicus Climate Change Service (C3S)
**Product type:** Reanalysis-derived daily statistics
**Source:** https://cds.climate.copernicus.eu/datasets/derived-era5-single-levels-daily-statistics

ERA5 provides gridded historical estimates of atmospheric conditions. This project uses ERA5 to investigate temperature extremes and heatwave-related indicators across Europe.

## 2. Temporal Coverage

- Official ERA5 product availability: 1940–present
- Proposed project study period: 1950–2025
- Currently downloaded sample: 1–31 July 2020
- Temporal resolution: Daily
- Sample time reference: UTC

The proposed historical study period is not yet fully downloaded or processed.

## 3. Spatial Coverage

**Original product:** Global

**Current downloaded subset:**

| Property | Value |
|---|---|
| Northern latitude | 72°N |
| Southern latitude | 34°N |
| Western longitude | 25°W |
| Eastern longitude | 45°E |
| Grid resolution | 0.25° × 0.25° |
| Latitude points | 153 |
| Longitude points | 281 |
| Total grid cells | 42,993 |

The current bounding box includes regions outside Europe and marine grid cells.

A geographic mask is therefore required before continental analysis.

## 4. Temperature Variables

**Current variable:** `t2m`

**Description:** 2-metre air temperature

**Daily statistic:** Maximum

**Original unit:** Kelvin (K)

**Database unit:** Degrees Celsius (°C)

Conversion:

`temperature_c = temperature_k - 273.15`

Daily mean temperature is a planned additional variable but is not included in the current sample.

## 5. Source File Format

The current ERA5 sample is stored as NetCDF.

Dimensions:

- `valid_time`: 31
- `latitude`: 153
- `longitude`: 281

Data variable:

- `t2m`

## 6. Database Integration

**Database:** `europe_climate`

Tables:

- `datasets`
- `grid_cells`
- `daily_temperatures`

The current ingestion pipeline stores temperature values in Celsius, linked to dates, geographic grid cells, and dataset metadata.

## 7. Initial Data Validation

| Metric | Value |
|---|---|
| Observations | 1,332,783 |
| Distinct dates | 31 |
| Grid cells | 42,993 |
| Duplicate observation keys | 0 |
| Minimum temperature | -1.95°C |
| Maximum temperature | 52.10°C |

These statistics describe the complete downloaded bounding box, not European land areas alone.

## 8. Known Limitations

1. The current geographic subset includes non-European regions.
2. The land mask is not yet implemented.
3. Spatial averages are not area-weighted.
4. Only one month of historical data has been tested.
5. The final European geographic boundary remains to be agreed.
6. Heatwave detection requires a finalized event definition and sufficient baseline observations.

## 9. Planned Improvements

- Implement European geographic masking.
- Separate land and marine grid cells.
- Develop area-weighted spatial aggregation.
- Extend historical temperature coverage.
- Add daily mean temperature where required.
- Implement reproducible processing and quality checks.

## 10. Official References

- Copernicus Climate Data Store: ERA5 post-processed daily statistics on single levels
- ECMWF: ERA5 family daily statistics documentation
- Copernicus Climate Change Service: Climate reanalysis documentation
