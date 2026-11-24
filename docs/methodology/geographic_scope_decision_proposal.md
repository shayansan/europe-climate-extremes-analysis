# Geographic Study Area — Decision Proposal (review required)

**Project:** Europe Climate Extremes Analysis  
**Status:** Proposed scientific scope; **NOT approved and NOT a final production mask**  
**Reference implementation:** `europe_geographic_candidate_v2.geojson`, using Natural Earth Admin-0 1:50m and `asia_europe_border.geojson`  
**Proposed grid:** ERA5 0.25°; geographic extraction bounds [N, W, S, E] = [82, -26, 34, 70]

## 1. Scientific objective

Analyze daily 2-metre air-temperature extremes over **geographical European land** on a fixed geographic domain. The boundary is not the EU, the EEA membership area, nor the entire territory of politically European countries. Keep the spatial domain fixed across 1950–2025 to avoid artificial temporal trends. Use the exact same grid and spatial mask for Tmax and Tmean.

## 2. Proposed explicit inclusion policy (for team approval)

| Geographic region | Proposed primary treatment | Rationale / required audit |
|---|---|---|
| Continental European mainland and islands geographically within the European region | Include | Spatially defined, not based on EU membership |
| Iceland, British Isles, Ireland, Svalbard, Baltic and Mediterranean European islands | Include where represented and within extraction bounds | Verify coverage and island polygon/grid representation |
| European Russia | Include **only west of the documented Europe–Asia dividing line**, plus associated European islands | Do not use all of Russia; audit line provenance, geometry and reference points |
| Kaliningrad | Include | European exclave |
| European Turkey (Eastern Thrace) | Include; exclude Anatolian Turkey | Verify straits-based division |
| Cyprus | **Exclude from the primary geographic-Europe series; offer a separate sensitivity series including it** | Geographic vs political inclusion differs; team must explicitly approve |
| South Caucasus (Armenia, Azerbaijan, Georgia) | **Exclude from the primary series pending a documented physiographic convention** | Europe–Asia boundary in Caucasus is not universally settled |
| Novaya Zemlya and Vaygach | Include under the current candidate-v2 convention, but independently audit their membership and coastal cells | Existing candidate-v2 explicitly adds these islands |
| Greenland, Canary Islands, Madeira, Azores, overseas dependencies | Exclude from primary continental Europe | Avoid country-affiliation-based inclusion of outlying territories |
| Offshore marine cells | Exclude from land-focused primary analysis | Geographic polygon and physical land–sea classification must be distinct |

All decisions about disputed or transcontinental territory must be recorded as **geographic conventions**, not claims about sovereignty.

## 3. Production mask definition

1. Load a **version-pinned** Natural Earth Admin-0 1:50m boundary and a **provenance-documented** Europe–Asia dividing line. Record source URLs, dataset versions, licenses where applicable, and SHA-256 file hashes.
2. Build/review separate mainland, transcontinental, island and exclusion components. Validate polygon topology and inspect map overlays. Do not depend on component indexes; use documented reference locations and explicit geometries.
3. Select ERA5 cell centres inside the geographic study area (`covers`/boundary-inclusive semantics) on the common 0.25° lat-lon grid. Record boundary/edge cases.
4. Independently obtain an ERA5 **land–sea mask** at the same grid, or explicitly regrid a documented source. **Proposed binary primary rule:** retain `lsm > 0.5`. Preserve continuous land fraction in the derived dataset for sensitivity checks. This threshold is a project choice, not an official universal definition of European land.
5. Primary eligible cell: `in_geographic_area AND land_fraction > 0.5`. Keep these fields separate; do not silently repurpose `grid_cells.land_mask` as geographic membership.
6. Compute regional daily summary using `cos(latitude)` weighting for selected cells. Document limitations near coastal/mixed cells; consider land-fraction weighting as sensitivity analysis. Never mix provisional and approved masks in one trend.
7. Preserve observation-level Tmax and Tmean and link each derived aggregate to a mask version, extraction footprint and variable/statistic definition.

## 4. Acceptance checks required **before** a final mask is approved

- Confirm the governing Europe–Asia line's source and trace its complete path, including Ural region, Caspian/Caucasus and Turkish straits. Validate endpoints and line geometry.
- Audit inclusion/exclusion of: Moscow, St Petersburg, Kaliningrad, Edirne, Ankara, Novosibirsk, Iceland, Svalbard, Novaya Zemlya, Vaygach, Cyprus, Caucasus, Canary Islands, Azores, Madeira, Greenland and selected coastlines. The current code already checks a subset; extend it.
- Check the candidate polygon's geometry validity, CRS EPSG:4326 and stable export/reload behavior.
- **Audit geographic clipping:** compute the unclipped selected geometry outside proposed bounds [82,-26,34,70]. An edge-cell count of zero does not by itself establish adequate coverage; report any excluded island/polygon area.
- Confirm alignment of all selected cells with both monthly files and with the land–sea mask; report number of land-eligible cells and each exclusion category.
- Report selected total land area / weighted cell count, resolution, smallest resolved islands and differences against candidate_v2.
- Run sensitivity analyses for Cyprus and the coastal land fraction threshold; quantify the difference in area-weighted regional statistics on a representative month.
- Freeze a deterministic `study_area_v1` boundary and mask **only after team sign-off**, and update pipelines, SQL dataset names and documentation accordingly.
- Ensure no historic dataset is marked production until the final mask and acquisition bounds are frozen.

## 5. What current pilot results do and do not establish

The August 2020 `candidate_v2` Tmax pilot contains **22,904 selected cells × 31 days = 710,024 observations** and passed daily coverage and SQL/Python aggregation checks. These are valid reproducibility checks **for that provisional mask**, not proof that the region is scientifically finalized. The existing SQL table's `land_mask` has not been established as the ERA5 land–sea fraction. Do not relabel candidate_v2 observations as final-Europe observations.

## 6. Approval record (team to complete)

- Selected physiographic Europe–Asia line and provenance: **PENDING**
- Cyprus treatment: **PENDING**
- Caucasus treatment: **PENDING**
- Arctic island and offshore treatment: **PENDING**
- Land–sea mask source and threshold: **PENDING**
- Unclipped extent/coverage audit: **PENDING**
- Sensitivity results: **PENDING**
- Approved by / date / version/hash: **PENDING**

## 7. Reference reading

- European Environment Agency, *Europe's Environment — The Dobris Assessment*, “The continent — Extent and boundaries” (notes ambiguity in Europe's eastern and island boundaries): https://www.eea.europa.eu/en/analysis/publications/92-826-5409-5/page003new.html
- Natural Earth, 1:50m cultural vectors, Admin-0 countries (cartographic polygons; default de facto boundary representation): https://www.naturalearthdata.com/downloads/50m-cultural-vectors/
- ECMWF, ERA5 data documentation (land–sea mask represents land fraction): https://confluence.ecmwf.int/pages/viewpage.action?pageId=235608188
