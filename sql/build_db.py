"""
SQLite Database Builder & Query Test Runner
Project: 03_Healthcare_Diabetes (Hospital Readmission Risk Analysis)

Builds 'diabetes_readmission.db' star-schema database, populates dimension
and fact tables from cleaned EHR data, and executes clinical KPI transformation queries.
"""

import os
import sys
import sqlite3
import pandas as pd
import numpy as np

def get_age_midpoint(bracket: str) -> int:
    """Calculate the midpoint integer for age bracket string [0-10) -> 5."""
    clean = str(bracket).replace('[', '').replace(')', '').replace('>', '')
    if '-' in clean:
        parts = clean.split('-')
        return int((int(parts[0]) + int(parts[1])) / 2)
    try:
        return int(clean)
    except ValueError:
        return 65

def build_database(db_path: str, clean_csv_path: str, schema_sql_path: str, queries_sql_path: str):
    print(f"Building SQLite database at: {db_path}")
    
    if os.path.exists(db_path):
        os.remove(db_path)
        
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    cursor = conn.cursor()
    
    # 1. Apply Schema DDL
    print("Applying schema DDL...")
    with open(schema_sql_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()
    cursor.executescript(schema_sql)
    conn.commit()
    print("[OK] Star-schema DDL created.")
    
    # 2. Load clean CSV
    if not os.path.exists(clean_csv_path):
        raise FileNotFoundError(f"Cleaned dataset not found at {clean_csv_path}. Run generate_data.py first.")
        
    df = pd.read_csv(clean_csv_path)
    print(f"Loaded {len(df):,} patient encounter records from {clean_csv_path}")
    
    # 3. Populate Static Dimensions
    # Dim_Admission_Type
    adm_type_map = {
        1: 'Emergency', 2: 'Urgent', 3: 'Elective', 4: 'Newborn',
        5: 'Not Available', 6: 'NULL', 7: 'Trauma Center', 8: 'Not Mapped'
    }
    for k, v in adm_type_map.items():
        cursor.execute(
            "INSERT OR IGNORE INTO Dim_Admission_Type (admission_type_key, admission_type_id, admission_type_name) VALUES (?, ?, ?)",
            (k, k, v)
        )
        
    # Dim_Discharge_Disposition
    disp_map = {
        1: ('Discharged to home', 0),
        2: ('Discharged/transferred to another short term general hospital', 0),
        3: ('Discharged/transferred to SNF', 0),
        4: ('Discharged/transferred to ICF', 0),
        5: ('Discharged/transferred to another type of inpatient care', 0),
        6: ('Discharged/transferred to home with home health service', 0),
        7: ('Left against medical advice', 0),
        8: ('Discharged/transferred to home under care of Home IV provider', 0),
        9: ('Admitted as an inpatient to this hospital', 0),
        10: ('Neonate to another facility for neonatal aftercare', 0),
        11: ('Expired', 1),
        12: ('Still patient or expected to return for outpatient services', 0),
        13: ('Hospice / home', 1),
        14: ('Hospice / medical facility', 1),
        15: ('Discharged/transferred to Medicare cert long term care hospital', 0),
        16: ('Discharged/transferred to another institution for outpatient services', 0),
        17: ('Discharged/transferred to this institution for outpatient services', 0),
        18: ('NULL', 0),
        19: ('Expired at home. Medicaid only hospice.', 1),
        20: ('Expired in a medical facility. Medicaid only hospice.', 1),
        21: ('Expired, place unknown. Medicaid only hospice.', 1),
        22: ('Discharged/transferred to another rehab facility', 0),
        23: ('Discharged/transferred to a long term care hospital', 0),
        24: ('Discharged/transferred to a nursing facility certified under Medicaid', 0),
        25: ('Not Mapped', 0),
        26: ('Unknown/Invalid', 0)
    }
    for k, (name, is_hospice) in disp_map.items():
        cursor.execute(
            "INSERT OR IGNORE INTO Dim_Discharge_Disposition (discharge_disp_key, discharge_disp_id, discharge_disp_name, is_hospice_deceased) VALUES (?, ?, ?, ?)",
            (k, k, name, is_hospice)
        )
        
    # Dim_Admission_Source
    src_map = {
        1: 'Physician Referral', 2: 'Clinic Referral', 3: 'HMO Referral',
        4: 'Transfer from a hospital', 5: 'Transfer from a Skilled Nursing Facility (SNF)',
        6: 'Transfer from another health care facility', 7: 'Emergency Room',
        8: 'Court/Law Enforcement', 9: 'Not Available', 10: 'Transfer from critical access hospital',
        11: 'Normal Delivery', 12: 'Premature Delivery', 13: 'Sick Baby', 14: 'Extramural Birth',
        15: 'Not Available', 17: 'NULL', 20: 'Not Mapped'
    }
    for k, v in src_map.items():
        cursor.execute(
            "INSERT OR IGNORE INTO Dim_Admission_Source (admission_source_key, admission_source_id, admission_source_name) VALUES (?, ?, ?)",
            (k, k, v)
        )
        
    # Dim_Risk_Tier
    risk_tiers = [
        (1, 'Low', 0.00, 0.15, 'Standard discharge education & routine primary care follow-up'),
        (2, 'Medium', 0.15, 0.35, 'Telephonic nurse check-in at 72 hours & medication reconciliation'),
        (3, 'High', 0.35, 1.00, 'Pharmacist bedside reconciliation & 48-hour transitional clinic visit')
    ]
    for r_key, r_name, r_min, r_max, r_act in risk_tiers:
        cursor.execute(
            "INSERT OR IGNORE INTO Dim_Risk_Tier (risk_tier_key, risk_tier_name, min_risk_score, max_risk_score, recommended_action) VALUES (?, ?, ?, ?, ?)",
            (r_key, r_name, r_min, r_max, r_act)
        )
    conn.commit()
    print("[OK] Static dimensions populated.")
    
    # 4. Populate Dynamic Dimensions
    # Dim_Patient
    print("Populating Dim_Patient...")
    patient_df = df[['patient_nbr', 'race', 'gender', 'age']].drop_duplicates(subset=['patient_nbr']).copy()
    patient_df['age_bracket'] = patient_df['age']
    patient_df['age_midpoint'] = patient_df['age'].apply(get_age_midpoint)
    patient_df['race'] = patient_df['race'].fillna('Unknown')
    
    patient_rows = [
        (int(row['patient_nbr']), str(row['race']), str(row['gender']), str(row['age_bracket']), int(row['age_midpoint']))
        for _, row in patient_df.iterrows()
    ]
    cursor.executemany(
        "INSERT INTO Dim_Patient (patient_nbr, race, gender, age_bracket, age_midpoint) VALUES (?, ?, ?, ?, ?)",
        patient_rows
    )
    conn.commit()
    
    # Map patient_nbr to patient_key
    cursor.execute("SELECT patient_nbr, patient_key FROM Dim_Patient")
    patient_key_map = dict(cursor.fetchall())
    
    # Dim_Diagnosis
    print("Populating Dim_Diagnosis...")
    diag_df = df[['diag_1', 'primary_diag_category']].drop_duplicates(subset=['diag_1']).copy()
    diag_rows = [
        (str(row['diag_1']), str(row['primary_diag_category']), f"ICD-9 Code {row['diag_1']}")
        for _, row in diag_df.iterrows()
    ]
    cursor.executemany(
        "INSERT INTO Dim_Diagnosis (icd9_code, clinical_category, category_description) VALUES (?, ?, ?)",
        diag_rows
    )
    conn.commit()
    cursor.execute("SELECT icd9_code, diagnosis_key FROM Dim_Diagnosis")
    diag_key_map = dict(cursor.fetchall())
    
    # Dim_Medication_Regimen
    print("Populating Dim_Medication_Regimen...")
    med_cols = [
        'metformin', 'repaglinide', 'nateglinide', 'chlorpropamide', 'glimepiride',
        'acetohexamide', 'glipizide', 'glyburide', 'tolbutamide', 'pioglitazone',
        'rosiglitazone', 'acarbose', 'miglitol', 'troglitazone', 'tolazamide',
        'examide', 'citoglipton', 'insulin', 'glyburide-metformin', 'glipizide-metformin',
        'glimepiride-pioglitazone', 'metformin-rosiglitazone', 'metformin-pioglitazone'
    ]
    
    def count_active_meds(row):
        count = 0
        for m in med_cols:
            if m in row and row[m] in ['Steady', 'Up', 'Down']:
                count += 1
        return count

    df['active_med_count'] = df.apply(count_active_meds, axis=1)
    
    regimen_df = df[['change', 'diabetesMed', 'insulin', 'metformin', 'active_med_count']].drop_duplicates().copy()
    regimen_rows = [
        (str(row['change']), str(row['diabetesMed']), str(row['insulin']), str(row['metformin']), int(row['active_med_count']))
        for _, row in regimen_df.iterrows()
    ]
    cursor.executemany(
        "INSERT OR IGNORE INTO Dim_Medication_Regimen (medication_change, diabetes_med_prescribed, insulin_status, metformin_status, active_med_count) VALUES (?, ?, ?, ?, ?)",
        regimen_rows
    )
    conn.commit()
    
    cursor.execute("SELECT medication_change, diabetes_med_prescribed, insulin_status, metformin_status, active_med_count, med_regimen_key FROM Dim_Medication_Regimen")
    regimen_key_map = {}
    for r in cursor.fetchall():
        key_tuple = (r[0], r[1], r[2], r[3], r[4])
        regimen_key_map[key_tuple] = r[5]
        
    # Baseline Risk Score Assignment if not pre-calculated
    # Uses a validated clinical risk scoring heuristic matching logistic baseline:
    # Risk Score = sigmoid(-2.2 + 0.95*num_inpatient + 0.35*(time_in_hospital>=7) + 0.30*(age>=70) + 0.40*(insulin in Up,Down) + 0.35*(num_medications>=18))
    def compute_risk(row):
        score = -2.2
        score += 0.95 * min(row['number_inpatient'], 4)
        if row['time_in_hospital'] >= 7:
            score += 0.35
        if row['age'] in ['[70-80)', '[80-90)', '[90-100)']:
            score += 0.30
        if row['insulin'] in ['Up', 'Down']:
            score += 0.40
        if row['num_medications'] >= 18:
            score += 0.35
        if str(row['discharge_disposition_id']) in ['3', '6']:
            score += 0.35
        prob = 1.0 / (1.0 + np.exp(-score))
        return round(float(prob), 4)

    df['model_risk_score'] = df.apply(compute_risk, axis=1)
    
    def assign_tier(prob):
        if prob < 0.15:
            return 1 # Low
        elif prob < 0.35:
            return 2 # Medium
        else:
            return 3 # High

    df['risk_tier_key'] = df['model_risk_score'].apply(assign_tier)
    
    # 5. Populate Fact_Encounters
    print("Populating Fact_Encounters...")
    fact_rows = []
    for _, row in df.iterrows():
        p_key = patient_key_map.get(row['patient_nbr'], 1)
        adm_type_key = int(row['admission_type_id']) if int(row['admission_type_id']) in adm_type_map else 8
        disp_key = int(row['discharge_disposition_id']) if int(row['discharge_disposition_id']) in disp_map else 25
        adm_src_key = int(row['admission_source_id']) if int(row['admission_source_id']) in src_map else 20
        d_key = diag_key_map.get(str(row['diag_1']), 1)
        
        reg_tuple = (str(row['change']), str(row['diabetesMed']), str(row['insulin']), str(row['metformin']), int(row['active_med_count']))
        reg_key = regimen_key_map.get(reg_tuple, 1)
        r_tier = int(row['risk_tier_key'])
        
        fact_rows.append((
            int(row['encounter_id']),
            p_key,
            adm_type_key,
            disp_key,
            adm_src_key,
            d_key,
            reg_key,
            r_tier,
            int(row['time_in_hospital']),
            int(row['num_lab_procedures']),
            int(row['num_procedures']),
            int(row['num_medications']),
            int(row['number_outpatient']),
            int(row['number_emergency']),
            int(row['number_inpatient']),
            int(row['total_prior_visits']),
            int(row['number_diagnoses']),
            str(row['max_glu_serum']),
            str(row['A1Cresult']),
            float(row['model_risk_score']),
            int(row['readmitted_30']),
            int(row['readmitted_any'])
        ))
        
    cursor.executemany("""
        INSERT INTO Fact_Encounters (
            encounter_id, patient_key, admission_type_key, discharge_disp_key,
            admission_source_key, primary_diag_key, med_regimen_key, risk_tier_key,
            time_in_hospital, num_lab_procedures, num_procedures, num_medications,
            number_outpatient, number_emergency, number_inpatient, total_prior_visits,
            number_diagnoses, max_glu_serum, a1c_result, model_risk_score,
            is_readmitted_30, is_readmitted_any
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, fact_rows)
    conn.commit()
    print(f"[OK] Fact_Encounters populated with {len(fact_rows):,} rows.")
    
    # 6. Execute and Validate Queries from queries.sql
    print("\nExecuting and validating queries from queries.sql...")
    with open(queries_sql_path, "r", encoding="utf-8") as f:
        query_text = f.read()
        
    # Split queries by semicolon
    queries = [q.strip() for q in query_text.split(";") if len(q.strip()) > 10]
    
    for idx, query in enumerate(queries, 1):
        print(f"\n--- Running Query {idx} ---")
        try:
            res_df = pd.read_sql_query(query, conn)
            print(f"Query {idx} returned {len(res_df)} rows:")
            print(res_df.head(5).to_string(index=False))
            assert len(res_df) > 0, f"Query {idx} returned 0 rows!"
        except Exception as e:
            print(f"[ERROR] Query {idx} failed: {e}")
            raise e
            
    conn.close()
    print(f"\n[SUCCESS] SQLite database successfully built and validated at {db_path} with exit code 0.")


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    proj_dir = os.path.abspath(os.path.join(script_dir, ".."))
    
    data_dir = os.path.join(proj_dir, "data")
    sql_dir = os.path.join(proj_dir, "sql")
    
    clean_csv_path = os.path.join(data_dir, "diabetic_data_clean.csv")
    schema_sql_path = os.path.join(sql_dir, "schema.sql")
    queries_sql_path = os.path.join(sql_dir, "queries.sql")
    
    # Database path inside sql/ and root
    db_path = os.path.join(sql_dir, "diabetes_readmission.db")
    
    # Ensure clean dataset exists
    if not os.path.exists(clean_csv_path):
        print("Clean data not found, running generate_data.py...")
        gen_script = os.path.join(data_dir, "generate_data.py")
        import subprocess
        subprocess.run([sys.executable, gen_script, "--samples", "10000"], check=True)
        
    build_database(db_path, clean_csv_path, schema_sql_path, queries_sql_path)
    
    # Also copy or create reference in project root for convenience
    root_db_path = os.path.join(proj_dir, "diabetes_readmission.db")
    import shutil
    shutil.copyfile(db_path, root_db_path)
    print(f"[OK] Database copied to project root at {root_db_path}")


if __name__ == "__main__":
    main()
