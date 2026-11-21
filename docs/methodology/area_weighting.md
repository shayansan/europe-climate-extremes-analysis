# Area-Weighted Temperature Aggregation

## 1. Objective

Calculate spatially weighted daily maximum temperature statistics from ERA5 observations within a preliminary European study-area mask.

## 2. Input Data

- Dataset: Copernicus ERA5
- Variable: `t2m` (daily maximum 2-metre temperature)
- Period: July 2020
- Grid resolution: 0.25° × 0.25°
- Geographic mask: Natural Earth 1:50m preliminary study-area mask
- Selected grid cells: 17,463

## 3. Method

ERA5 observations are stored on a regular latitude-longitude grid.

Because grid-cell surface area changes with latitude, spatial averages are calculated using cosine latitude weights:

\[
w_i = \cos(\varphi_i)
\]

The weighted mean temperature is:

\[
\bar{T}_w = \frac{\sum_i w_i T_i}{\sum_i w_i}
\]

where:

- \(T_i\) is the daily maximum temperature at grid cell \(i\), in degrees Celsius.
- \(\varphi_i\) is the latitude of grid cell \(i\).
- \(w_i\) is the approximate area weight.

Only grid cells selected by the preliminary geographic mask and containing valid temperature measurements are included.

This method approximates grid-cell area weighting. It does not calculate the exact land-area fraction of partially covered coastal grid cells.

## 4. Validation Results

The weighted aggregation was independently checked for July 1, 2020.

| Method | Temperature |
|---|---:|
| Unweighted mean over full bounding box | 18.724°C |
| Unweighted mean after geographic masking | 22.051°C |
| Area-weighted mean after masking | 23.271°C |

The geographic mask changed the mean by +3.327°C.

Applying cosine latitude weights to the masked observations changed the mean by an additional +1.220°C.

The independently calculated weighted mean matched the output of the main aggregation script.

## 5. Output

The processing script generates:

`data/processed/area_weighted_daily_tmax_preview.csv`

The output contains:

- `date`
- `valid_cells`
- `weighted_mean_tmax_c`
- `maximum_tmax_c`

The July 2020 output contains 31 daily records.

## 6. Limitations

- The geographic mask is preliminary.
- The study-area definition is not yet finalized.
- Coastal grid cells are classified by their centre points.
- Cosine latitude weighting approximates cell areas.
- The current sample covers only July 2020.
- The analysis does not yet estimate heatwave frequency, duration, or long-term temperature trends.

## 7. Future Work

- Finalize European geographic coverage.
- Validate the final land and study-area masks.
- Extend the analysis to historical temperature data.
- Compare daily maximum and daily mean temperatures where available.
- Produce consistent annual and regional climate indicators.
- Integrate the aggregation workflow with downstream statistical analysis.
