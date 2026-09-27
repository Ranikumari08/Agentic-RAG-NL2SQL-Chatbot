from faker import Faker
import pandas as pd
import random
import os
from datetime import datetime, timedelta


# ============================================================
# CONFIGURATION
# ============================================================

fake = Faker("en_IN")

OUTPUT_DIR = "data"

# Create data folder automatically if it doesn't exist
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ============================================================
# HELPER DATA
# ============================================================

GENDERS = ["Male", "Female"]

BLOOD_GROUPS = [
    "A+",
    "A-",
    "B+",
    "B-",
    "AB+",
    "AB-",
    "O+",
    "O-"
]

CITIES = [
    "Bengaluru",
    "Mysuru",
    "Chennai",
    "Vellore",
    "Hyderabad",
    "Mumbai",
    "Pune"
]

INSURANCE_PROVIDERS = [
    "Star Health",
    "HDFC ERGO",
    "ICICI Lombard",
    "Bajaj Allianz",
    "Care Health",
    "Niva Bupa"
]

APPOINTMENT_TYPES = [
    "Consultation",
    "Follow-up",
    "Emergency",
    "Health Checkup"
]

APPOINTMENT_STATUS = [
    "Completed",
    "Scheduled",
    "Cancelled",
    "No-show"
]

BOOKING_METHODS = [
    "Online",
    "Phone",
    "Walk-in",
    "Reception"
]

DIAGNOSES = [
    "Hypertension",
    "Diabetes",
    "Common Cold",
    "Migraine",
    "Asthma",
    "Gastritis",
    "Anemia",
    "Thyroid Disorder",
    "Arthritis",
    "Respiratory Infection",
    "Vitamin D Deficiency",
    "Fever"
]

SEVERITY = [
    "Mild",
    "Moderate",
    "Severe"
]

MEDICATIONS = [
    ("Metformin", "Diabetes"),
    ("Amlodipine", "Hypertension"),
    ("Atorvastatin", "Cholesterol"),
    ("Paracetamol", "Pain Relief"),
    ("Azithromycin", "Antibiotic"),
    ("Omeprazole", "Gastric"),
    ("Levothyroxine", "Thyroid"),
    ("Cetirizine", "Allergy"),
    ("Ibuprofen", "Pain Relief"),
    ("Montelukast", "Asthma"),
    ("Pantoprazole", "Gastric"),
    ("Losartan", "Hypertension"),
    ("Glimepiride", "Diabetes"),
    ("Vitamin D3", "Vitamin Supplement"),
    ("Iron Supplement", "Anemia")
]

LAB_TESTS = [
    ("Complete Blood Count", "Blood"),
    ("Blood Glucose", "Blood"),
    ("HbA1c", "Diabetes"),
    ("Lipid Profile", "Blood"),
    ("Urine Test", "Urine"),
    ("ECG", "Cardiac"),
    ("X-Ray", "Imaging"),
    ("Ultrasound", "Imaging"),
    ("Echocardiogram", "Cardiac"),
    ("Thyroid Profile", "Blood")
]

PAYMENT_METHODS = [
    "Cash",
    "UPI",
    "Credit Card",
    "Debit Card",
    "Insurance"
]

PAYMENT_STATUS = [
    "Paid",
    "Pending",
    "Partially Paid"
]


# ============================================================
# 1. DEPARTMENTS
# ============================================================

def generate_departments():

    departments = [
        {
            "department_id": "DEP001",
            "department_name": "General Medicine",
            "location": "Ground Floor"
        },
        {
            "department_id": "DEP002",
            "department_name": "Pediatrics",
            "location": "First Floor"
        },
        {
            "department_id": "DEP003",
            "department_name": "Obstetrics & Gynecology",
            "location": "First Floor"
        },
        {
            "department_id": "DEP004",
            "department_name": "Cardiology",
            "location": "Second Floor"
        },
        {
            "department_id": "DEP005",
            "department_name": "Nutrition & Wellness",
            "location": "Second Floor"
        },
        {
            "department_id": "DEP006",
            "department_name": "Diagnostics",
            "location": "Ground Floor"
        }
    ]

    df = pd.DataFrame(departments)

    df.to_csv(
        os.path.join(OUTPUT_DIR, "departments.csv"),
        index=False
    )

    print(f"✓ departments.csv created ({len(df)} records)")

    return departments


