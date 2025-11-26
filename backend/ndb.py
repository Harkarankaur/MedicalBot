import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")

def get_conn():
    return psycopg2.connect(
        host=DB_HOST, dbname=DB_NAME, user=DB_USER, password=DB_PASS
    )


# ---------------------- CREATE TABLES ----------------------
def create_tables():
    conn = get_conn()
    cur = conn.cursor()

    # Patients
    cur.execute("""
        CREATE TABLE IF NOT EXISTS patients (
            patient_id SERIAL PRIMARY KEY,
            fhir_id VARCHAR(50),
            name TEXT NOT NULL,
            gender TEXT,
            birth_date DATE,
            phone TEXT,
            email VARCHAR(100),
            address TEXT,
            emergency_contact_phone TEXT,
            blood_group VARCHAR(5),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Doctors
    cur.execute("""
        CREATE TABLE IF NOT EXISTS doctors (
            doctor_id SERIAL PRIMARY KEY,
            fhir_id VARCHAR(50),
            name TEXT NOT NULL,
            specialization VARCHAR(100),
            phone TEXT,
            email VARCHAR(100),
            department VARCHAR(100),
            qualification VARCHAR(100),
            years_of_experience INT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Appointments
    cur.execute("""
        CREATE TABLE IF NOT EXISTS appointments (
            appointment_id SERIAL PRIMARY KEY,
            fhir_id VARCHAR(50),
            patient_id INT REFERENCES patients(patient_id),
            practitioner_id INT REFERENCES doctors(doctor_id),
            encounter_date TIMESTAMP,
            status TEXT,
            reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Diseases
    cur.execute("""
        CREATE TABLE IF NOT EXISTS diseases (
            disease_id SERIAL PRIMARY KEY,
            name VARCHAR(200),
            description TEXT
        );
    """)

    # Patient Conditions
    cur.execute("""
        CREATE TABLE IF NOT EXISTS patient_conditions (
            patient_conditions_id SERIAL PRIMARY KEY,
            fhir_id VARCHAR(50),
            patient_id INT REFERENCES patients(patient_id),
            disease_id INT REFERENCES diseases(disease_id),
            code VARCHAR(50),
            description TEXT,
            onset_date DATE,
            status VARCHAR(20)
        );
    """)

    # Symptoms
    cur.execute("""
        CREATE TABLE IF NOT EXISTS symptoms (
            symptom_id SERIAL PRIMARY KEY,
            name VARCHAR(200),
            description TEXT
        );
    """)

    # Patient Symptoms
    cur.execute("""
        CREATE TABLE IF NOT EXISTS patient_symptoms (
            ps_id SERIAL PRIMARY KEY,
            patient_id INT REFERENCES patients(patient_id),
            symptom_id INT REFERENCES symptoms(symptom_id),
            noted_on DATE
        );
    """)

    # Treatments
    cur.execute("""
        CREATE TABLE IF NOT EXISTS treatments (
            treatment_id SERIAL PRIMARY KEY,
            name VARCHAR(200),
            description TEXT
        );
    """)

    # Patient Treatments  (FIXED: missing comma)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS patient_treatments (
            id SERIAL PRIMARY KEY,
            name VARCHAR(200),
            description TEXT,
            patient_id INT REFERENCES patients(patient_id),
            treatment_id INT REFERENCES treatments(treatment_id),
            doctor_id INT REFERENCES doctors(doctor_id),
            start_date DATE,
            end_date DATE,
            notes TEXT
        );
    """)

    # Medicines
    cur.execute("""
        CREATE TABLE IF NOT EXISTS medicines (
            medicine_id SERIAL PRIMARY KEY,
            name VARCHAR(200),
            type VARCHAR(50),
            description TEXT
        );
    """)

    # Prescriptions
    cur.execute("""
        CREATE TABLE IF NOT EXISTS prescriptions (
            prescription_id SERIAL PRIMARY KEY,
            patient_id INT REFERENCES patients(patient_id),
            doctor_id INT REFERENCES doctors(doctor_id),
            medicine_id INT REFERENCES medicines(medicine_id),
            dosage VARCHAR(100),
            frequency VARCHAR(100),
            duration VARCHAR(100),
            instructions TEXT,
            prescribed_on DATE
        );
    """)

    # Billing
    cur.execute("""
        CREATE TABLE IF NOT EXISTS billing (
            bill_id SERIAL PRIMARY KEY,
            patient_id INT REFERENCES patients(patient_id),
            amount DECIMAL(10, 2),
            discount DECIMAL(10, 2),
            tax DECIMAL(10, 2),
            total_amount DECIMAL(10, 2),
            payment_status VARCHAR(50),
            generated_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Staff
    cur.execute("""
        CREATE TABLE IF NOT EXISTS staff (
            staff_id SERIAL PRIMARY KEY,
            name VARCHAR(100),
            role VARCHAR(100),
            phone TEXT,
            email VARCHAR(100)
        );
    """)

    # Diagnostic Reports
    cur.execute("""
        CREATE TABLE IF NOT EXISTS diagnostic_reports (
            id SERIAL PRIMARY KEY,
            fhir_id VARCHAR(50),
            patient_id INT REFERENCES patients(patient_id),
            encounter_id INT REFERENCES appointments(appointment_id),
            code TEXT,
            conclusion TEXT,
            issued TIMESTAMP
        );
    """)

    # Document References
    cur.execute("""
        CREATE TABLE IF NOT EXISTS document_references (
            id SERIAL PRIMARY KEY,
            fhir_id VARCHAR(50),
            patient_id INT REFERENCES patients(patient_id),
            encounter_id INT REFERENCES appointments(appointment_id),
            title TEXT,
            content TEXT,
            author TEXT,
            date TIMESTAMP
        );
    """)

    conn.commit()
    cur.close()
    conn.close()



# ---------------------- INSERT FUNCTIONS ----------------------
# (ALL functions below follow same style and always open/close DB)
def insert_patient(
    name, gender, birth_date, phone="", email=None, address="",
    fhir_id=None, emergency_contact_phone=None, blood_group=None,
    created_at=None, updated_at=None
):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO patients 
        (fhir_id, name, gender, birth_date, phone, email, address, 
        emergency_contact_phone, blood_group, created_at, updated_at)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        RETURNING patient_id;
    """, (
        fhir_id, name, gender, birth_date, phone, email, address,
        emergency_contact_phone, blood_group, created_at, updated_at
    ))

    new_id = cur.fetchone()[0]

    conn.commit()
    cur.close()
    conn.close()
    return new_id

def insert_doctor(fhir_id, name, specialization, phone, email, department, qualification, years_of_experience):

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO doctors 
        (fhir_id, name, specialization, phone, email, department, qualification, years_of_experience)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        RETURNING doctor_id;
    """, (fhir_id, name, specialization, phone, email, department, qualification, years_of_experience))

    new_id = cur.fetchone()[0]

    conn.commit()
    cur.close()
    conn.close()
    return new_id


def insert_appointment(patient_id, practitioner_id, encounter_date, status="finished", fhir_id=None):

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO appointments 
        (fhir_id, patient_id, practitioner_id, encounter_date, status)
        VALUES (%s,%s,%s,%s,%s)
        RETURNING appointment_id;
    """, (fhir_id, patient_id, practitioner_id, encounter_date, status))

    new_id = cur.fetchone()[0]

    conn.commit()
    cur.close()
    conn.close()
    return new_id


def insert_disease(name, description):

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO diseases (name, description)
        VALUES (%s, %s)
        RETURNING disease_id;
    """, (name, description))

    new_id = cur.fetchone()[0]

    conn.commit()
    cur.close()
    conn.close()
    return new_id



def insert_patient_condition(patient_id, disease_id, code, description, onset_date, status="active", fhir_id=None):

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO patient_conditions 
        (fhir_id, patient_id, disease_id, code, description, onset_date, status)
        VALUES (%s,%s,%s,%s,%s,%s,%s)
        RETURNING patient_conditions_id;
    """, (fhir_id, patient_id, disease_id, code, description, onset_date, status))

    new_id = cur.fetchone()[0]

    conn.commit()
    cur.close()
    conn.close()
    return new_id



