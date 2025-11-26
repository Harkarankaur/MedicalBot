import random
from faker import Faker
from datetime import datetime, timedelta
from symptoms import REAL_DISEASES,SYMPTOMS
# Import all insert functions from db.py
from ndb import (
    insert_patient, insert_doctor, insert_appointment, insert_disease,
    insert_patient_condition, insert_symptom, insert_patient_symptom,
    insert_treatment, insert_patient_treatment, insert_medicine,
    insert_prescription, insert_billing, insert_staff,
    insert_diagnostic_report, insert_document_reference,
)

fake = Faker()

# --------------------------
# CONFIG
# --------------------------
NUM_PATIENTS = 500
NUM_DOCTORS = 80
NUM_DISEASES = 100
NUM_SYMPTOMS = 150
NUM_TREATMENTS = 200
NUM_MEDICINES = 500
NUM_STAFF = 100


# --------------------------
# HELPERS
# --------------------------
def random_date(days=365):
    return (datetime.now() - timedelta(days=random.randint(1, days))).strftime("%Y-%m-%d")

def random_timestamp(days=1000):
    """Generate a random timestamp within the last <days> days."""
    dt = datetime.now() - timedelta(
        days=random.randint(1, days),
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59),
        seconds=random.randint(0, 59)
    )
    return dt.strftime("%Y-%m-%d %H:%M:%S")

# --------------------------
# STORAGE
# --------------------------
patients = []
doctors = []
diseases = []
symptoms = []
treatments = []
medicines = []
appointments = []

# --------------------------
# GENERATE PATIENTS
# --------------------------
print("Creating patients...")

for _ in range(NUM_PATIENTS):
    p_id = insert_patient(
        name=fake.name(),
        gender=random.choice(["male", "female"]),
        birth_date=random_date(20000),
        phone=fake.phone_number(),
        email=fake.email(),
        address=fake.address(),
        emergency_contact_phone=fake.phone_number(),
        blood_group=random.choice(["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"]),
        fhir_id=f"pat-{fake.uuid4()[:8]}",
        created_at=random_timestamp(2000),
        updated_at=random_timestamp(500)
    )
    patients.append(p_id)


# --------------------------
# GENERATE DOCTORS
# --------------------------
print("Creating doctors...")

for _ in range(NUM_DOCTORS):
    d_id = insert_doctor(
        fhir_id=f"doc-{fake.uuid4()[:8]}",
        name=fake.name(),
        specialization=random.choice(["Cardiology", "Neurology", "General", "Orthopedic", "Dermatology"]),
        phone=fake.phone_number(),
        email=fake.email(),
        department=random.choice(["OPD", "Emergency", "Surgery", "ICU"]),
        qualification=random.choice(["MBBS", "MBBS MD", "MBBS MS"]),
        years_of_experience=random.randint(1, 35)
    )
    doctors.append(d_id)


# --------------------------
# DISEASES
# --------------------------
print("Creating diseases...")

for d in REAL_DISEASES:
    dis_id = insert_disease(
        name=d,
        description=f"A condition known as {d}."
    )
    diseases.append(dis_id)


# --------------------------
# SYMPTOMS
# --------------------------
# REAL SYMPTOMS
print("Creating real symptoms...")

for (name, desc) in SYMPTOMS:
    sym_id = insert_symptom(
        name=name,
        description=desc    # use real description from dataset
    )
    symptoms.append(sym_id)

# --------------------------
# TREATMENTS
# --------------------------
print("Creating treatments...")

for _ in range(NUM_TREATMENTS):
    t_id = insert_treatment(
        name=fake.word().capitalize(),
        description=fake.text()
    )
    treatments.append(t_id)


# --------------------------
# MEDICINES
# --------------------------
print("Creating medicines...")

for _ in range(NUM_MEDICINES):
    m_id = insert_medicine(
        name=fake.word().capitalize(),
        type=random.choice(["Tablet", "Syrup", "Injection", "Capsule"]),
        description=fake.text()
    )
    medicines.append(m_id)


# --------------------------
# STAFF
# --------------------------
print("Creating staff...")

roles = ["Nurse", "Receptionist", "Lab Technician", "Pharmacist", "Manager"]

for _ in range(NUM_STAFF):
    insert_staff(
        name=fake.name(),
        role=random.choice(roles),
        phone=fake.phone_number(),
        email=fake.email()
    )


# --------------------------
# APPOINTMENTS + RELATED DATA
# --------------------------
print("Creating appointments & related records...")

for p in patients:

    for _ in range(random.randint(1, 3)):

        doctor = random.choice(doctors)
        appt_date = random_date(365)

        # Appointment
        appt_id = insert_appointment(
            patient_id=p,
            practitioner_id=doctor,
            encounter_date=appt_date,
            status="finished",
            fhir_id=f"enc-{fake.uuid4()[:8]}"
        )
        appointments.append(appt_id)

        # Condition
        insert_patient_condition(
            patient_id=p,
            disease_id=random.choice(diseases),
            code=f"C{random.randint(100,999)}",
            description=fake.sentence(),
            onset_date=random_date(2000),
            status=random.choice(["active", "resolved"]),
            fhir_id=f"cond-{fake.uuid4()[:8]}"
        )

        # Patient Symptoms
        for _ in range(random.randint(1, 4)):
            insert_patient_symptom(
                patient_id=p,
                symptom_id=random.choice(symptoms),
                noted_on=random_date(365)
            )

        # Treatment
        tr = random.choice(treatments)
        insert_patient_treatment(
            name=fake.word().capitalize(),
            description=fake.text(),
            patient_id=p,
            treatment_id=tr,
            doctor_id=doctor,
            start_date=random_date(300),
            end_date=random_date(200),
            notes=fake.text()
            )


        # Prescription
        insert_prescription(
            patient_id=p,
            doctor_id=doctor,
            medicine_id=random.choice(medicines),
            dosage="1 tablet",
            frequency="Twice a day",
            duration="5 days",
            instructions="Take after meals",
            prescribed_on=appt_date
        )

        # Billing
        amount = random.randint(500, 5000)
        discount = amount * 0.10
        tax = amount * 0.05

        insert_billing(
            patient_id=p,
            amount=amount,
            discount=discount,
            tax=tax,
            total_amount=amount - discount + tax,
            payment_status=random.choice(["paid", "pending"])
        )

        # Diagnostic Report
        insert_diagnostic_report(
            patient_id=p,
            encounter_id=appt_id,
            code=f"DX-{random.randint(100,999)}",
            conclusion=fake.sentence(),
            issued=appt_date,
            fhir_id=f"rep-{fake.uuid4()[:8]}"
        )

        # Document Reference
        insert_document_reference(
            patient_id=p,
            encounter_id=appt_id,
            title="Nurse Notes",
            content=fake.text(),
            author=fake.name(),
            date=appt_date,
            fhir_id=f"doc-{fake.uuid4()[:8]}"
        )


print("\n🎉 Synthetic data generation completed successfully!")
