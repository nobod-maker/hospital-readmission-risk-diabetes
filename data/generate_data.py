"""
High-Fidelity Synthetic Data Generator & Clinical ETL Pipeline
Project: 03_Healthcare_Diabetes (Hospital Readmission Risk Analysis)
Source Dataset: Diabetes 130-US Hospitals (1999-2008)

Generates:
1. data/diabetic_data.csv (Raw 50-column encounter dataset with realistic clinical distributions)
2. data/IDs_mapping.csv (Standard lookup tables for admission types, discharge dispositions, admission sources)
3. data/diabetic_data_clean.csv (Preprocessed cohort with first-encounter deduplication,
   hospice/mortality exclusion, ICD-9 clinical mapping, and binary readmitted_30 target)
"""

import os
import sys
import argparse
import numpy as np
import pandas as pd

def get_args():
    parser = argparse.ArgumentParser(description="Generate Diabetes 130-US Hospitals synthetic EHR dataset.")
    parser.add_argument("--samples", type=int, default=10000, help="Number of encounters to generate (default: 10000)")
    parser.add_argument("--full", action="store_true", help="Generate full 101,766 encounters with 71,518 unique patients")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    parser.add_argument("--output_dir", type=str, default=None, help="Output directory path")
    return parser.parse_args()


def generate_ids_mapping(output_dir: str):
    """Generate IDs_mapping.csv matching the UCI Diabetes 130-US Hospitals standard."""
    mapping_text = """admission_type_id,description
1,Emergency
2,Urgent
3,Elective
4,Newborn
5,Not Available
6,NULL
7,Trauma Center
8,Not Mapped

discharge_disposition_id,description
1,Discharged to home
2,Discharged/transferred to another short term general hospital
3,Discharged/transferred to SNF
4,Discharged/transferred to ICF
5,Discharged/transferred to another type of inpatient care institution
6,Discharged/transferred to home with home health service
7,Left against medical advice
8,Discharged/transferred to home under care of Home IV provider
9,Admitted as an inpatient to this hospital
10,Neonate to another facility for neonatal aftercare
11,Expired
12,Still patient or expected to return for outpatient services
13,Hospice / home
14,Hospice / medical facility
15,Discharged/transferred to Medicare cert long term care hospital
16,Discharged/transferred to another institution for outpatient services
17,Discharged/transferred to this institution for outpatient services
18,NULL
19,Expired at home. Medicaid only hospice.
20,Expired in a medical facility. Medicaid only hospice.
21,Expired, place unknown. Medicaid only hospice.
22,Discharged/transferred to another rehab facility
23,Discharged/transferred to a long term care hospital
24,Discharged/transferred to a nursing facility certified under Medicaid
25,Not Mapped
26,Unknown/Invalid

admission_source_id,description
1,Physician Referral
2,Clinic Referral
3,HMO Referral
4,Transfer from a hospital
5,Transfer from a Skilled Nursing Facility (SNF)
6,Transfer from another health care facility
7,Emergency Room
8,Court/Law Enforcement
9,Not Available
10,Transfer from critical access hospital
11,Normal Delivery
12,Premature Delivery
13,Sick Baby
14,Extramural Birth
15,Not Available
17,NULL
20,Not Mapped
"""
    mapping_path = os.path.join(output_dir, "IDs_mapping.csv")
    with open(mapping_path, "w", encoding="utf-8") as f:
        f.write(mapping_text)
    print(f"[OK] Created IDs_mapping.csv at {mapping_path}")


