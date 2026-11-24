"""Import one complete, geographically masked ERA5 daily-statistics month to MySQL.

Run from the repository root using `python -m src.data_collection.import_era5_monthly`.
Without --commit, this is a read-only, database-free validation.
"""
import argparse
import calendar
import os
from pathlib import Path

import numpy as np
import xarray as xr

from src.pipeline import create_spatial_mask, load_study_geometry, read_grid

BATCH_SIZE = 5000
STATISTICS = {'tmax': 'daily_maximum', 'tmean': 'daily_mean'}
# Scope is intentionally part of dataset identity: never mix old pilot observations.
DATASET_NAME = 'Copernicus ERA5 geographic Europe candidate_v2'
SOURCE_NAME = 'ECMWF / Copernicus'
SOURCE_URL = 'https://cds.climate.copernicus.eu/'


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--statistic', choices=STATISTICS, required=True)
    parser.add_argument('--study-area', type=Path, required=True)
    parser.add_argument('--commit', action='store_true',
                        help='Explicitly permit SQL INSERTs (otherwise dry-run)')
    return parser.parse_args()


def validate_input(ds, statistic):
    temperature, latitudes, longitudes = read_grid(ds)
    dates = np.asarray(temperature.valid_time.values).astype('datetime64[D]')
    if len(dates) == 0 or len(set(dates.tolist())) != len(dates):
        raise ValueError('Empty or duplicate observation dates')
    first = str(dates[0])
    year, month, _ = map(int, first.split('-'))
    ndays = calendar.monthrange(year, month)[1]
    expected = np.arange(np.datetime64(f'{year}-{month:02d}-01'),
                         np.datetime64(f'{year}-{month:02d}-01') + np.timedelta64(ndays, 'D'))
    if not np.array_equal(dates, expected):
        raise ValueError('NetCDF must contain one complete calendar month in order')
    history = str(ds.attrs.get('history', '')).lower()
    if 'how=max' in history and statistic != 'tmax':
        raise ValueError('NetCDF metadata identifies daily maximum, not Tmean')
    if 'how=mean' in history and statistic != 'tmean':
        raise ValueError('NetCDF metadata identifies daily mean, not Tmax')
    return temperature, latitudes, longitudes, year, month


def inspect_month(temperature, mask):
    if int(mask.sum()) == 0:
        raise ValueError('Empty study-area mask')
    expected_per_day = int(mask.sum())
    for i, timestamp in enumerate(temperature.valid_time.values):
        raw = np.asarray(temperature.isel(valid_time=i).values)
        if raw.shape != mask.shape:
            raise ValueError('Data/grid mismatch')
        selected = raw[mask]
        if not np.isfinite(selected).all():
            raise ValueError(f'Missing/non-finite value in study area on {str(timestamp)[:10]}')
        if np.any(selected < 150) or np.any(selected > 350):
            raise ValueError('Physically implausible Kelvin value; inspect source')
    return expected_per_day * temperature.sizes['valid_time']


def connect_database():
    from dotenv import load_dotenv
    import mysql.connector
    load_dotenv()
    return mysql.connector.connect(
        host=os.environ['DB_HOST'],
        port=int(os.environ.get('DB_PORT', '3306')),
        database=os.environ['DB_NAME'],
        user=os.environ['DB_USER'],
        password=os.environ['DB_PASSWORD'],
        autocommit=False,
    )


def get_or_insert_dataset(cursor, statistic):
    spec = (DATASET_NAME, SOURCE_NAME, SOURCE_URL, 't2m',
            STATISTICS[statistic], 'K', 'UTC')
    cursor.execute('''
        SELECT dataset_id FROM datasets
        WHERE dataset_name=%s AND source_name=%s AND source_url=%s
          AND variable_name=%s AND statistic_type=%s
          AND original_unit=%s AND time_zone=%s
    ''', spec)
    hits = [row[0] for row in cursor.fetchall()]
    if len(hits) > 1:
        raise ValueError('Ambiguous dataset metadata: multiple matching rows')
    if hits:
        return hits[0]
    cursor.execute('''
        INSERT INTO datasets (dataset_name,source_name,source_url,
                              variable_name,statistic_type,original_unit,time_zone)
        VALUES (%s,%s,%s,%s,%s,%s,%s)
    ''', spec)
    return cursor.lastrowid


def selected_coordinates(latitudes, longitudes, mask):
    lat_grid, lon_grid = np.meshgrid(latitudes, longitudes, indexing='ij')
    return [(round(float(lat), 3), round(float(lon), 3))
            for lat, lon in zip(lat_grid[mask], lon_grid[mask])]


