"""
appointment_tool.py
Books and cancels real rows in the appointments table.

- Appointment IDs follow the existing convention seen in appointments.csv
  (A0001, A0002, ... A2000) instead of a random UUID fragment, so joins
  against billing / lab_tests / medical_records / prescriptions keep working.
- book_appointment validates the patient and doctor exist and that the
  slot isn't already taken before inserting (no silent double-booking).
- cancel_appointment checks the appointment exists and isn't already
  cancelled before updating it.
"""

from typing import Dict, Any
from db import get_cursor

BLOCKING_STATUSES = ("Scheduled", "Completed")


def _next_appointment_id(cur) -> str:
    cur.execute(
        """
        SELECT appointment_id FROM appointments
        ORDER BY appointment_id DESC
        LIMIT 1
        """
    )
    row = cur.fetchone()
    if not row:
        return "A0001"
    last_num = int(row["appointment_id"][1:])
    return f"A{last_num + 1:04d}"


def book_appointment(
    patient_id: str,
    doctor_id: str,
    date: str,
    time: str,
    appointment_type: str = "Consultation",
    booking_method: str = "Online",
    reason_for_visit: str = "",
) -> Dict[str, Any]:

    with get_cursor() as cur:
        cur.execute("SELECT 1 FROM patients WHERE patient_id = %s", (patient_id,))
        if not cur.fetchone():
            return {"status": "error", "message": f"Patient '{patient_id}' not found."}

        cur.execute("SELECT 1 FROM doctors WHERE doctor_id = %s", (doctor_id,))
        if not cur.fetchone():
            return {"status": "error", "message": f"Doctor '{doctor_id}' not found."}

        cur.execute(
            """
            SELECT 1 FROM appointments
            WHERE doctor_id = %s AND appointment_date = %s
              AND appointment_time = %s AND status = ANY(%s)
            """,
            (doctor_id, date, time, list(BLOCKING_STATUSES)),
        )
        if cur.fetchone():
            return {
                "status": "error",
                "message": f"Slot {date} {time} is already booked for doctor {doctor_id}.",
            }

    with get_cursor(commit=True) as cur:
        appointment_id = _next_appointment_id(cur)
        cur.execute(
            """
            INSERT INTO appointments
                (appointment_id, patient_id, doctor_id, appointment_date,
                 appointment_time, appointment_type, status, booking_method,
                 reason_for_visit)
            VALUES (%s, %s, %s, %s, %s, %s, 'Scheduled', %s, %s)
            """,
            (
                appointment_id,
                patient_id,
                doctor_id,
                date,
                time,
                appointment_type,
                booking_method,
                reason_for_visit,
            ),
        )

    return {
        "status": "confirmed",
        "appointment_id": appointment_id,
        "patient_id": patient_id,
        "doctor_id": doctor_id,
        "date": date,
        "time": time,
        "message": "Appointment booked successfully.",
    }


def cancel_appointment(appointment_id: str) -> Dict[str, Any]:

    with get_cursor() as cur:
        cur.execute(
            "SELECT status FROM appointments WHERE appointment_id = %s",
            (appointment_id,),
        )
        row = cur.fetchone()

    if not row:
        return {"status": "error", "message": f"Appointment '{appointment_id}' not found."}

    if row["status"] == "Cancelled":
        return {
            "status": "error",
            "message": f"Appointment '{appointment_id}' is already cancelled.",
        }

    with get_cursor(commit=True) as cur:
        cur.execute(
            "UPDATE appointments SET status = 'Cancelled' WHERE appointment_id = %s",
            (appointment_id,),
        )

    return {
        "status": "cancelled",
        "appointment_id": appointment_id,
        "message": "Appointment cancelled successfully.",
    }