# ============================================================
# 2. DOCTORS
# ============================================================

def generate_doctors():

    doctors = [
        {
            "doctor_id": "D001",
            "doctor_name": "Dr. Ayesha Kapoor",
            "specialization": "Internal Medicine",
            "qualification": "MD",
            "experience_years": 12,
            "consultation_fee": 800,
            "department_id": "DEP001",
            "joining_date": "2021-04-10"
        },
        {
            "doctor_id": "D002",
            "doctor_name": "Dr. Rohan Mehta",
            "specialization": "Pediatrics",
            "qualification": "MD",
            "experience_years": 8,
            "consultation_fee": 600,
            "department_id": "DEP002",
            "joining_date": "2022-06-15"
        },
        {
            "doctor_id": "D003",
            "doctor_name": "Dr. Priya Nair",
            "specialization": "Obstetrics & Gynecology",
            "qualification": "MD",
            "experience_years": 10,
            "consultation_fee": 900,
            "department_id": "DEP003",
            "joining_date": "2020-08-20"
        },
        {
            "doctor_id": "D004",
            "doctor_name": "Dr. Anil Deshmukh",
            "specialization": "Cardiology",
            "qualification": "DM",
            "experience_years": 15,
            "consultation_fee": 1200,
            "department_id": "DEP004",
            "joining_date": "2019-02-12"
        },
        {
            "doctor_id": "D005",
            "doctor_name": "Dr. Sneha Rao",
            "specialization": "Nutrition & Dietetics",
            "qualification": "PhD",
            "experience_years": 7,
            "consultation_fee": 700,
            "department_id": "DEP005",
            "joining_date": "2023-01-18"
        }
    ]

    df = pd.DataFrame(doctors)

    df.to_csv(
        os.path.join(OUTPUT_DIR, "doctors.csv"),
        index=False
    )

    print(f"✓ doctors.csv created ({len(df)} records)")

    return doctors


# ============================================================
# 3. PATIENTS
# ============================================================

def generate_patients(count=300):

    patients = []

    start_date = datetime(2020, 1, 1)

    for i in range(1, count + 1):

        gender = random.choice(GENDERS)

        first_name = fake.first_name()
        last_name = fake.last_name()

        patient = {
            "patient_id": f"P{i:03d}",
            "first_name": first_name,
            "last_name": last_name,
            "date_of_birth": fake.date_of_birth(
                minimum_age=18,
                maximum_age=80
            ),
            "gender": gender,
            "phone": fake.numerify("##########"),
            "email": f"{first_name.lower()}.{last_name.lower()}@example.com",
            "city": random.choice(CITIES),
            "registration_date": fake.date_between(
                start_date=start_date,
                end_date="today"
            ),
            "blood_group": random.choice(BLOOD_GROUPS),
            "insurance_provider": random.choice(
                INSURANCE_PROVIDERS
            )
        }

        patients.append(patient)

    df = pd.DataFrame(patients)

    df.to_csv(
        os.path.join(OUTPUT_DIR, "patients.csv"),
        index=False
    )

    print(f"✓ patients.csv created ({len(df)} records)")

    return patients


# ============================================================
# 4. MEDICATIONS
# ============================================================

def generate_medications():

    medications = []

    for i in range(1, 101):

        base_name, category = random.choice(MEDICATIONS)

        medications.append({
            "medication_id": f"MED{i:03d}",
            "medication_name": f"{base_name} {i}",
            "category": category,
            "manufacturer": random.choice([
                "Sun Pharma",
                "Cipla",
                "Dr. Reddy's",
                "Lupin",
                "Abbott",
                "Mankind Pharma"
            ]),
            "unit_price": round(
                random.uniform(5, 500),
                2
            ),
            "stock_quantity": random.randint(50, 1000)
        })

    df = pd.DataFrame(medications)

    df.to_csv(
        os.path.join(OUTPUT_DIR, "medications.csv"),
        index=False
    )

    print(f"✓ medications.csv created ({len(df)} records)")

    return medications