def prepare_grid_ids(cursor, coords):
    if len(set(coords)) != len(coords):
        raise ValueError('Duplicate coordinates after rounding to 3 decimals')
    for start in range(0, len(coords), BATCH_SIZE):
        cursor.executemany('''
            INSERT INTO grid_cells (latitude,longitude) VALUES (%s,%s)
            ON DUPLICATE KEY UPDATE grid_cell_id=grid_cell_id
        ''', coords[start:start + BATCH_SIZE])
    lats = [lat for lat, _ in coords]
    lons = [lon for _, lon in coords]
    cursor.execute('''
        SELECT grid_cell_id, latitude, longitude FROM grid_cells
        WHERE latitude BETWEEN %s AND %s AND longitude BETWEEN %s AND %s
    ''', (min(lats), max(lats), min(lons), max(lons)))
    mapping = {(round(float(lat), 3), round(float(lon), 3)): cell_id
               for cell_id, lat, lon in cursor.fetchall()}
    if any(coord not in mapping for coord in coords):
        raise ValueError('Grid-cell mapping is incomplete')
    return [mapping[coord] for coord in coords]


def import_month(connection, temperature, mask, latitudes, longitudes, statistic):
    cursor = connection.cursor()

    try:
        dataset_id = get_or_insert_dataset(cursor, statistic)
        coords = selected_coordinates(latitudes, longitudes, mask)
        grid_ids = prepare_grid_ids(cursor, coords)

        inserted = 0
        attempted = 0
        tolerance_c = 0.001

        for day_index, timestamp in enumerate(temperature.valid_time.values):
            date = str(np.datetime64(timestamp, 'D'))
            values = np.asarray(
                temperature.isel(valid_time=day_index).values
            )[mask]

            records = [
                (dataset_id, grid_id, date, float(kelvin) - 273.15)
                for grid_id, kelvin in zip(grid_ids, values)
            ]

            attempted += len(records)

            for start in range(0, len(records), BATCH_SIZE):
                batch = records[start:start + BATCH_SIZE]
                batch_ids = [record[1] for record in batch]

                placeholders = ",".join(["%s"] * len(batch_ids))

                cursor.execute(
                    f"""
                    SELECT grid_cell_id, temperature_c
                    FROM daily_temperatures
                    WHERE dataset_id = %s
                      AND observation_date = %s
                      AND grid_cell_id IN ({placeholders})
                    """,
                    (dataset_id, date, *batch_ids),
                )

                existing_rows = cursor.fetchall()

                if len(existing_rows) != len({
                    row[0] for row in existing_rows
                }):
                    raise ValueError(
                        f"Duplicate database grid IDs on {date}"
                    )

                existing = {
                    row[0]: float(row[1])
                    for row in existing_rows
                }

                new_records = []

                for record in batch:
                    _, grid_id, _, incoming_c = record

                    if grid_id not in existing:
                        new_records.append(record)
                        continue

                    stored_c = existing[grid_id]

                    if abs(stored_c - incoming_c) > tolerance_c:
                        raise ValueError(
                            "Conflicting temperature: "
                            f"dataset={dataset_id}, "
                            f"grid={grid_id}, date={date}, "
                            f"stored={stored_c:.6f} C, "
                            f"incoming={incoming_c:.6f} C"
                        )

                if new_records:
                    cursor.executemany(
                        """
                        INSERT INTO daily_temperatures
                        (dataset_id, grid_cell_id,
                         observation_date, temperature_c)
                        VALUES (%s, %s, %s, %s)
                        """,
                        new_records,
                    )

                    if cursor.rowcount != len(new_records):
                        raise ValueError(
                            "Unexpected number of inserted rows"
                        )

                    inserted += cursor.rowcount

        first_date = str(
            np.datetime64(temperature.valid_time.values[0], 'D')
        )
        last_date = str(
            np.datetime64(temperature.valid_time.values[-1], 'D')
        )

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM daily_temperatures
            WHERE dataset_id = %s
              AND observation_date BETWEEN %s AND %s
            """,
            (dataset_id, first_date, last_date),
        )

        count = cursor.fetchone()[0]

        if count != attempted:
            raise ValueError(
                f"Database count {count} != expected {attempted}"
            )

        connection.commit()
        return dataset_id, inserted, count

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()


def main():
    args = parse_args()
    if not args.input.is_file():
        raise FileNotFoundError(args.input)
    if not args.study_area.is_file():
        raise FileNotFoundError(args.study_area)
    geom = load_study_geometry(None, args.study_area)
    with xr.open_dataset(args.input) as ds:
        temperature, latitudes, longitudes, year, month = validate_input(ds, args.statistic)
        mask, _, _, _ = create_spatial_mask(latitudes, longitudes, geom)
        expected = inspect_month(temperature, mask)
        print(f'Period: {year}-{month:02d}; statistic: {args.statistic}')
        print(f'Selected cells: {int(mask.sum()):,}; days: {temperature.sizes["valid_time"]}')
        print(f'Expected observations: {expected:,}')
        if not args.commit:
            print('DRY RUN PASS — no database connection, no changes made')
            return
        if 'candidate_v2' not in args.study_area.name:
            raise ValueError('Refusing write: expected candidate_v2 GeoJSON')
        connection = connect_database()
        try:
            dataset_id, inserted, total = import_month(
                connection, temperature, mask, latitudes, longitudes, args.statistic)
            print(f'COMMITTED: dataset_id={dataset_id}; inserted={inserted:,}; '
                  f'monthly_total={total:,}')
        finally:
            connection.close()


if __name__ == '__main__':
    main()