def insert_symptom(name, description):

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO symptoms (name, description)
        VALUES (%s, %s)
        RETURNING symptom_id;
    """, (name, description))

    new_id = cur.fetchone()[0]

    conn.commit()
    cur.close()
    conn.close()
    return new_id



def insert_patient_symptom(patient_id, symptom_id, noted_on):

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO patient_symptoms (patient_id, symptom_id, noted_on)
        VALUES (%s,%s,%s)
        RETURNING ps_id;
    """, (patient_id, symptom_id, noted_on))

    new_id = cur.fetchone()[0]

    conn.commit()
    cur.close()
    conn.close()
    return new_id



def insert_treatment(name, description):

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO treatments (name, description)
        VALUES (%s,%s)
        RETURNING treatment_id;
    """, (name, description))

    new_id = cur.fetchone()[0]

    conn.commit()
    cur.close()
    conn.close()
    return new_id



def insert_patient_treatment(name, description, patient_id, treatment_id, doctor_id, start_date, end_date, notes):

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO patient_treatments 
        (name, description, patient_id, treatment_id, doctor_id, start_date, end_date, notes)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        RETURNING id;
    """, (name, description, patient_id, treatment_id, doctor_id, start_date, end_date, notes))

    new_id = cur.fetchone()[0]

    conn.commit()
    cur.close()
    conn.close()
    return new_id



