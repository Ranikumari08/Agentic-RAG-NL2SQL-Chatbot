from doctors_tools import check_doctor_availability
from appointment_tools import book_appointment, cancel_appointment
from pharmacy_tools import check_medicine_availability
from lab_tools import check_lab_test_availability
from notification_tools import send_notification

# NOTE: values below (P001, D001, etc.) must exist in your Postgres
# tables for the positive-path checks to return "success"/"confirmed".
# Swap in real IDs from your own patients/doctors tables as needed.

print("\n--- Doctor Availability ---")
print(check_doctor_availability(doctor_name="Ayesha Kapoor", date="2026-10-05"))

print("\n--- Book Appointment ---")
booking = book_appointment(
    patient_id="P001",
    doctor_id="D001",
    date="2026-10-05",
    time="10:00",
    reason_for_visit="Routine checkup",
)
print(booking)

print("\n--- Cancel Appointment (using the ID just booked) ---")
if booking.get("appointment_id"):
    print(cancel_appointment(booking["appointment_id"]))

print("\n--- Medicine ---")
print(check_medicine_availability("Metformin", 20))

print("\n--- Lab Test (abbreviation) ---")
print(check_lab_test_availability("CBC", "2026-10-05"))

print("\n--- Notification ---")
print(send_notification("P001", "Your appointment is tomorrow at 10 AM."))