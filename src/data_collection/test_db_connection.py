
import os

import mysql.connector
from dotenv import load_dotenv

load_dotenv()

connection = None

try:
    connection = mysql.connector.connect(
        host=os.environ["DB_HOST"],
        port=int(os.environ["DB_PORT"]),
        database=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
    )

    if connection.is_connected():
        print("Successfully connected to MySQL.")

        cursor = connection.cursor()
        try:
            cursor.execute("SELECT DATABASE(), CURRENT_USER()")
            database, user = cursor.fetchone()

            print(f"Database: {database}")
            print(f"User: {user}")

            cursor.execute("SHOW TABLES")

            print("\nAvailable tables:")
            for (table_name,) in cursor.fetchall():
                print(f"- {table_name}")
        finally:
            cursor.close()

except mysql.connector.Error as error:
    print(f"MySQL connection failed: {error}")

finally:
    if connection is not None and connection.is_connected():
        connection.close()
        print("\nConnection closed.")
