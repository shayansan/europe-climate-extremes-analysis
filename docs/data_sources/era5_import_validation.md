# ERA5 Data Ingestion — Initial Validation Report

**Dataset:** Copernicus ERA5 Daily Statistics  
**Variable:** 2-metre temperature (daily maximum)  
**Period:** 2020-07-01 to 2020-07-31  
**Database:** MySQL — europe_climate

## Ingestion Results

| Metric | Result |
|---|---|
| Total observations | 1,332,783 |
| Grid cells | 42,993 |
| Days | 31 |
| Observations per day | 42,993 |
| Duplicate observation keys | 0 |
| Minimum temperature | -1.95°C |
| Maximum temperature | 52.10°C |
| Unweighted mean temperature | 19.66°C |

## Validation Summary

All 1,332,783 expected observations were successfully stored in MySQL.

The dataset contains 31 distinct dates, with consistent record counts for every day. The minimum and maximum temperatures agree with the original NetCDF measurements after conversion from Kelvin to Celsius.

No duplicate observation keys were detected.

## Outstanding Validation

- Verify individual temperature values against the original NetCDF file.
- Apply a geographical land mask.
- Implement area-weighted continental summaries.
- Validate additional months and historical periods.
- Confirm the final heatwave definition.

## Conclusion

The initial ERA5-to-MySQL ingestion test passed structural integrity and basic temperature-range checks.

The pipeline is ready for further testing, but the dataset is not yet considered fully validated for scientific climate analysis.
