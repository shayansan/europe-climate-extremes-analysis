# ERA5 August 2020 Tmax — Data Quality Report

**Project:** Europe Climate Extremes Analysis  
**Status:** Validated monthly pilot; provisional study area (candidate_v2)  
**Prepared:** 2026-11-24  
**Related issues:** #6 Data Ingestion, #7 Data Quality, #9 Data Handoff

## 1. Scope and provenance

- Source: Copernicus ERA5 derived daily statistics, 2 m air temperature (`t2m`), daily maximum, UTC, original units Kelvin.
- Period: 2020-08-01 through 2020-08-31, inclusive.
- Requested bounding box (north, west, south, east): `[82, -26, 34, 70]`.
- Study geometry: `data/processed/geography/europe_geographic_candidate_v2.geojson` (provisional; not the finalized definition of geographical Europe).
- NetCDF input: `data/raw/era5/historical_candidate_v2/tmax/2020/era5_tmax_2020_08.nc`.
- Daily aggregate CSV: `data/processed/tmax_2020_08_candidate_v2.csv`.
- MySQL database: `europe_climate`; dataset ID `2`, statistic `daily_maximum`.
- Raw source request ID: `379ce9f3-6d04-48a3-b712-e42f936c5442`.

## 2. Validation results

| Check | Observed result | Assessment |
| --- | --- | --- |
| Daily coverage | 31 distinct dates, 2020-08-01 to 2020-08-31 | PASS |
| Study-area grid cells | 22,904 distinct grid cells | PASS |
| Stored observations | 710,024 (= 22,904 × 31) | PASS |
| Daily completeness | Each day has 22,904 records; no incomplete days | PASS |
| Coordinates in stored data | Latitude 35.000 to 80.250; longitude -25.500 to 68.750 | Within requested bounding box |
| Observed temperatures | -2.44346 °C to 42.4535 °C | Range recorded; no full physical-QC audit |
| Cross-system comparison | 31 daily records paired between SQL and CSV | PASS |
| Maximum weighted-mean discrepancy | 0.000487 °C | PASS (tolerance 0.005 °C) |
| Maximum daily-maximum discrepancy | 0.000500 °C | PASS (tolerance 0.005 °C) |

Summary of daily CSV aggregates (31 days): mean of daily area-weighted Tmax = 22.769 °C; monthly maximum of per-grid-cell daily Tmax = 42.454 °C (CSV-rounded).

## 3. Methods and interpretation

The analysis uses the geographic candidate_v2 polygon to select ERA5 grid points. Daily regional means are calculated with weights proportional to `cos(latitude)`. Original Kelvin temperatures are converted to Celsius. The SQL verification recomputed weighted means and daily maxima from `daily_temperatures` joined to `grid_cells`, using matching latitude weights.

Daily CSV values are rounded to three decimal places; SQL temperatures are stored using the MySQL `FLOAT` type. Small discrepancies within the recorded tolerance are expected.

**Important:** The 22,904 selected grid points are point-in-polygon decisions; this is not a fractional land-area mask. The result is a *regional average of daily maximum temperatures*, not daily mean (`Tmean`). The monthly maximum of grid-cell Tmax is also not a regional mean.

## 4. Known limitations / outstanding work

1. Study polygon `candidate_v2` is provisional. Arctic islands, Ural, Caucasus and other disputed geographic conventions require final methodological approval; geographic scope must remain fixed for long-term comparisons.
2. Only August 2020 **Tmax** is verified here. August 2020 Tmean was last observed in `accepted`, not ready, under request ID `900e2bd8-20b1-487a-9b65-6000dc3809e7`.
3. Cross-variable consistency (`Tmean <= Tmax`) has not yet been verified on the complete August grid.
4. Long-term historical coverage, percentile-based heatwave thresholds, homogenization/physical plausibility checks and trend-model assumptions are outside this validation.
5. Legacy dataset ID `1` covers July 2020 using a different geographic extent. **Do not concatenate its aggregates with candidate_v2 as a comparable time series.**
6. This report is based on recorded validation outputs; a fresh independent re-run or a restoration test is not claimed.

## 5. Reproduction

Run from repository root with the project virtual environment enabled:

```bash
python -m src.pipeline \
  --input data/raw/era5/historical_candidate_v2/tmax/2020/era5_tmax_2020_08.nc \
  --statistic tmax \
  --study-area data/processed/geography/europe_geographic_candidate_v2.geojson \
  --output data/processed/tmax_2020_08_candidate_v2.csv
```

Reproduction requires local ERA5 raw files and boundary GeoJSON, which may not be committed to Git. Database access uses locally configured `.env` credentials; do not share passwords or backups.

Use the companion `era5_august_2020_handoff.sql` to verify DB coverage and export daily observations. Queries filter **dataset_id = 2** intentionally to avoid combining geographically inconsistent datasets.
