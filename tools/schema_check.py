"""
schema_check.py
Run this once to print the actual columns/types Postgres has for each
table. Compare against schema.sql — since your tables were created
manually, this confirms there's no mismatch before the tool functions
run any real queries.

Usage:
    python schema_check.py
"""

import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()

TABLES = [
    "departments", "doctors", "patients", "appointments",
    "billing", "lab_tests", "medical_records", "medications",
    "prescriptions",
]

conn = psycopg2.connect(
    host=os.getenv("DB_HOST", "localhost"),
    port=os.getenv("DB_PORT", "5432"),
    dbname=os.getenv("DB_NAME", "lifespring_healthcare"),
    user=os.getenv("DB_USER", "postgres"),
    password=os.getenv("DB_PASSWORD", ""),
)

with conn.cursor() as cur:
    for table in TABLES:
        cur.execute(
            """
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = %s
            ORDER BY ordinal_position
            """,
            (table,),
        )
        rows = cur.fetchall()
        if not rows:
            print(f"\n{table}: TABLE NOT FOUND")
            continue
        print(f"\n{table}:")
        for col, dtype in rows:
            print(f"  {col:<22} {dtype}")

conn.close()