-- Europe Climate Extremes Analysis
-- August 2020, geographic Europe candidate_v2, ERA5 daily Tmax
-- Dataset ID 2 was verified against the local MySQL database.
-- Read only: no data mutations.

-- 1. Dataset metadata (do not assume every environment uses ID 2).
SELECT dataset_id, dataset_name, source_name, source_url,
       variable_name, statistic_type, original_unit, time_zone
FROM datasets
WHERE dataset_id = 2;

-- 2. Coverage, range and number of distinct grid cells.
SELECT COUNT(*) AS observations,
       COUNT(DISTINCT observation_date) AS days,
       COUNT(DISTINCT grid_cell_id) AS grid_cells,
       MIN(observation_date) AS first_date,
       MAX(observation_date) AS last_date,
       MIN(temperature_c) AS min_temperature_c,
       MAX(temperature_c) AS max_temperature_c
FROM daily_temperatures
WHERE dataset_id = 2;

-- 3. Missing/incomplete days (zero returned rows is the expected outcome).
SELECT observation_date, COUNT(*) AS observations
FROM daily_temperatures
WHERE dataset_id = 2
GROUP BY observation_date
HAVING COUNT(*) <> 22904;

-- 4. Daily regional weighted means and daily grid-cell maxima.
SELECT t.observation_date,
       COUNT(*) AS valid_cells,
       SUM(t.temperature_c * COS(RADIANS(g.latitude))) /
       SUM(COS(RADIANS(g.latitude))) AS weighted_mean_tmax_c,
       MAX(t.temperature_c) AS maximum_tmax_c
FROM daily_temperatures AS t
JOIN grid_cells AS g ON g.grid_cell_id = t.grid_cell_id
WHERE t.dataset_id = 2
GROUP BY t.observation_date
ORDER BY t.observation_date;

-- 5. Grid-cell-level data handoff for heatwave analysis.
-- Large output (710,024 rows): export with a scripted cursor or streaming query,
-- not by copying results from an interactive MySQL terminal.
SELECT t.observation_date,
       g.latitude,
       g.longitude,
       t.temperature_c AS tmax_c
FROM daily_temperatures AS t
JOIN grid_cells AS g ON g.grid_cell_id = t.grid_cell_id
WHERE t.dataset_id = 2
ORDER BY t.observation_date, g.latitude, g.longitude;
