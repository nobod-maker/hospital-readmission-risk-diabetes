-- ============================================================================
-- Clinical KPI & Analytical Transformation Queries
-- Project: 03_Healthcare_Diabetes
-- Dialect: SQLite / DuckDB
-- ============================================================================

-- ----------------------------------------------------------------------------
-- KPI 1: 30-Day Readmission Rate and Average Length of Stay by Age Band
-- Business Goal: Identify vulnerable age cohorts with elevated acute recidivism.
-- ----------------------------------------------------------------------------
SELECT 
    p.age_bracket,
    COUNT(f.encounter_key) AS total_patients,
    SUM(f.is_readmitted_30) AS readmitted_30_count,
    ROUND(100.0 * SUM(f.is_readmitted_30) / NULLIF(COUNT(f.encounter_key), 0), 2) AS readmit_30_rate_pct,
    ROUND(AVG(f.time_in_hospital), 2) AS avg_stay_days,
    ROUND(AVG(f.num_medications), 2) AS avg_medications
FROM Fact_Encounters f
JOIN Dim_Patient p ON f.patient_key = p.patient_key
GROUP BY p.age_bracket
ORDER BY p.age_bracket;

-- ----------------------------------------------------------------------------
-- KPI 2: Readmission Rate by Prior Inpatient Admissions Velocity
-- Clinical Goal: Evaluate acute recidivism as a function of previous 12-month hospitalizations.
-- ----------------------------------------------------------------------------
SELECT 
    CASE 
        WHEN f.number_inpatient = 0 THEN '0 Inpatient Visits'
        WHEN f.number_inpatient = 1 THEN '1 Inpatient Visit'
        WHEN f.number_inpatient = 2 THEN '2 Inpatient Visits'
        ELSE '3+ Inpatient Visits'
    END AS prior_inpatient_tier,
    COUNT(f.encounter_key) AS total_encounters,
    SUM(f.is_readmitted_30) AS readmitted_30_count,
    ROUND(100.0 * SUM(f.is_readmitted_30) / NULLIF(COUNT(f.encounter_key), 0), 2) AS readmit_30_rate_pct,
    ROUND(AVG(f.total_prior_visits), 2) AS avg_total_prior_visits
FROM Fact_Encounters f
GROUP BY 1
ORDER BY 1;

-- ----------------------------------------------------------------------------
-- KPI 3: Medication Regimen Adjustment & HbA1c Biomarker Impact
-- Clinical Goal: Assess how active insulin titration during admission and poorly
-- controlled hyperglycemia (>8% A1C) interact to influence 30-day readmissions.
-- ----------------------------------------------------------------------------
SELECT 
    m.medication_change AS med_change_flag,
    m.insulin_status,
    f.a1c_result,
    COUNT(f.encounter_key) AS encounter_count,
    SUM(f.is_readmitted_30) AS readmitted_30_count,
    ROUND(100.0 * SUM(f.is_readmitted_30) / NULLIF(COUNT(f.encounter_key), 0), 2) AS readmit_30_rate_pct
FROM Fact_Encounters f
JOIN Dim_Medication_Regimen m ON f.med_regimen_key = m.med_regimen_key
GROUP BY m.medication_change, m.insulin_status, f.a1c_result
HAVING COUNT(f.encounter_key) >= 10
ORDER BY readmit_30_rate_pct DESC;

-- ----------------------------------------------------------------------------
-- KPI 4: Top Clinical Diagnosis Categories Ranked by Readmission Volume
-- Analytical Method: Window function DENSE_RANK() ordering clinical categories.
-- ----------------------------------------------------------------------------
SELECT 
    d.clinical_category,
    COUNT(f.encounter_key) AS total_encounters,
    SUM(f.is_readmitted_30) AS readmitted_30_count,
    ROUND(100.0 * SUM(f.is_readmitted_30) / NULLIF(COUNT(f.encounter_key), 0), 2) AS readmit_30_rate_pct,
    ROUND(100.0 * SUM(f.is_readmitted_30) / (SELECT NULLIF(SUM(is_readmitted_30), 0) FROM Fact_Encounters), 2) AS pct_of_total_readmissions,
    DENSE_RANK() OVER (ORDER BY SUM(f.is_readmitted_30) DESC) AS readmit_volume_rank
FROM Fact_Encounters f
JOIN Dim_Diagnosis d ON f.primary_diag_key = d.diagnosis_key
GROUP BY d.clinical_category
ORDER BY readmit_volume_rank;

-- ----------------------------------------------------------------------------
-- KPI 5: Readmission Rate by Discharge Disposition
-- Clinical Goal: Compare transition outcomes (Home vs Skilled Nursing Facility vs Home Health).
-- ----------------------------------------------------------------------------
SELECT 
    dd.discharge_disp_name,
    COUNT(f.encounter_key) AS encounter_count,
    SUM(f.is_readmitted_30) AS readmitted_30_count,
    ROUND(100.0 * SUM(f.is_readmitted_30) / NULLIF(COUNT(f.encounter_key), 0), 2) AS readmit_30_rate_pct,
    ROUND(AVG(f.time_in_hospital), 2) AS avg_los_days
FROM Fact_Encounters f
JOIN Dim_Discharge_Disposition dd ON f.discharge_disp_key = dd.discharge_disp_key
GROUP BY dd.discharge_disp_name
HAVING COUNT(f.encounter_key) >= 20
ORDER BY readmit_30_rate_pct DESC;

-- ----------------------------------------------------------------------------
-- KPI 6: Risk Tier Stratification and Readmission Capture Rate
-- Operational Goal: Validate that machine learning risk tiering effectively concentrates
-- true 30-day readmissions into the High and Medium risk segments.
-- ----------------------------------------------------------------------------
SELECT 
    rt.risk_tier_name,
    COUNT(f.encounter_key) AS cohort_size,
    ROUND(100.0 * COUNT(f.encounter_key) / (SELECT NULLIF(COUNT(*), 0) FROM Fact_Encounters), 2) AS pct_of_population,
    SUM(f.is_readmitted_30) AS actual_readmissions,
    ROUND(100.0 * SUM(f.is_readmitted_30) / NULLIF(COUNT(f.encounter_key), 0), 2) AS cohort_readmit_rate_pct,
    ROUND(100.0 * SUM(f.is_readmitted_30) / (SELECT NULLIF(SUM(is_readmitted_30), 0) FROM Fact_Encounters), 2) AS readmission_capture_pct
FROM Fact_Encounters f
JOIN Dim_Risk_Tier rt ON f.risk_tier_key = rt.risk_tier_key
GROUP BY rt.risk_tier_key, rt.risk_tier_name
ORDER BY rt.risk_tier_key DESC;
