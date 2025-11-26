import psycopg2

# -----------------------------------------
# PostgreSQL Connection Configuration
# -----------------------------------------
DB_NAME = "my_new_db"
DB_USER = "postgres"
DB_PASSWORD = "medical123"
DB_HOST = "localhost"
DB_PORT = "5432"

# -----------------------------------------
# Real Hospital-Grade Symptoms Dataset
# -----------------------------------------
SYMPTOMS = [
    ("Fever", "Elevated body temperature often due to infection"),
    ("Cough", "Reflex action to clear mucus or irritants from airway"),
    ("Shortness of breath", "Difficulty breathing or feeling breathless"),
    ("Headache", "Pain or discomfort in the head or neck region"),
    ("Fatigue", "Extreme tiredness or lack of energy"),
    ("Chest pain", "Pain or pressure felt in the chest area"),
    ("Abdominal pain", "Pain in stomach or abdominal region"),
    ("Nausea", "Sensation of wanting to vomit"),
    ("Vomiting", "Forceful expulsion of stomach contents"),
    ("Diarrhea", "Loose or watery bowel movements"),
    ("Constipation", "Infrequent or difficult bowel movements"),
    ("Dizziness", "Sensation of spinning or loss of balance"),
    ("Fainting", "Temporary loss of consciousness"),
    ("Sweating", "Excessive or abnormal perspiration"),
    ("Palpitations", "Rapid or irregular heartbeat sensation"),
    ("Sore throat", "Pain or scratchiness in the throat"),
    ("Runny nose", "Excess nasal drainage"),
    ("Nasal congestion", "Blocked or stuffy nose"),
    ("Joint pain", "Pain or stiffness in joints"),
    ("Muscle pain", "Pain or tenderness in muscles"),
    ("Rash", "Visible skin irritation or discoloration"),
    ("Itching", "Sensation causing urge to scratch"),
    ("Back pain", "Pain in the lower or upper back"),
    ("Weight loss", "Unexpected reduction in body weight"),
    ("Weight gain", "Unexpected increase in body weight"),
    ("Loss of appetite", "Reduced desire to eat"),
    ("Increased appetite", "Unusual hunger or desire to eat more"),
    ("Anxiety", "Feeling of worry or fear"),
    ("Depression", "Mood disorder causing persistent sadness"),
    ("Sleep disturbance", "Trouble falling or staying asleep"),
    ("Swelling", "Enlargement of body parts due to fluid accumulation"),
    ("Blurred vision", "Reduced clarity of eyesight"),
    ("Hearing loss", "Reduced ability to hear sounds"),
    ("Tremors", "Involuntary rhythmic muscle movement"),
    ("Difficulty urinating", "Problems starting or maintaining urine flow"),
    ("Burning urination", "Pain or burning sensation during urination"),
    ("Frequent urination", "Increased urge to urinate"),
    ("Bleeding", "Loss of blood internally or externally"),
    ("Bruising", "Discoloration caused by bleeding under skin"),
    ("Weakness", "Reduced strength or function"),
    ("Confusion", "Impaired thinking or disorientation"),
    ("Seizures", "Uncontrolled electrical activity in brain"),
    ("Chills", "Shivering due to cold or fever"),
    ("Swollen lymph nodes", "Enlarged glands indicating infection"),
    ("Yellow skin (jaundice)", "Yellowing of skin due to liver issues"),
    ("Difficulty swallowing", "Trouble swallowing food or liquids"),
    ("Hoarseness", "Raspy or weak voice"),
    ("Chest tightness", "Feeling of pressure in the chest"),
    ("Rapid heartbeat", "Fast pulse rate"),
    ("Slow heartbeat", "Abnormally slow pulse"),
    ("Hair loss", "Unexpected loss of hair"),
    ("Dry mouth", "Reduced saliva causing dryness"),
    ("Dry skin", "Flaky, rough or dry skin texture"),
    ("Cold hands/feet", "Reduced circulation causing cool extremities"),
    ("Red eyes", "Redness due to irritation or infection"),
    ("Tearing", "Excessive eye watering"),
    ("Difficulty walking", "Problems with mobility or balance"),
    ("Numbness", "Loss of sensation"),
    ("Tingling", "Pins-and-needles sensation"),
    ("Abdominal bloating", "Swelling of stomach area"),
    ("Indigestion", "Discomfort after eating"),
    ("Heartburn", "Burning sensation in chest"),
    ("Cramps", "Sudden painful muscle contractions"),
    ("Loss of smell", "Reduced ability to detect odors"),
    ("Loss of taste", "Reduced ability to taste flavors"),
]
REAL_DISEASES = [
    "Influenza", "Pneumonia", "Asthma", "Diabetes Mellitus Type 1",
    "Diabetes Mellitus Type 2", "Hypertension", "Migraine",
    "Tuberculosis", "Malaria", "COVID-19", "Chickenpox", "Measles",
    "Bronchitis", "Arthritis", "Osteoporosis", "Dengue Fever",
    "Hepatitis A", "Hepatitis B", "Kidney Failure", "Urinary Tract Infection",
    "Sinusitis", "Heart Failure", "Coronary Artery Disease", "Stroke",
    "Liver Cirrhosis", "Appendicitis", "Gallstones", "Pancreatitis",
    "Anemia", "Hypothyroidism", "Hyperthyroidism", "COPD",
    "Epilepsy", "Depression", "Anxiety Disorder", "Schizophrenia",
    "Bipolar Disorder", "Dermatitis", "Psoriasis", "Eczema",
    "Acne", "Otitis Media", "Tonsillitis", "Gastritis", "GERD",
    "Irritable Bowel Syndrome", "Crohn's Disease", "Colitis",
    "Chronic Kidney Disease", "Lung Cancer", "Breast Cancer",
    "Prostate Cancer", "Cervical Cancer", "Leukemia", "Lymphoma",
    "Malnutrition", "Obesity", "HIV/AIDS", "Meningitis", "Encephalitis",
    "Conjunctivitis", "Glaucoma", "Cataract", "Vertigo", "Sciatica",
    "Fibromyalgia", "Rheumatoid Arthritis", "Scoliosis", "Fractures",
    "Burns", "Allergic Rhinitis", "Food Poisoning", "Heat Stroke",
    "Chronic Fatigue Syndrome", "Insomnia", "Panic Disorder",
    "Hypotension", "Hyperlipidemia", "Pneumothorax"
]

# -----------------------------------------
# Database Insertion Logic
# -----------------------------------------
def populate_symptoms():
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        cur = conn.cursor()

        print("Deleting existing symptoms...")
        cur.execute("DELETE FROM symptoms;")
        cur.execute("ALTER SEQUENCE symptoms_id_seq RESTART WITH 1;")

        print("Inserting new medical symptoms...")
        cur.executemany(
            "INSERT INTO symptoms (name, description) VALUES (%s, %s);",
            SYMPTOMS,
        )

        conn.commit()
        print("Symptoms table updated successfully!")

    except Exception as e:
        print("Error:", e)
    finally:
        if conn:
            cur.close()
            conn.close()


if __name__ == "__main__":
    populate_symptoms()
