# Climate Data Requirements

**Project:** Europe Climate Extremes Analysis  
**Component:** Data Management & SQL  
**Status:** Proposed — Pending Team Agreement and Dataset Validation

## 1. Research Question

How has global warming affected the frequency and intensity of extreme heat events in Europe, and how might their probability and return periods change under future climate scenarios?

## 2. Geographical Scope

The study will focus on Europe as a whole to investigate changes in extreme heat events at a continental scale.

Where appropriate, regional analyses will be conducted to account for differences in climate conditions across Europe.

The final geographical boundary, land mask, and spatial grid will be defined according to the selected climate dataset.

Continental temperature averages will use appropriate area weighting. Changes in spatial data coverage will be assessed to avoid misleading long-term comparisons.

## 3. Historical Period

**Proposed historical period:** 1950–2025.

This period provides a sufficiently long historical record for investigating long-term temperature trends and changes in extreme heat events.

The final period will depend on dataset availability, temporal completeness, and spatial coverage.

Historical results will be aggregated into annual and decadal summaries to support trend analysis and comparisons across different periods.

**Proposed reference period:** 1991–2020.

## 4. Temporal Resolution

**Required resolution:** Daily.

Daily observations are necessary to:

- Identify consecutive extreme-temperature days.
- Calculate annual heatwave frequency.
- Estimate heatwave duration.
- Measure heatwave intensity.
- Extract annual maximum temperatures.
- Construct annual and decadal temperature summaries.

Monthly or annual aggregates alone are insufficient for identifying consecutive-day heatwave events.

## 5. Required Temperature Variables

### Primary Variable

**Daily maximum near-surface air temperature (Tmax)**

Used for:

- Identifying extreme heat days.
- Detecting heatwave events.
- Calculating heatwave frequency and duration.
- Quantifying temperature exceedances.
- Extracting annual maxima for GEV modelling.

### Secondary Variable

**Daily mean near-surface air temperature (Tmean)**

Used for:

- Analysing long-term temperature changes.
- Comparing annual and decadal temperatures.
- Calculating moving averages.
- Providing additional climate context.

Temperature values will be standardized to degrees Celsius (°C).

Original units and conversion procedures will be documented.

## 6. Operational Definition of a Heatwave

The proposed definition is:

**A heatwave occurs when daily maximum temperature exceeds the local calendar-day 95th-percentile threshold for at least three consecutive days.**

The threshold will be estimated using the proposed 1991–2020 reference period.

The percentile threshold should account for seasonal temperature variation and geographic differences across Europe.

The final implementation must specify the calendar-day percentile calculation, reference window, leap-day handling, and treatment of missing observations.

### Heatwave Indicators

The project will aim to calculate:

- Annual number of heatwave events.
- Annual number of heatwave days.
- Duration of each heatwave event.
- Maximum daily temperature during each event.
- Temperature exceedance above the local percentile threshold.

Heatwave events will initially be detected at the grid-cell level. Continental summaries will be constructed with appropriate spatial weighting.

## 7. Historical Dataset Requirements

The selected dataset should ideally provide:

- European geographic coverage.
- Daily near-surface temperature observations or estimates.
- Daily maximum and mean temperature variables.
- A long and sufficiently complete historical record.
- Consistent geographical coordinates.
- Documented units and missing-value conventions.
- Reliable provider documentation.
- A reproducible download method.
- A suitable machine-readable format, preferably NetCDF.

Candidate datasets include E-OBS and Copernicus ERA5.

The final dataset will be selected after comparing coverage, quality, temporal resolution, accessibility, and integration requirements.

## 8. Future Climate Scenarios

Future projections will be treated separately from historical observations.

The scenario-analysis stage should identify appropriate climate model projections, future periods, emissions scenarios, and methods for estimating changes in extreme heat probability.

Historical observations and future simulations must not be treated as interchangeable data sources.

Any comparison between historical and future conditions will require a consistent event definition, compatible spatial and temporal processing, and consideration of model uncertainty.

## 9. Data Management and SQL Requirements

The Data Management component will provide:

- Documentation of selected climate data sources.
- Reproducible data acquisition procedures.
- Standardized variable names and units.
- Dataset and spatial-grid metadata.
- Data quality checks.
- A relational database for selected observations, metadata, or derived indicators.
- Reusable SQL queries for downstream analysis.
- A documented data interface for the Python processing component.

Large multidimensional source datasets may remain in their original NetCDF format rather than being fully converted into relational database tables.

The final SQL schema will be designed after examining the actual selected dataset.

## 10. Data Quality Requirements

The data quality assessment will include:

- Temporal completeness.
- Missing-value detection.
- Duplicate observation checks.
- Coordinate and geographic coverage validation.
- Temperature-unit consistency.
- Detection of invalid or suspicious temperature values.
- Verification of dates and calendar conventions.
- Identification of changes in spatial coverage over time.
- Record-count checks before and after ingestion.

Missing observations will not automatically be replaced or removed without a documented justification.

## 11. Expected Deliverables

The Data Management component will produce:

1. A dataset comparison and selection document.
2. Documentation of the chosen data source.
3. A documented SQL database schema.
4. Reproducible data acquisition and ingestion scripts.
5. Data-quality reports and validation queries.
6. Reusable analytical SQL queries.
7. A documented data handoff for Python analysis.

## 12. Decisions Pending Confirmation

Before implementation, the team must confirm:

- The final historical dataset.
- The exact European spatial domain.
- The final historical coverage after quality checks.
- The heatwave threshold and event definition.
- The treatment of spatial and temporal missing data.
- The interface between SQL storage and Python processing.
- The source and methodology for future climate projections.
