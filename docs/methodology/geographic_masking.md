# European Geographic Masking Methodology

## 1. Objective

Define a reproducible geographic mask for selecting ERA5 grid cells within the European study area.

The mask will be used to exclude observations outside the study area before calculating regional temperature statistics and extreme heat indicators.

## 2. Data Sources

- Climate dataset: Copernicus ERA5
- Geographic boundaries: Natural Earth Admin 0 Countries
- Boundary resolutions tested: 1:110m and 1:50m
- Coordinate reference system: EPSG:4326
- ERA5 grid resolution: 0.25° × 0.25°

## 3. Initial Masking Method

The preliminary implementation selects Natural Earth features classified as `CONTINENT == "Europe"`.

Country geometries are combined into a single geometry, and ERA5 grid-cell centres are tested for spatial intersection with that geometry.

This is a preliminary country-based mask, not the finalized geographic definition of Europe.

## 4. Initial Validation Results

| Metric | 110m | 50m |
|---|---:|---:|
| Total ERA5 cells | 42,993 | 42,993 |
| Selected cells | 17,633 | 17,463 |
| Excluded cells | 25,360 | 25,530 |

The two masks produced 790 different grid-cell classifications.

Using `contains_xy` and `intersects_xy` on the 110m dataset produced identical results for the tested ERA5 grid.

## 5. Geographic Validation

The following test locations were correctly classified using the preliminary mask:

- Rome: Included
- Berlin: Included
- Paris: Included
- Iraq (34°N, 44.75°E): Excluded

These checks confirm expected classifications for selected locations but do not establish complete geographic accuracy.

## 6. Outstanding Geographic Decisions

Before finalizing the study area, the team must agree on:

- The geographic boundary between European and Asian Russia.
- The European portion of Turkey.
- Whether Cyprus is included in the study.
- The treatment of small islands and coastal grid cells.
- The spatial extent needed to cover the complete study area.

## 7. Distinction Between Masks

`land_mask` identifies land versus non-land cells.

`in_study_area` identifies whether a cell belongs to the selected geographic study region.

These properties must be stored and interpreted separately.

## 8. Current Limitations

- The ERA5 sample covers only 34–72°N and 25°W–45°E.
- The current geographic subset does not cover all possible definitions of Europe.
- Natural Earth boundaries differ between resolutions.
- The preliminary method classifies grid-cell centres rather than measuring land-area overlap.
- Spatial area weighting has not yet been implemented.

## 9. Planned Work

1. Agree on the final European study-area definition.
2. Establish reproducible geographic boundary rules.
3. Generate and validate the final study-area mask.
4. Maintain separate land and study-area classifications.
5. Integrate the validated mask with the data-processing pipeline.
6. Apply appropriate spatial weighting for regional climate statistics.

## 10. Spatial Coverage Audit

The initial ERA5 sample covers 34–72°N and 25°W–45°E.

A spatial coverage audit was performed using Natural Earth 1:50m country boundaries.

### Results

| Metric | Value |
|---|---:|
| Total selected polygon area | 22,968,010 km² |
| Area outside ERA5 bounding box | 15,096,185 km² |
| Uncovered fraction | 65.73% |
| Russian polygon area outside the box | 14,934,874 km² |
| Uncovered fraction excluding Russia | 2.69% |

### Interpretation

Most of the uncovered area is associated with the Russian polygon, which extends far beyond geographic Europe.

The calculation also includes some overseas territories and islands.

These results should not be interpreted as the percentage of geographic Europe missing from the ERA5 sample.

### Methodological Decision

The current 50m mask will remain a preliminary implementation.

Before downloading the full historical dataset, the study must establish an explicit geographic definition of Europe, including the treatment of transcontinental countries and overseas territories.

The final ERA5 download bounds must fully cover the agreed study area.

No modifications to the MySQL land-mask column will be made until that definition has been finalized.