def map_icd9_to_category(code_str: str) -> str:
    """
    Map an ICD-9 diagnosis code string to one of the 9 clinical categories.
    Categories:
    - Diabetes: 250.xx
    - Circulatory: 390-459, 785
    - Respiratory: 460-519, 786
    - Digestive: 520-579, 787
    - Genitourinary: 580-629, 788
    - Musculoskeletal: 710-739
    - Injury: 800-999
    - Neoplasms: 140-239
    - Other: all others (including V and E codes, or codes not matching above)
    """
    if pd.isna(code_str) or code_str == "?" or code_str == "":
        return "Other"
    
    code = str(code_str).strip()
    if code.startswith("250"):
        return "Diabetes"
    
    # Check for V or E prefix
    if code.startswith("V") or code.startswith("E"):
        return "Other"
    
    # Extract leading 3 numeric digits before decimal point
    prefix = code.split(".")[0]
    try:
        val = int(prefix)
    except ValueError:
        return "Other"
    
    if (390 <= val <= 459) or val == 785:
        return "Circulatory"
    elif (460 <= val <= 519) or val == 786:
        return "Respiratory"
    elif (520 <= val <= 579) or val == 787:
        return "Digestive"
    elif (580 <= val <= 629) or val == 788:
        return "Genitourinary"
    elif 710 <= val <= 739:
        return "Musculoskeletal"
    elif 800 <= val <= 999:
        return "Injury"
    elif 140 <= val <= 239:
        return "Neoplasms"
    else:
        return "Other"


