-- ============================================================================
-- Star-Schema Relational DDL for Hospital Readmission Risk Analysis
-- Project: 03_Healthcare_Diabetes
-- Dialect: SQLite / DuckDB
-- ============================================================================

PRAGMA foreign_keys = ON;

-- ----------------------------------------------------------------------------
-- 1. Dimension: Patient Demographics (Dim_Patient)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS Dim_Patient (
    patient_key INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_nbr INTEGER NOT NULL UNIQUE,
    race TEXT DEFAULT 'Unknown',
    gender TEXT NOT NULL,
    age_bracket TEXT NOT NULL,
    age_midpoint INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_dim_patient_nbr ON Dim_Patient(patient_nbr);

-- ----------------------------------------------------------------------------
-- 2. Dimension: Admission Type (Dim_Admission_Type)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS Dim_Admission_Type (
    admission_type_key INTEGER PRIMARY KEY,
    admission_type_id INTEGER NOT NULL UNIQUE,
    admission_type_name TEXT NOT NULL
);

-- ----------------------------------------------------------------------------
-- 3. Dimension: Discharge Disposition (Dim_Discharge_Disposition)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS Dim_Discharge_Disposition (
    discharge_disp_key INTEGER PRIMARY KEY,
    discharge_disp_id INTEGER NOT NULL UNIQUE,
    discharge_disp_name TEXT NOT NULL,
    is_hospice_deceased INTEGER DEFAULT 0
);

-- ----------------------------------------------------------------------------
-- 4. Dimension: Admission Source (Dim_Admission_Source)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS Dim_Admission_Source (
    admission_source_key INTEGER PRIMARY KEY,
    admission_source_id INTEGER NOT NULL UNIQUE,
    admission_source_name TEXT NOT NULL
);

-- ----------------------------------------------------------------------------
-- 5. Dimension: Diagnosis & Clinical Category (Dim_Diagnosis)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS Dim_Diagnosis (
    diagnosis_key INTEGER PRIMARY KEY AUTOINCREMENT,
    icd9_code TEXT NOT NULL UNIQUE,
    clinical_category TEXT NOT NULL,
    category_description TEXT
);

CREATE INDEX IF NOT EXISTS idx_dim_diag_cat ON Dim_Diagnosis(clinical_category);

-- ----------------------------------------------------------------------------
-- 6. Dimension: Medication Regimen (Dim_Medication_Regimen)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS Dim_Medication_Regimen (
    med_regimen_key INTEGER PRIMARY KEY AUTOINCREMENT,
    medication_change TEXT NOT NULL,
    diabetes_med_prescribed TEXT NOT NULL,
    insulin_status TEXT NOT NULL,
    metformin_status TEXT NOT NULL,
    active_med_count INTEGER NOT NULL,
    UNIQUE(medication_change, diabetes_med_prescribed, insulin_status, metformin_status, active_med_count)
);

-- ----------------------------------------------------------------------------
-- 7. Dimension: Clinical Risk Tier (Dim_Risk_Tier)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS Dim_Risk_Tier (
    risk_tier_key INTEGER PRIMARY KEY,
    risk_tier_name TEXT NOT NULL UNIQUE,
    min_risk_score REAL NOT NULL,
    max_risk_score REAL NOT NULL,
    recommended_action TEXT NOT NULL
);

-- ----------------------------------------------------------------------------
-- 8. Central Fact: Inpatient Encounters (Fact_Encounters)
-- Grain: One record per eligible first hospital encounter
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS Fact_Encounters (
    encounter_key INTEGER PRIMARY KEY AUTOINCREMENT,
    encounter_id INTEGER NOT NULL UNIQUE,
    patient_key INTEGER NOT NULL,
    admission_type_key INTEGER NOT NULL,
    discharge_disp_key INTEGER NOT NULL,
    admission_source_key INTEGER NOT NULL,
    primary_diag_key INTEGER NOT NULL,
    med_regimen_key INTEGER NOT NULL,
    risk_tier_key INTEGER NOT NULL,
    time_in_hospital INTEGER NOT NULL,
    num_lab_procedures INTEGER NOT NULL,
    num_procedures INTEGER NOT NULL,
    num_medications INTEGER NOT NULL,
    number_outpatient INTEGER NOT NULL,
    number_emergency INTEGER NOT NULL,
    number_inpatient INTEGER NOT NULL,
    total_prior_visits INTEGER NOT NULL,
    number_diagnoses INTEGER NOT NULL,
    max_glu_serum TEXT DEFAULT 'None',
    a1c_result TEXT DEFAULT 'None',
    model_risk_score REAL DEFAULT 0.0,
    is_readmitted_30 INTEGER NOT NULL,
    is_readmitted_any INTEGER NOT NULL,
    FOREIGN KEY (patient_key) REFERENCES Dim_Patient(patient_key),
    FOREIGN KEY (admission_type_key) REFERENCES Dim_Admission_Type(admission_type_key),
    FOREIGN KEY (discharge_disp_key) REFERENCES Dim_Discharge_Disposition(discharge_disp_key),
    FOREIGN KEY (admission_source_key) REFERENCES Dim_Admission_Source(admission_source_key),
    FOREIGN KEY (primary_diag_key) REFERENCES Dim_Diagnosis(diagnosis_key),
    FOREIGN KEY (med_regimen_key) REFERENCES Dim_Medication_Regimen(med_regimen_key),
    FOREIGN KEY (risk_tier_key) REFERENCES Dim_Risk_Tier(risk_tier_key)
);

CREATE INDEX IF NOT EXISTS idx_fact_enc_patient ON Fact_Encounters(patient_key);
CREATE INDEX IF NOT EXISTS idx_fact_enc_risk ON Fact_Encounters(risk_tier_key, is_readmitted_30);
CREATE INDEX IF NOT EXISTS idx_fact_enc_diag ON Fact_Encounters(primary_diag_key);
CREATE INDEX IF NOT EXISTS idx_fact_enc_readmit ON Fact_Encounters(is_readmitted_30);
