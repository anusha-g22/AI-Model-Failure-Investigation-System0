
import os
import mysql.connector
from dotenv import load_dotenv

from pathlib import Path

load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")

def get_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "failure_lineage")
    )

if __name__ == "__main__":
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT DATABASE()")
        print("Connected to database:", cursor.fetchone()[0])

        cursor.execute("SHOW TABLES")
        print("\nAvailable tables:")
        for table in cursor.fetchall():
            print("-", table[0])

        cursor.close()
        conn.close()

        print("\nMySQL connection successful!")

    except mysql.connector.Error as error:
        print("MySQL connection failed:", error)