def generate_diabetic_data(num_records: int, seed: int = 42) -> pd.DataFrame:
    """Generate high-fidelity synthetic diabetic encounter dataset matching UCI specifications."""
    np.random.seed(seed)
    
    # Calculate patient multiplexing: 71,518 unique patients for full 101,766 encounters
    if num_records == 101766:
        target_unique_patients = 71518
    else:
        target_unique_patients = int(num_records * (71518 / 101766))
    patient_ids = np.arange(10000001, 10000001 + target_unique_patients)
    
    # Assign encounters to patients
    # 70% get 1 encounter, 20% get 2, 7% get 3, 2% get 4, 1% get 5+
    weights = [0.70, 0.20, 0.07, 0.02, 0.01]
    enc_counts = np.random.choice([1, 2, 3, 4, 5], size=target_unique_patients, p=weights)
    
    # Expand into patient-encounter pairs
    assigned_patients = []
    for pid, count in zip(patient_ids, enc_counts):
        assigned_patients.extend([pid] * count)
        if len(assigned_patients) >= num_records:
            break
            
    assigned_patients = assigned_patients[:num_records]
    actual_records = len(assigned_patients)
    
    encounter_ids = np.arange(100001, 100001 + actual_records)
    
    # Demographic assignments per unique patient to maintain consistency
    patient_demo = {}
    races = ['Caucasian', 'AfricanAmerican', 'Hispanic', 'Other', 'Asian', '?']
    race_probs = [0.74, 0.19, 0.02, 0.015, 0.007, 0.028]
    
    genders = ['Female', 'Male', 'Unknown/Invalid']
    gender_probs = [0.535, 0.464, 0.001]
    
    age_brackets = ['[0-10)', '[10-20)', '[20-30)', '[30-40)', '[40-50)', 
                    '[50-60)', '[60-70)', '[70-80)', '[80-90)', '[90-100)']
    age_probs = [0.002, 0.007, 0.016, 0.037, 0.095, 0.170, 0.222, 0.251, 0.173, 0.027]
    
    for pid in patient_ids:
        patient_demo[pid] = {
            'race': np.random.choice(races, p=race_probs),
            'gender': np.random.choice(genders, p=gender_probs),
            'age': np.random.choice(age_brackets, p=age_probs)
        }
        
    race_col = [patient_demo[pid]['race'] for pid in assigned_patients]
    gender_col = [patient_demo[pid]['gender'] for pid in assigned_patients]
    age_col = [patient_demo[pid]['age'] for pid in assigned_patients]
    
    # Weight column (>96% missing '?')
    weights_vals = ['?', '[0-25)', '[25-50)', '[50-75)', '[75-100)', '[100-125)', '[125-150)']
    weight_col = np.random.choice(weights_vals, size=actual_records, p=[0.968, 0.001, 0.003, 0.008, 0.012, 0.006, 0.002])
    
    # Admission types (1=Emergency: 53%, 2=Urgent: 18%, 3=Elective: 18%, others: 11%)
    adm_types = [1, 2, 3, 4, 5, 6, 7, 8]
    adm_probs = [0.53, 0.18, 0.18, 0.001, 0.046, 0.058, 0.001, 0.004]
    admission_type_id = np.random.choice(adm_types, size=actual_records, p=adm_probs)
    
    # Discharge disposition (1=Home: 60%, 3=SNF: 14%, 6=Home Health: 13%, 2=Short Term: 2%, 
    # Expired/Hospice [11, 13, 14, 19, 20, 21]: ~3.5%)
    disp_ids = [1, 2, 3, 4, 5, 6, 7, 8, 11, 13, 14, 18, 19, 20, 22, 25]
    disp_probs = [0.60, 0.02, 0.14, 0.01, 0.01, 0.13, 0.006, 0.001, 0.016, 0.004, 0.004, 0.035, 0.005, 0.001, 0.014, 0.004]
    discharge_disposition_id = np.random.choice(disp_ids, size=actual_records, p=disp_probs)
    
    # Admission source (7=ER: 56%, 1=Physician: 29%, 2=Clinic: 1%, 4/5/6=Transfer: 6%, others: 8%)
    source_ids = [1, 2, 3, 4, 5, 6, 7, 8, 17, 20]
    source_probs = [0.29, 0.01, 0.002, 0.03, 0.01, 0.02, 0.56, 0.001, 0.07, 0.007]
    admission_source_id = np.random.choice(source_ids, size=actual_records, p=source_probs)
    
    # Time in hospital (1 to 14 days, Gamma/Poisson distributed, mean ~4.4)
    time_in_hospital = np.clip(np.random.geometric(p=0.22, size=actual_records), 1, 14)
    
    # Payer code (~40% missing '?')
    payers = ['?', 'MC', 'MD', 'HM', 'UN', 'BC', 'SP', 'CP', 'OG', 'DM']
    payer_probs = [0.395, 0.315, 0.035, 0.062, 0.035, 0.046, 0.050, 0.025, 0.015, 0.022]
    payer_code = np.random.choice(payers, size=actual_records, p=payer_probs)
    
    # Medical specialty (~49% missing '?')
    specs = ['?', 'InternalMedicine', 'Cardiology', 'Surgery-General', 'Family/GeneralPractice', 
             'Emergency/Trauma', 'Orthopedics', 'Nephrology', 'Radiologist', 'Other']
    spec_probs = [0.49, 0.14, 0.05, 0.03, 0.07, 0.07, 0.01, 0.01, 0.01, 0.12]
    medical_specialty = np.random.choice(specs, size=actual_records, p=spec_probs)
    
    # Procedures and Labs
    num_lab_procedures = np.clip(np.random.normal(loc=43, scale=19, size=actual_records).astype(int), 1, 132)
    num_procedures = np.random.choice([0, 1, 2, 3, 4, 5, 6], size=actual_records, p=[0.46, 0.20, 0.13, 0.10, 0.05, 0.04, 0.02])
    num_medications = np.clip(np.random.normal(loc=16, scale=8, size=actual_records).astype(int), 1, 81)
    
    # Prior visits
    # Inpatient visits: right-skewed zero-inflated Poisson
    num_inpatient = np.random.choice([0, 1, 2, 3, 4, 5], size=actual_records, p=[0.67, 0.20, 0.07, 0.03, 0.02, 0.01])
    num_emergency = np.random.choice([0, 1, 2, 3, 4], size=actual_records, p=[0.88, 0.08, 0.02, 0.01, 0.01])
    num_outpatient = np.random.choice([0, 1, 2, 3, 4, 5], size=actual_records, p=[0.84, 0.09, 0.03, 0.02, 0.01, 0.01])
    
    # Diagnoses ICD-9 codes
    # Typical primary codes in 130-US dataset:
    # 250.xx (Diabetes), 414/428/410 (Circulatory), 486/491 (Respiratory), 574/560 (Digestive),
    # 599/585 (Genitourinary), 715/722 (Musculoskeletal), 820/808 (Injury), 162/174 (Neoplasms)
    icd9_samples = {
        'Diabetes': ['250.00', '250.02', '250.6', '250.8', '250.01'],
        'Circulatory': ['428', '414', '410', '427', '434', '785'],
        'Respiratory': ['486', '491', '493', '507', '786'],
        'Digestive': ['574', '560', '577', '530', '787'],
        'Genitourinary': ['599', '584', '585', '600', '788'],
        'Musculoskeletal': ['715', '722', '730'],
        'Injury': ['820', '821', '808', '996'],
        'Neoplasms': ['162', '174', '197', '202'],
        'Other': ['V58', 'V45', '707', '276', '272']
    }
    
    diag_cat_choices = ['Circulatory', 'Diabetes', 'Respiratory', 'Digestive', 
                        'Genitourinary', 'Musculoskeletal', 'Injury', 'Neoplasms', 'Other']
    diag_cat_probs = [0.30, 0.14, 0.14, 0.09, 0.05, 0.05, 0.07, 0.03, 0.13]
    
    diag_1 = []
    diag_2 = []
    diag_3 = []
    
    for _ in range(actual_records):
        c1 = np.random.choice(diag_cat_choices, p=diag_cat_probs)
        c2 = np.random.choice(diag_cat_choices, p=diag_cat_probs)
        c3 = np.random.choice(diag_cat_choices, p=diag_cat_probs)
        diag_1.append(np.random.choice(icd9_samples[c1]))
        diag_2.append(np.random.choice(icd9_samples[c2]))
        diag_3.append(np.random.choice(icd9_samples[c3]))
        
    number_diagnoses = np.clip(np.random.choice([3, 5, 7, 9, 12, 16], size=actual_records, p=[0.05, 0.15, 0.35, 0.35, 0.08, 0.02]), 1, 16)
    
    # Biomarkers: max_glu_serum and A1Cresult
    max_glu_serum = np.random.choice(['None', 'Norm', '>200', '>300'], size=actual_records, p=[0.947, 0.025, 0.015, 0.013])
    A1Cresult = np.random.choice(['None', 'Norm', '>7', '>8'], size=actual_records, p=[0.833, 0.049, 0.038, 0.080])
    
    # 23 Diabetes medications
    med_list = [
        'metformin', 'repaglinide', 'nateglinide', 'chlorpropamide', 'glimepiride',
        'acetohexamide', 'glipizide', 'glyburide', 'tolbutamide', 'pioglitazone',
        'rosiglitazone', 'acarbose', 'miglitol', 'troglitazone', 'tolazamide',
        'examide', 'citoglipton', 'insulin', 'glyburide-metformin', 'glipizide-metformin',
        'glimepiride-pioglitazone', 'metformin-rosiglitazone', 'metformin-pioglitazone'
    ]
    
    med_cols = {}
    for med in med_list:
        if med in ['examide', 'citoglipton']:
            med_cols[med] = ['No'] * actual_records
        elif med == 'insulin':
            med_cols[med] = np.random.choice(['No', 'Steady', 'Up', 'Down'], size=actual_records, p=[0.47, 0.30, 0.12, 0.11])
        elif med == 'metformin':
            med_cols[med] = np.random.choice(['No', 'Steady', 'Up', 'Down'], size=actual_records, p=[0.80, 0.18, 0.01, 0.01])
        elif med in ['glipizide', 'glyburide']:
            med_cols[med] = np.random.choice(['No', 'Steady', 'Up', 'Down'], size=actual_records, p=[0.87, 0.11, 0.01, 0.01])
        elif med in ['pioglitazone', 'rosiglitazone']:
            med_cols[med] = np.random.choice(['No', 'Steady', 'Up', 'Down'], size=actual_records, p=[0.93, 0.06, 0.005, 0.005])
        else:
            med_cols[med] = np.random.choice(['No', 'Steady', 'Up', 'Down'], size=actual_records, p=[0.99, 0.008, 0.001, 0.001])
            
    # Medication change flag
    change = np.random.choice(['Ch', 'No'], size=actual_records, p=[0.46, 0.54])
    
    # Diabetes med prescribed
    diabetesMed = np.random.choice(['Yes', 'No'], size=actual_records, p=[0.77, 0.23])
    
    # Target variable generation with correlated clinical logic:
    # Base 30-day readmit log-odds ~ -2.4 (yielding ~8-9%)
    # Risk multipliers:
    # - number_inpatient >= 2: +1.2 log-odds
    # - discharge_disposition_id in (3, 6) [SNF, Home Health]: +0.5 log-odds
    # - time_in_hospital >= 7: +0.4 log-odds
    # - insulin in ('Up', 'Down') + A1Cresult == '>8': +0.8 log-odds
    # - age >= 70: +0.3 log-odds
    # - death/hospice in [11, 13, 14, 19, 20, 21]: physically 0 readmission probability
    
    log_odds = np.full(actual_records, -2.5)
    
    for i in range(actual_records):
        if discharge_disposition_id[i] in [11, 13, 14, 19, 20, 21]:
            log_odds[i] = -99.0  # Cannot readmit if deceased/hospice
            continue
            
        if num_inpatient[i] >= 2:
            log_odds[i] += 1.35
        elif num_inpatient[i] == 1:
            log_odds[i] += 0.50
            
        if discharge_disposition_id[i] in [3, 6]:
            log_odds[i] += 0.45
            
        if time_in_hospital[i] >= 7:
            log_odds[i] += 0.35
            
        if med_cols['insulin'][i] in ['Up', 'Down'] and A1Cresult[i] == '>8':
            log_odds[i] += 0.75
            
        if age_col[i] in ['[70-80)', '[80-90)', '[90-100)']:
            log_odds[i] += 0.30
            
        if num_medications[i] >= 20:
            log_odds[i] += 0.25
            
        if diag_1[i].startswith('428') or diag_1[i].startswith('250'):
            log_odds[i] += 0.30

    probs_30 = 1.0 / (1.0 + np.exp(-log_odds))
    probs_30 = np.clip(probs_30, 0.0, 0.95)
    
    readmitted = []
    for i in range(actual_records):
        if discharge_disposition_id[i] in [11, 13, 14, 19, 20, 21]:
            readmitted.append('NO')
        else:
            p30 = probs_30[i]
            # Overall: ~11.16% '<30', ~34.93% '>30', ~53.91% 'NO'
            roll = np.random.uniform(0, 1)
            if roll < p30:
                readmitted.append('<30')
            elif roll < p30 + 0.38:
                readmitted.append('>30')
            else:
                readmitted.append('NO')
                
    df = pd.DataFrame({
        'encounter_id': encounter_ids,
        'patient_nbr': assigned_patients,
        'race': race_col,
        'gender': gender_col,
        'age': age_col,
        'weight': weight_col,
        'admission_type_id': admission_type_id,
        'discharge_disposition_id': discharge_disposition_id,
        'admission_source_id': admission_source_id,
        'time_in_hospital': time_in_hospital,
        'payer_code': payer_code,
        'medical_specialty': medical_specialty,
        'num_lab_procedures': num_lab_procedures,
        'num_procedures': num_procedures,
        'num_medications': num_medications,
        'number_outpatient': num_outpatient,
        'number_emergency': num_emergency,
        'number_inpatient': num_inpatient,
        'diag_1': diag_1,
        'diag_2': diag_2,
        'diag_3': diag_3,
        'number_diagnoses': number_diagnoses,
        'max_glu_serum': max_glu_serum,
        'A1Cresult': A1Cresult,
        **med_cols,
        'change': change,
        'diabetesMed': diabetesMed,
        'readmitted': readmitted
    })
    
    return df


