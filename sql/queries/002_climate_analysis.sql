
-- =====================================================
-- Issue #8: Climate Data Exploration
-- Dataset: ERA5 Daily Maximum Temperature
-- Database: europe_climate
--
-- Important:
-- Results cover available observations only.
-- Annual summaries are NOT necessarily full-year data.
-- Spatial averages are unweighted and unmasked.
-- =====================================================

USE europe_climate;

-- 1. Dataset coverage
-- Identify which datasets and periods are available.

SELECT
    d.dataset_id,
    d.dataset_name,
    d.statistic_type,
    MIN(t.observation_date) AS first_date,
    MAX(t.observation_date) AS last_date,
    COUNT(DISTINCT t.observation_date) AS days_available,
    COUNT(DISTINCT t.grid_cell_id) AS grid_cells,
    COUNT(*) AS observations
FROM daily_temperatures AS t
JOIN datasets AS d
    ON t.dataset_id = d.dataset_id
GROUP BY
    d.dataset_id,
    d.dataset_name,
    d.statistic_type;


-- 2. Monthly temperature statistics
-- These are descriptive summaries of daily Tmax values.

SELECT
    dataset_id,
    YEAR(observation_date) AS year,
    MONTH(observation_date) AS month,
    COUNT(DISTINCT observation_date) AS days_available,
    COUNT(*) AS observations,
    ROUND(AVG(temperature_c), 2) AS mean_daily_tmax_c,
    ROUND(MIN(temperature_c), 2) AS min_daily_tmax_c,
    ROUND(MAX(temperature_c), 2) AS max_daily_tmax_c
FROM daily_temperatures
GROUP BY
    dataset_id,
    YEAR(observation_date),
    MONTH(observation_date)
ORDER BY dataset_id, year, month;


-- 3. Annual summaries of available observations
-- Do not interpret partial years as complete years.

SELECT
    dataset_id,
    YEAR(observation_date) AS year,
    COUNT(DISTINCT observation_date) AS days_available,
    COUNT(*) AS observations,
    ROUND(AVG(temperature_c), 2) AS mean_daily_tmax_c,
    ROUND(MAX(temperature_c), 2) AS maximum_daily_tmax_c
FROM daily_temperatures
GROUP BY dataset_id, YEAR(observation_date)
ORDER BY dataset_id, year;


-- 4. High-temperature observations
-- 40 C is an illustrative fixed threshold,
-- NOT the project's final heatwave definition.

SELECT
    t.observation_date,
    g.latitude,
    g.longitude,
    ROUND(t.temperature_c, 2) AS temperature_c
FROM daily_temperatures AS t
JOIN grid_cells AS g
    ON t.grid_cell_id = g.grid_cell_id
WHERE t.temperature_c >= 40
ORDER BY t.temperature_c DESC
LIMIT 20;


-- 5. Geographic filtering
-- Example bounding box over a part of Europe.
-- This is NOT a European land mask.

SELECT
    t.observation_date,
    g.latitude,
    g.longitude,
    ROUND(t.temperature_c, 2) AS temperature_c
FROM daily_temperatures AS t
JOIN grid_cells AS g
    ON t.grid_cell_id = g.grid_cell_id
WHERE g.latitude BETWEEN 35 AND 48
  AND g.longitude BETWEEN 5 AND 20
  AND t.observation_date = '2020-07-01'
ORDER BY g.latitude DESC, g.longitude
LIMIT 30;


-- 6. Daily spatial summaries for Python
-- Unweighted averages; not yet suitable as
-- final area-weighted European climate indicators.

SELECT
    t.dataset_id,
    t.observation_date,
    COUNT(*) AS observations,
    ROUND(AVG(t.temperature_c), 3) AS mean_daily_tmax_c,
    ROUND(MAX(t.temperature_c), 3) AS max_daily_tmax_c
FROM daily_temperatures AS t
GROUP BY
    t.dataset_id,
    t.observation_date
ORDER BY t.dataset_id, t.observation_date;
