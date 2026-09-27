"""
lab_tools.py
Looks up real lab test info from Postgres (lab_tests table, loaded from
lab_tests.csv). Real test_name values are full names (e.g.
"Complete Blood Count", "Blood Glucose", "Lipid Profile", "ECG",
"Echocardiogram", "HbA1c", "Ultrasound", "Urine Test", "X-Ray") — not
abbreviations like "CBC" — so common abbreviations are resolved to the
real name before querying.

lab_tests.csv is transactional (one row per patient's test), not a rate
card, so "cost" here is derived as the average cost seen for that test
name, and slots are a fixed candidate list filtered against tests
already scheduled for that date (same approach as doctor availability).

Schema assumed:
  lab_tests(test_id, patient_id, appointment_id, test_name, test_category,
            test_date, result, normal_range, status, cost)
"""

from typing import Dict, Any
from db import get_cursor

# Common abbreviations/aliases -> actual test_name in the database.
# Extend this as new abbreviations come up in real patient/agent queries.
TEST_ALIASES = {
    "CBC": "Complete Blood Count",
    "COMPLETE BLOOD COUNT": "Complete Blood Count",
    "BLOOD SUGAR": "Blood Glucose",
    "SUGAR TEST": "Blood Glucose",
    "GLUCOSE": "Blood Glucose",
    "LIPID": "Lipid Profile",
    "THYROID": "Thyroid Profile",
    "ECG": "ECG",
    "ECHO": "Echocardiogram",
    "URINE": "Urine Test",
    "XRAY": "X-Ray",
    "X RAY": "X-Ray",
}

CANDIDATE_SLOTS = ["09:00 AM", "11:00 AM", "12:30 PM", "02:00 PM", "04:00 PM"]


def _resolve_test_name(test_name: str) -> str:
    key = test_name.strip().upper()
    return TEST_ALIASES.get(key, test_name)


def check_lab_test_availability(test_name: str, date: str) -> Dict[str, Any]:

    resolved_name = _resolve_test_name(test_name)

    with get_cursor() as cur:
        cur.execute(
            """
            SELECT test_name, AVG(cost) AS avg_cost, COUNT(*) AS sample_size
            FROM lab_tests
            WHERE test_name ILIKE %s
            GROUP BY test_name
            """,
            (resolved_name,),
        )
        catalog_row = cur.fetchone()

        if not catalog_row:
            return {
                "status": "error",
                "message": f"Lab test '{test_name}' not found.",
            }

        cur.execute(
            """
            SELECT test_date FROM lab_tests
            WHERE test_name ILIKE %s AND test_date = %s
            """,
            (resolved_name, date),
        )
        booked_count = len(cur.fetchall())

    # Simple capacity model: each existing booking on that date consumes
    # one slot from the candidate list. Replace with a real capacity/
    # schedule table if one exists.
    available_slots = CANDIDATE_SLOTS[booked_count:]

    return {
        "status": "success",
        "test_name": catalog_row["test_name"],
        "date": date,
        "available": len(available_slots) > 0,
        "cost": round(float(catalog_row["avg_cost"]), 2),
        "available_slots": available_slots,
    }