def insert_medicine(name, type, description):

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO medicines (name, type, description)
        VALUES (%s,%s,%s)
        RETURNING medicine_id;
    """, (name, type, description))

    new_id = cur.fetchone()[0]

    conn.commit()
    cur.close()
    conn.close()
    return new_id



def insert_prescription(patient_id, doctor_id, medicine_id, dosage, frequency, duration, instructions, prescribed_on):

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO prescriptions 
        (patient_id, doctor_id, medicine_id, dosage, frequency, duration, instructions, prescribed_on)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        RETURNING prescription_id;
    """, (patient_id, doctor_id, medicine_id, dosage, frequency, duration, instructions, prescribed_on))

    new_id = cur.fetchone()[0]

    conn.commit()
    cur.close()
    conn.close()
    return new_id



def insert_billing(patient_id, amount, discount, tax, total_amount, payment_status):

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO billing 
        (patient_id, amount, discount, tax, total_amount, payment_status)
        VALUES (%s,%s,%s,%s,%s,%s)
        RETURNING bill_id;
    """, (patient_id, amount, discount, tax, total_amount, payment_status))

    new_id = cur.fetchone()[0]

    conn.commit()
    cur.close()
    conn.close()
    return new_id



def insert_staff(name, role, phone, email):

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO staff (name, role, phone, email)
        VALUES (%s,%s,%s,%s)
        RETURNING staff_id;
    """, (name, role, phone, email))

    new_id = cur.fetchone()[0]

    conn.commit()
    cur.close()
    conn.close()
    return new_id



def insert_diagnostic_report(patient_id, encounter_id, code, conclusion, issued, fhir_id=None):

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO diagnostic_reports 
        (fhir_id, patient_id, encounter_id, code, conclusion, issued)
        VALUES (%s,%s,%s,%s,%s,%s)
        RETURNING id;
    """, (fhir_id, patient_id, encounter_id, code, conclusion, issued))

    new_id = cur.fetchone()[0]

    conn.commit()
    cur.close()
    conn.close()
    return new_id



def insert_document_reference(patient_id, encounter_id, title, content, author, date, fhir_id=None):

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO document_references 
        (fhir_id, patient_id, encounter_id, title, content, author, date)
        VALUES (%s,%s,%s,%s,%s,%s,%s)
        RETURNING id;
    """, (fhir_id, patient_id, encounter_id, title, content, author, date))

    new_id = cur.fetchone()[0]

    conn.commit()
    cur.close()
    conn.close()
    return new_id
