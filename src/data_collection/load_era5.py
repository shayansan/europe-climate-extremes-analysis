
import os
from pathlib import Path

import mysql.connector
import numpy as np
import xarray as xr
from dotenv import load_dotenv


load_dotenv()

# Input dataset
DATA_FILE = Path(
    "data/raw/era5/9831f09756389bd31899fc3ddad5aa5c.nc"
)

BATCH_SIZE = 5000


def connect_database():
    return mysql.connector.connect(
        host=os.environ["DB_HOST"],
        port=int(os.environ["DB_PORT"]),
        database=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
    )


def register_dataset(cursor):
    source = (
        "Copernicus ERA5",
        "ECMWF / Copernicus",
        "https://cds.climate.copernicus.eu/",
        "t2m",
        "daily_maximum",
        "K",
        "UTC",
    )

    cursor.execute(
        """
        SELECT dataset_id
        FROM datasets
        WHERE dataset_name = %s
          AND source_name = %s
          AND source_url = %s
          AND variable_name = %s
          AND statistic_type = %s
          AND original_unit = %s
          AND time_zone = %s
        LIMIT 1
        """,
        source,
    )

    result = cursor.fetchone()
    if result:
        return result[0]

    cursor.execute(
        """
        INSERT INTO datasets (
            dataset_name, source_name, source_url,
            variable_name, statistic_type,
            original_unit, time_zone
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        source,
    )

    return cursor.lastrowid


def register_grid_cells(cursor, latitudes, longitudes):
    coordinates = [
        (round(float(lat), 3), round(float(lon), 3))
        for lat in latitudes
        for lon in longitudes
    ]

    cursor.executemany(
        """
        INSERT INTO grid_cells (latitude, longitude)
        VALUES (%s, %s)
        ON DUPLICATE KEY UPDATE
            latitude = latitude
        """,
        coordinates,
    )

    cursor.execute(
        "SELECT grid_cell_id, latitude, longitude FROM grid_cells"
    )

    return {
        (round(float(lat), 3), round(float(lon), 3)): cell_id
        for cell_id, lat, lon in cursor.fetchall()
    }


def import_temperature_data(cursor, connection, ds, dataset_id, grid_map):
    latitudes = ds.latitude.values
    longitudes = ds.longitude.values

    latitude_grid, longitude_grid = np.meshgrid(
        latitudes, longitudes, indexing="ij"
    )

    coordinates = [
        (round(float(lat), 3), round(float(lon), 3))
        for lat, lon in zip(latitude_grid.flat, longitude_grid.flat)
    ]

    grid_ids = [grid_map[coord] for coord in coordinates]


    query = """
            INSERT INTO daily_temperatures (
            dataset_id,
            grid_cell_id,
            observation_date,
            temperature_c
            )
            VALUES (%s, %s, %s, %s) AS new
            ON DUPLICATE KEY UPDATE
            temperature_c = new.temperature_c
    """

    total_processed = 0

    for day_index, timestamp in enumerate(ds.valid_time.values):
        date = np.datetime_as_string(timestamp, unit="D")

        temperatures = ds["t2m"].isel(
            valid_time=day_index
        ).values.ravel()

        records = []

        for grid_id, kelvin in zip(grid_ids, temperatures):
            if not np.isfinite(kelvin):
                continue

            celsius = float(kelvin) - 273.15

            records.append((
                dataset_id,
                grid_id,
                date,
                celsius,
            ))

        for start in range(0, len(records), BATCH_SIZE):
            batch = records[start:start + BATCH_SIZE]
            cursor.executemany(query, batch)

        connection.commit()
        total_processed += len(records)

        print(
            f"Day {day_index + 1}/{len(ds.valid_time)} "
            f"| Date: {date} "
            f"| Processed: {total_processed:,}"
        )

    return total_processed


def main():
    if not DATA_FILE.is_file():
        raise FileNotFoundError(f"Dataset not found: {DATA_FILE}")

    connection = None

    try:
        connection = connect_database()
        cursor = connection.cursor()

        with xr.open_dataset(DATA_FILE) as ds:
            if ds["t2m"].attrs.get("units") != "K":
                raise ValueError("Unexpected temperature unit")

            if "how=max" not in ds.attrs.get("history", ""):
                raise ValueError("Expected daily maximum ERA5 data")

            dataset_id = register_dataset(cursor)

            grid_map = register_grid_cells(
                cursor,
                ds.latitude.values,
                ds.longitude.values,
            )
            connection.commit()

            total = import_temperature_data(
                cursor, connection, ds, dataset_id, grid_map
            )

            print(f"\nImport completed: {total:,} observations processed.")

        cursor.close()

    except Exception:
        if connection is not None:
            connection.rollback()
        raise

    finally:
        if connection is not None and connection.is_connected():
            connection.close()


if __name__ == "__main__":
    main()