def clean_and_prepare_cohort(df_raw: pd.DataFrame) -> pd.DataFrame:
    """
    Apply clinical data cleaning and cohort filtering:
    1. Replace '?' with NaN
    2. Drop 'weight' column (>96% missing)
    3. Filter out invalid genders
    4. Exclude deceased and hospice encounters (discharge IDs 11, 13, 14, 19, 20, 21)
    5. Deduplicate to keep ONLY the first encounter per patient_nbr (leakage elimination)
    6. Map ICD-9 codes to 9 clinical categories
    7. Define binary readmitted_30 target (1 for '<30', 0 for '>30' or 'NO')
    8. Engineer clinical ratio and comorbidity features
    """
    df = df_raw.copy()
    
    # 1. Replace '?' with NaN
    df = df.replace('?', np.nan)
    
    # 2. Drop weight
    if 'weight' in df.columns:
        df = df.drop(columns=['weight'])
        
    # 3. Filter invalid genders
    df = df[df['gender'].isin(['Female', 'Male'])]
    
    # 4. Exclude deceased / hospice patients
    hospice_deceased_ids = [11, 13, 14, 19, 20, 21]
    df = df[~df['discharge_disposition_id'].isin(hospice_deceased_ids)]
    
    # 5. Deduplicate to strictly first encounter per patient
    df = df.sort_values(by='encounter_id', ascending=True)
    df = df.groupby('patient_nbr', as_index=False).first()
    
    # 6. Map ICD-9 codes to clinical categories
    df['primary_diag_category'] = df['diag_1'].apply(map_icd9_to_category)
    df['diag_2_category'] = df['diag_2'].apply(map_icd9_to_category)
    df['diag_3_category'] = df['diag_3'].apply(map_icd9_to_category)
    
    # 7. Binary readmitted_30 target
    df['readmitted_30'] = (df['readmitted'] == '<30').astype(int)
    df['readmitted_any'] = (df['readmitted'].isin(['<30', '>30'])).astype(int)
    
    # 8. Clinical feature engineering
    df['total_prior_visits'] = df['number_inpatient'] + df['number_emergency'] + df['number_outpatient']
    df['inpatient_visit_ratio'] = df['number_inpatient'] / (df['total_prior_visits'] + 1.0)
    df['medication_intensity'] = df['num_medications'] / df['time_in_hospital'].clip(lower=1)
    df['lab_intensity'] = df['num_lab_procedures'] / df['time_in_hospital'].clip(lower=1)
    df['high_comorbidity_flag'] = (df['number_diagnoses'] >= 9).astype(int)
    df['insulin_treatment_flag'] = df['insulin'].isin(['Steady', 'Up', 'Down']).astype(int)
    
    return df


