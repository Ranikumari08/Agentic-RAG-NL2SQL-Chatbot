"""
doctors_tool.py
Looks up a real doctor row from Postgres (doctors table, loaded from
doctors.csv) and computes availability by checking which slots on the
requested date are already taken in the appointments table.

Schema assumed (from doctors.csv / appointments.csv):
  doctors(doctor_id, doctor_name, specialization, qualification,
          experience_years, consultation_fee, department_id, joining_date)
  appointments(appointment_id, patient_id, doctor_id, appointment_date,
               appointment_time, appointment_type, status, booking_method,
               reason_for_visit)
"""

from typing import Dict, Any
from db import get_cursor

# Standard bookable slots per day. In a real system this would come from
# a doctor's schedule/shift table; kept as a fixed candidate list here
# and filtered against actual bookings.
CANDIDATE_SLOTS = ["10:00", "11:30", "13:00", "15:00", "16:30"]

# Statuses that actually block a slot. A cancelled/no-show appointment
# should NOT hold the slot.
BLOCKING_STATUSES = ("Scheduled", "Completed")


def _find_doctor(doctor_name: str = None, doctor_id: str = None) -> Dict[str, Any]:
    with get_cursor() as cur:
        if doctor_id:
            cur.execute(
                "SELECT doctor_id, doctor_name, specialization, consultation_fee "
                "FROM doctors WHERE doctor_id = %s",
                (doctor_id,),
            )
        else:
            # ILIKE = case-insensitive partial match, so "sharma" or
            # "Dr. Sharma" both work, and typos in casing don't fail silently.
            cur.execute(
                "SELECT doctor_id, doctor_name, specialization, consultation_fee "
                "FROM doctors WHERE doctor_name ILIKE %s",
                (f"%{doctor_name}%",),
            )
        return cur.fetchone()


def check_doctor_availability(
    date: str,
    doctor_name: str = None,
    doctor_id: str = None,
) -> Dict[str, Any]:
    """
    Look up a doctor by name or id and return real available slots for
    the given date, based on what's already booked in `appointments`.
    """
    if not doctor_name and not doctor_id:
        return {"status": "error", "message": "Provide doctor_name or doctor_id."}

    doctor = _find_doctor(doctor_name=doctor_name, doctor_id=doctor_id)
    if not doctor:
        identifier = doctor_id or doctor_name
        return {"status": "error", "message": f"Doctor '{identifier}' not found."}

    with get_cursor() as cur:
        cur.execute(
            """
            SELECT appointment_time
            FROM appointments
            WHERE doctor_id = %s
              AND appointment_date = %s
              AND status = ANY(%s)
            """,
            (doctor["doctor_id"], date, list(BLOCKING_STATUSES)),
        )
        booked = {row["appointment_time"].strftime("%H:%M") for row in cur.fetchall()}

    available_slots = [slot for slot in CANDIDATE_SLOTS if slot not in booked]

    return {
        "status": "success",
        "doctor_id": doctor["doctor_id"],
        "doctor_name": doctor["doctor_name"],
        "specialization": doctor["specialization"],
        "consultation_fee": float(doctor["consultation_fee"]),
        "date": date,
        "available": len(available_slots) > 0,
        "available_slots": available_slots,
    }