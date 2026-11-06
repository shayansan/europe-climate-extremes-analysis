
-- ERA5 Data Ingestion Validation
-- Sample: July 2020
-- Dataset: Daily maximum 2m temperature

USE europe_climate;

-- 1. Check stored observations
SELECT COUNT(*) AS total_observations
FROM daily_temperatures;

-- 2. Check temporal coverage
SELECT
    MIN(observation_date) AS first_date,
    MAX(observation_date) AS last_date,
    COUNT(DISTINCT observation_date) AS total_days
FROM daily_temperatures;

-- 3. Check observations per day
SELECT
    observation_date,
    COUNT(*) AS total_observations
FROM daily_temperatures
GROUP BY observation_date
ORDER BY observation_date;

-- 4. Check temperature statistics
SELECT
    ROUND(MIN(temperature_c), 2) AS minimum_c,
    ROUND(MAX(temperature_c), 2) AS maximum_c,
    ROUND(AVG(temperature_c), 2) AS mean_c
FROM daily_temperatures;

-- 5. Check duplicate observations
SELECT
    dataset_id,
    grid_cell_id,
    observation_date,
    COUNT(*) AS duplicate_count
FROM daily_temperatures
GROUP BY dataset_id, grid_cell_id, observation_date
HAVING COUNT(*) > 1;

-- 6. Check dataset metadata
SELECT * FROM datasets;
