-- Issue #9: Climate Data Handoff
-- Export observation-level ERA5 data
-- Current dataset: Daily maximum temperature

USE europe_climate;

SELECT
    t.dataset_id,
    t.observation_date,
    g.latitude,
    g.longitude,
    t.temperature_c,
    g.land_mask,
    d.dataset_name,
    d.variable_name,
    d.statistic_type
FROM daily_temperatures AS t
JOIN grid_cells AS g
    ON t.grid_cell_id = g.grid_cell_id
JOIN datasets AS d
    ON t.dataset_id = d.dataset_id
WHERE t.dataset_id = 1
ORDER BY
    t.observation_date,
    g.latitude,
    g.longitude;
