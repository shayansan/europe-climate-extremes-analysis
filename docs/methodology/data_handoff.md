# Climate Data Handoff Specification

## 1. Purpose

Define a consistent interface between the ERA5 data management pipeline and the Python data processing, visualization, and statistical analysis components.

## 2. Data Sources

**Primary source:** Copernicus ERA5

**Initial test dataset:** July 2020, daily maximum 2-metre temperature.

**Current storage:** NetCDF source files and MySQL database (`europe_climate`).

## 3. Database Schema

The database contains three main tables:

- `datasets`: source information, variables, and metadata.
- `grid_cells`: geographical coordinates and optional land-mask information.
- `daily_temperatures`: daily temperature measurements linked to datasets and grid cells.

## 4. Standard Observation Schema

| Field | Type | Description |
|---|---|---|
| dataset_id | INTEGER | Source dataset identifier |
| observation_date | DATE | Observation date |
| latitude | FLOAT | Latitude in degrees |
| longitude | FLOAT | Longitude in degrees |
| temperature_c | FLOAT | Daily temperature statistic in Celsius |
| land_mask | BOOLEAN / NULL | Geographic land classification |

The actual temperature statistic must be identified using dataset metadata. The current ERA5 sample contains daily maximum temperatures.

## 5. Data Processing Requirements

The Python processing stage should:

1. Read NetCDF data or a documented SQL export.
2. Validate temporal coverage and temperature units.
3. Detect missing and duplicate observations.
4. Preserve coordinate and dataset metadata.
5. Apply an agreed European geographic mask.
6. Use appropriate spatial weighting for regional summaries.
7. Produce reproducible outputs for downstream analysis.

## 6. Expected Outputs

### Observation-level data

Standardized daily observations with coordinates, dates, temperature values, and source metadata.

### Aggregated data

Daily, monthly, or annual statistics, with documented coverage and aggregation methods.

### Extreme heat indicators

Heatwave frequency, duration, and intensity, calculated only after the event definition has been finalized.

## 7. Initial Validation

The July 2020 ERA5 sample contains:

- 31 observation days.
- 42,993 grid cells.
- 1,332,783 temperature observations.
- No duplicate observation keys.

## 8. Known Limitations

- The current sample covers only July 2020.
- The downloaded bounding box includes locations outside Europe.
- The land mask and spatial weighting are not yet implemented.
- Full historical coverage is unavailable.
- Final heatwave indicators have not yet been produced.

## 9. Pending Integration Decisions

- Final geographic boundary.
- Historical data coverage.
- NetCDF and SQL responsibilities.
- Output formats for Python and statistical analysis.
- Missing-data policy.
- Heatwave detection methodology.

## 10. Related GitHub Issues

- #8 — SQL climate data exploration.
- #9 — Analysis-ready data handoff.
- #10 — Climate data cleaning and transformation.
- #12 — Processed dataset preparation.

## 11. Reproducible Data Export

The initial handoff uses a tab-separated export generated from MySQL.

Run the SQL export from the repository root:

```bash
mkdir -p data/processed

mysql -u climate_user -p \
  --batch --raw \
  europe_climate \
  < sql/queries/003_export_climate_data.sql \
  > data/processed/era5_2020_07.tsv
```

The export contains observation dates, coordinates, temperature measurements, dataset metadata, and land-mask fields.

The current SQL query selects `dataset_id = 1`, which corresponds to the initial July 2020 test dataset. Dataset selection must be made configurable before general historical ingestion.

## 12. Python Validation

Activate the project's virtual environment:

```bash
source .venv/bin/activate
```

Run the validation script:

```bash
python src/data_processing/validate_handoff.py
```

### Initial Validation Results

| Metric | Result |
|---|---|
| Observations | 1,332,783 |
| Unique dates | 31 |
| Duplicate observation keys | 0 |
| Minimum temperature | -1.95°C |
| Maximum temperature | 52.10°C |
| Missing land-mask values | 1,332,783 |

The validation confirms that the exported dataset can be loaded into Pandas and passes basic structural checks.

The geographical mask and full historical coverage remain pending.

## 13. Reproducibility Notes

- Raw and processed climate data should remain outside Git version control.
- Database credentials must be stored securely and must not be committed.
- Exported files should be regenerated from the documented data source.
- Future validation should not depend on hard-coded observation counts or dates.
- Regional climate indicators require geographical masking and appropriate area weighting.