# ============================================================
# 5. APPOINTMENTS
# ============================================================

def generate_appointments(patients, doctors, count=2000):

    appointments = []

    start_date = datetime(2025, 1, 1)
    end_date = datetime(2026, 12, 31)

    for i in range(1, count + 1):

        patient = random.choice(patients)
        doctor = random.choice(doctors)

        appointment_date = fake.date_between(
            start_date=start_date,
            end_date=end_date
        )

        appointment_time = fake.time(
            pattern="%H:%M"
        )

        status = random.choice(APPOINTMENT_STATUS)

        appointments.append({
            "appointment_id": f"A{i:04d}",
            "patient_id": patient["patient_id"],
            "doctor_id": doctor["doctor_id"],
            "appointment_date": appointment_date,
            "appointment_time": appointment_time,
            "appointment_type": random.choice(
                APPOINTMENT_TYPES
            ),
            "status": status,
            "booking_method": random.choice(
                BOOKING_METHODS
            ),
            "reason_for_visit": random.choice([
                "Routine checkup",
                "Fever",
                "Headache",
                "Follow-up",
                "Chest discomfort",
                "Diabetes consultation",
                "Blood pressure check",
                "Pregnancy consultation",
                "Child health checkup",
                "Diet consultation"
            ])
        })

    df = pd.DataFrame(appointments)

    df.to_csv(
        os.path.join(OUTPUT_DIR, "appointments.csv"),
        index=False
    )

    print(f"✓ appointments.csv created ({len(df)} records)")

    return appointments


# ============================================================
# 6. MEDICAL RECORDS
# ============================================================

def generate_medical_records(
    patients,
    doctors,
    appointments,
    count=1500
):

    records = []

    for i in range(1, count + 1):

        appointment = random.choice(appointments)

        patient_id = appointment["patient_id"]
        doctor_id = appointment["doctor_id"]

        records.append({
            "record_id": f"MR{i:04d}",
            "patient_id": patient_id,
            "appointment_id": appointment["appointment_id"],
            "doctor_id": doctor_id,
            "diagnosis": random.choice(DIAGNOSES),
            "symptoms": random.choice([
                "Headache and fatigue",
                "Fever and body pain",
                "Shortness of breath",
                "Abdominal discomfort",
                "High blood pressure",
                "Joint pain",
                "Cough and cold",
                "Increased thirst",
                "Dizziness"
            ]),
            "record_date": appointment["appointment_date"],
            "severity": random.choice(SEVERITY),
            "notes": "Patient evaluated during consultation."
        })

    df = pd.DataFrame(records)

    df.to_csv(
        os.path.join(OUTPUT_DIR, "medical_records.csv"),
        index=False
    )

    print(
        f"✓ medical_records.csv created ({len(df)} records)"
    )

    return records


# ============================================================
# 7. PRESCRIPTIONS
# ============================================================

def generate_prescriptions(
    patients,
    doctors,
    appointments,
    medications,
    count=1500
):

    prescriptions = []

    for i in range(1, count + 1):

        appointment = random.choice(appointments)
        medication = random.choice(medications)

        prescriptions.append({
            "prescription_id": f"RX{i:04d}",
            "patient_id": appointment["patient_id"],
            "doctor_id": appointment["doctor_id"],
            "appointment_id": appointment["appointment_id"],
            "medication_id": medication["medication_id"],
            "dosage": random.choice([
                "250mg",
                "500mg",
                "5mg",
                "10mg",
                "20mg"
            ]),
            "frequency": random.choice([
                "Once Daily",
                "Twice Daily",
                "Three Times Daily",
                "As Needed"
            ]),
            "duration_days": random.choice([
                3,
                5,
                7,
                14,
                30,
                60
            ]),
            "prescription_date": appointment["appointment_date"]
        })

    df = pd.DataFrame(prescriptions)

    df.to_csv(
        os.path.join(OUTPUT_DIR, "prescriptions.csv"),
        index=False
    )

    print(
        f"✓ prescriptions.csv created ({len(df)} records)"
    )

    return prescriptions


# ============================================================
# 8. LAB TESTS
# ============================================================