def main():
    args = get_args()
    
    # Resolve output directory
    if args.output_dir:
        output_dir = args.output_dir
    else:
        # Default to 03_Healthcare_Diabetes/data/
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_dir = script_dir
        
    os.makedirs(output_dir, exist_ok=True)
    
    num_samples = 101766 if args.full else args.samples
    print(f"Generating {num_samples} diabetic encounters (seed={args.seed})...")
    
    # 1. Generate IDs_mapping.csv
    generate_ids_mapping(output_dir)
    
    # 2. Generate raw diabetic_data.csv
    df_raw = generate_diabetic_data(num_samples, seed=args.seed)
    raw_path = os.path.join(output_dir, "diabetic_data.csv")
    df_raw.to_csv(raw_path, index=False)
    print(f"[OK] Saved raw diabetic_data.csv ({len(df_raw):,} encounters, {df_raw['patient_nbr'].nunique():,} unique patients) to {raw_path}")
    
    # 3. Clean and prepare deduplicated clinical cohort
    df_clean = clean_and_prepare_cohort(df_raw)
    clean_path = os.path.join(output_dir, "diabetic_data_clean.csv")
    df_clean.to_csv(clean_path, index=False)
    
    readmit_30_rate = df_clean['readmitted_30'].mean() * 100
    print(f"[OK] Saved clean cohort diabetic_data_clean.csv ({len(df_clean):,} unique patients, 30-Day Readmission Rate: {readmit_30_rate:.2f}%) to {clean_path}")
    print("[SUCCESS] Data generation and clinical ETL complete with exit code 0.")


if __name__ == "__main__":
    main()
