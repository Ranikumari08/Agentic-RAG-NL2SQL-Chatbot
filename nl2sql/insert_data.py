import os
import psycopg2
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(
    host=os.getenv("DB_HOST", "localhost"),
    port=os.getenv("DB_PORT", "5432"),
    database=os.getenv("DB_NAME", "lifespring_healthcare"),
    user=os.getenv("DB_USER", "postgres"),
    password=os.getenv("DB_PASSWORD", ""),
)

cursor = conn.cursor()

print("Connected to PostgreSQL successfully!")

DATA_DIR = "data"

departments = pd.read_csv(
    os.path.join(DATA_DIR, "departments.csv")
)

doctors = pd.read_csv(
    os.path.join(DATA_DIR, "doctors.csv")
)

patients = pd.read_csv(
    os.path.join(DATA_DIR, "patients.csv")
)

medications = pd.read_csv(
    os.path.join(DATA_DIR, "medications.csv")
)

appointments = pd.read_csv(
    os.path.join(DATA_DIR, "appointments.csv")
)

medical_records = pd.read_csv(
    os.path.join(DATA_DIR, "medical_records.csv")
)

prescriptions = pd.read_csv(
    os.path.join(DATA_DIR, "prescriptions.csv")
)

lab_tests = pd.read_csv(
    os.path.join(DATA_DIR, "lab_tests.csv")
)

billing = pd.read_csv(
    os.path.join(DATA_DIR, "billing.csv")
)

##insert department 
for _, row in departments.iterrows():

    cursor.execute(
        """
        INSERT INTO departments
        (
            department_id,
            department_name,
            location
        )
        VALUES (%s, %s, %s)
        """,
        (
            row["department_id"],
            row["department_name"],
            row["location"]
        )
    )

conn.commit()

print("Departments inserted.")

## insert doctors
for _, row in doctors.iterrows():

    cursor.execute(
        """
        INSERT INTO doctors
        (
            doctor_id,
            doctor_name,
            specialization,
            qualification,
            experience_years,
            consultation_fee,
            department_id,
            joining_date
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        (
            row["doctor_id"],
            row["doctor_name"],
            row["specialization"],
            row["qualification"],
            row["experience_years"],
            row["consultation_fee"],
            row["department_id"],
            row["joining_date"]
        )
    )

conn.commit()

print("Doctors inserted.")

## insert patients
for _, row in patients.iterrows():

    cursor.execute(
        """
        INSERT INTO patients
        (
            patient_id,
            first_name,
            last_name,
            date_of_birth,
            gender,
            phone,
            email,
            city,
            registration_date,
            blood_group,
            insurance_provider
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        (
            row["patient_id"],
            row["first_name"],
            row["last_name"],
            row["date_of_birth"],
            row["gender"],
            row["phone"],
            row["email"],
            row["city"],
            row["registration_date"],
            row["blood_group"],
            row["insurance_provider"]
        )
    )

conn.commit()

print("Patients inserted.")

##insert medications
for _, row in medications.iterrows():

    cursor.execute(
        """
        INSERT INTO medications
        (
            medication_id,
            medication_name,
            category,
            manufacturer,
            unit_price,
            stock_quantity
        )
        VALUES (%s,%s,%s,%s,%s,%s)
        """,
        (
            row["medication_id"],
            row["medication_name"],
            row["category"],
            row["manufacturer"],
            row["unit_price"],
            row["stock_quantity"]
        )
    )

conn.commit()

print("Medications inserted.")

## insert appointment

for _, row in appointments.iterrows():

    cursor.execute(
        """
        INSERT INTO appointments
        (
            appointment_id,
            patient_id,
            doctor_id,
            appointment_date,
            appointment_time,
            appointment_type,
            status,
            booking_method,
            reason_for_visit
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        (
            row["appointment_id"],
            row["patient_id"],
            row["doctor_id"],
            row["appointment_date"],
            row["appointment_time"],
            row["appointment_type"],
            row["status"],
            row["booking_method"],
            row["reason_for_visit"]
        )
    )

conn.commit()

print("Appointments inserted.")

## insert medical records

for _, row in medical_records.iterrows():

    cursor.execute(
        """
        INSERT INTO medical_records
        (
            record_id,
            patient_id,
            appointment_id,
            doctor_id,
            diagnosis,
            symptoms,
            record_date,
            severity,
            notes
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        (
            row["record_id"],
            row["patient_id"],
            row["appointment_id"],
            row["doctor_id"],
            row["diagnosis"],
            row["symptoms"],
            row["record_date"],
            row["severity"],
            row["notes"]
        )
    )

conn.commit()

print("Medical records inserted.")

## insert prescriptopns

for _, row in prescriptions.iterrows():

    cursor.execute(
        """
        INSERT INTO prescriptions
        (
            prescription_id,
            patient_id,
            doctor_id,
            appointment_id,
            medication_id,
            dosage,
            frequency,
            duration_days,
            prescription_date
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        (
            row["prescription_id"],
            row["patient_id"],
            row["doctor_id"],
            row["appointment_id"],
            row["medication_id"],
            row["dosage"],
            row["frequency"],
            row["duration_days"],
            row["prescription_date"]
        )
    )

conn.commit()

print("Prescriptions inserted.")

## insert lab tests
for _, row in lab_tests.iterrows():

    cursor.execute(
        """
        INSERT INTO lab_tests
        (
            test_id,
            patient_id,
            appointment_id,
            test_name,
            test_category,
            test_date,
            result,
            normal_range,
            status,
            cost
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        (
            row["test_id"],
            row["patient_id"],
            row["appointment_id"],
            row["test_name"],
            row["test_category"],
            row["test_date"],
            row["result"],
            row["normal_range"],
            row["status"],
            row["cost"]
        )
    )

conn.commit()

print("Lab tests inserted.")

## insert billing
for _, row in billing.iterrows():

    cursor.execute(
        """
        INSERT INTO billing
        (
            bill_id,
            patient_id,
            appointment_id,
            bill_date,
            consultation_fee,
            lab_charges,
            medicine_charges,
            discount,
            insurance_coverage,
            total_amount,
            payment_method,
            payment_status
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        (
            row["bill_id"],
            row["patient_id"],
            row["appointment_id"],
            row["bill_date"],
            row["consultation_fee"],
            row["lab_charges"],
            row["medicine_charges"],
            row["discount"],
            row["insurance_coverage"],
            row["total_amount"],
            row["payment_method"],
            row["payment_status"]
        )
    )

conn.commit()

print("Billing records inserted.")

## close connection

cursor.close()
conn.close()

print("\nAll data inserted successfully!")