def generate_lab_tests(
    patients,
    appointments,
    count=2000
):

    lab_tests = []

    for i in range(1, count + 1):

        appointment = random.choice(appointments)

        test_name, category = random.choice(
            LAB_TESTS
        )

        lab_tests.append({
            "test_id": f"T{i:04d}",
            "patient_id": appointment["patient_id"],
            "appointment_id": appointment["appointment_id"],
            "test_name": test_name,
            "test_category": category,
            "test_date": appointment["appointment_date"],
            "result": random.choice([
                "Normal",
                "Within normal range",
                "Slightly elevated",
                "Elevated",
                "Requires follow-up"
            ]),
            "normal_range": random.choice([
                "Normal range",
                "70-100 mg/dL",
                "4.0-6.0 %",
                "60-100 bpm"
            ]),
            "status": random.choice([
                "Completed",
                "Pending",
                "Reviewed"
            ]),
            "cost": round(
                random.uniform(200, 2500),
                2
            )
        })

    df = pd.DataFrame(lab_tests)

    df.to_csv(
        os.path.join(OUTPUT_DIR, "lab_tests.csv"),
        index=False
    )

    print(
        f"✓ lab_tests.csv created ({len(df)} records)"
    )

    return lab_tests


# ============================================================
# 9. BILLING
# ============================================================

def generate_billing(
    patients,
    appointments,
    doctors,
    count=2000
):

    billing_records = []

    for i in range(1, count + 1):

        appointment = random.choice(appointments)

        doctor = next(
            d for d in doctors
            if d["doctor_id"] == appointment["doctor_id"]
        )

        consultation_fee = float(
            doctor["consultation_fee"]
        )

        lab_charges = round(
            random.uniform(0, 3000),
            2
        )

        medicine_charges = round(
            random.uniform(0, 2000),
            2
        )

        discount = round(
            random.uniform(0, 500),
            2
        )

        insurance = round(
            random.uniform(0, 2000),
            2
        )

        total = max(
            consultation_fee
            + lab_charges
            + medicine_charges
            - discount
            - insurance,
            0
        )

        billing_records.append({
            "bill_id": f"B{i:04d}",
            "patient_id": appointment["patient_id"],
            "appointment_id": appointment["appointment_id"],
            "bill_date": appointment["appointment_date"],
            "consultation_fee": consultation_fee,
            "lab_charges": lab_charges,
            "medicine_charges": medicine_charges,
            "discount": discount,
            "insurance_coverage": insurance,
            "total_amount": round(total, 2),
            "payment_method": random.choice(
                PAYMENT_METHODS
            ),
            "payment_status": random.choice(
                PAYMENT_STATUS
            )
        })

    df = pd.DataFrame(billing_records)

    df.to_csv(
        os.path.join(OUTPUT_DIR, "billing.csv"),
        index=False
    )

    print(
        f"✓ billing.csv created ({len(df)} records)"
    )

    return billing_records


# ============================================================
# MAIN PROGRAM
# ============================================================

def main():

    print("\n========================================")
    print(" Lifespring Healthcare Data Generator")
    print("========================================\n")

    print("Generating synthetic healthcare data...\n")

    # 1. Departments
    departments = generate_departments()

    # 2. Doctors
    doctors = generate_doctors()

    # 3. Patients
    patients = generate_patients(300)

    # 4. Medications
    medications = generate_medications()

    # 5. Appointments
    appointments = generate_appointments(
        patients,
        doctors,
        2000
    )

    # 6. Medical Records
    medical_records = generate_medical_records(
        patients,
        doctors,
        appointments,
        1500
    )

    # 7. Prescriptions
    prescriptions = generate_prescriptions(
        patients,
        doctors,
        appointments,
        medications,
        1500
    )

    # 8. Lab Tests
    lab_tests = generate_lab_tests(
        patients,
        appointments,
        2000
    )

    # 9. Billing
    billing = generate_billing(
        patients,
        appointments,
        doctors,
        2000
    )

    print("\n========================================")
    print(" Data generation completed successfully!")
    print("========================================")

    print("\nFiles created inside:", OUTPUT_DIR)


if __name__ == "__main__":
    main()