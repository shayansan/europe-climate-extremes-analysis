# European Study Area Definition

## 1. Research Scope

The project investigates historical changes in temperature extremes and heatwave characteristics across geographical Europe.

The primary analysis targets European land areas rather than the complete territories of countries classified politically as European.

## 2. Geographic Inclusion Policy

**Mainland Europe:** Included.

**European islands:** Included where represented by the selected geographic boundary dataset.

**European Russia:** Intended for inclusion, subject to a validated boundary separating European and Asian Russia.

**European Turkey:** Intended for inclusion, subject to a validated geographic boundary.

**Cyprus:** Pending an explicit methodological decision. Its inclusion or exclusion must be documented and applied consistently.

**Overseas territories:** Excluded from the primary continental European analysis unless a separately justified exception is introduced.

## 3. Study Area Versus Land Mask

The geographic study-area boundary and the land-sea classification are separate components.

The study-area boundary identifies the geographic domain of the research.

The land mask identifies which ERA5 grid cells represent land rather than ocean.

A grid cell must satisfy both conditions to be included in the primary land-temperature analysis.

## 4. Current Prototype

The current implementation uses Natural Earth 1:50m country polygons selected through:

`CONTINENT == "Europe"`

This is a preliminary country-based geographic mask and must not be interpreted as the final definition of Europe.

For the July 2020 ERA5 sample:

- Total grid cells: 42,993
- Selected grid cells: 17,463
- Excluded grid cells: 25,530

These figures describe the prototype only.

## 5. Boundary Limitations

The Natural Earth continent attribute does not provide an independently validated physical Europe-Asia boundary.

Transcontinental countries, overseas territories, coastal grid cells, and island representation require additional checks.

Grid-cell centre selection also does not estimate the fraction of each cell covered by land or by the study area.

## 6. Requirements Before Historical Analysis

Before producing final European climate indicators:

1. Select and document an authoritative geographic boundary.
2. Resolve transcontinental regions explicitly.
3. Confirm the treatment of Cyprus and overseas territories.
4. Implement and validate a land mask separately.
5. Save the boundary source, version, coordinate reference system, and processing method.
6. Recalculate geographic coverage and area-weighted statistics using the final mask.

## 7. Current Status

**Status: Provisional — geographic definition not finalized.**

The existing July 2020 results are suitable for pipeline development and regression testing, but not for final Europe-wide climate conclusions.
