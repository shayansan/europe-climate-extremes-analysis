
CREATE DATABASE IF NOT EXISTS europe_climate;
USE europe_climate;

-- Dataset metadata
CREATE TABLE IF NOT EXISTS datasets (
    dataset_id INT AUTO_INCREMENT PRIMARY KEY,
    dataset_name VARCHAR(100) NOT NULL,
    source_name VARCHAR(100) NOT NULL,
    source_url VARCHAR(500),
    variable_name VARCHAR(50) NOT NULL,
    statistic_type VARCHAR(30) NOT NULL,
    original_unit VARCHAR(20) NOT NULL,
    time_zone VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Geographic grid points
CREATE TABLE IF NOT EXISTS grid_cells (
    grid_cell_id INT AUTO_INCREMENT PRIMARY KEY,
    latitude DECIMAL(6,3) NOT NULL,
    longitude DECIMAL(7,3) NOT NULL,
    land_mask BOOLEAN DEFAULT NULL,

    CONSTRAINT uq_grid_coordinates
        UNIQUE (latitude, longitude),

    CONSTRAINT chk_latitude
        CHECK (latitude BETWEEN -90 AND 90),

    CONSTRAINT chk_longitude
        CHECK (longitude BETWEEN -180 AND 180)
);

-- Daily temperature observations
CREATE TABLE IF NOT EXISTS daily_temperatures (
    observation_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    dataset_id INT NOT NULL,
    grid_cell_id INT NOT NULL,
    observation_date DATE NOT NULL,
    temperature_c FLOAT NOT NULL,

    CONSTRAINT fk_temperature_dataset
        FOREIGN KEY (dataset_id)
        REFERENCES datasets(dataset_id),

    CONSTRAINT fk_temperature_grid
        FOREIGN KEY (grid_cell_id)
        REFERENCES grid_cells(grid_cell_id),

    CONSTRAINT uq_daily_observation
        UNIQUE (dataset_id, grid_cell_id, observation_date),

    INDEX idx_temperature_date (observation_date),
    INDEX idx_temperature_grid_date (grid_cell_id, observation_date)
);
