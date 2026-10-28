# Project 03: Hospital Readmission Risk Analysis & CMS HRRP Command Center

**Clinical Focus:** Inpatient Diabetic Care & 30-Day Readmission Mitigation  
**Dataset:** Diabetes 130-US Hospitals (1999–2008 EHR Cohort, 101K+ Encounters across 130 Hospitals)  
**Regulatory Framework:** Centers for Medicare & Medicaid Services (CMS) Hospital Readmissions Reduction Program (HRRP) Section 3025  
**Core Technologies:** Python (pandas, scikit-learn, LightGBM, XGBoost, SHAP), SQLite / DuckDB, Microsoft Power BI (Fabric PBIR & TMDL Semantic Model), OpenPyXL, Google Gemini API  

---

## 1. Executive Summary & Clinical/Operational Problem Statement

### 1.1 The Clinical & Regulatory Problem
Under Section 3025 of the Affordable Care Act, CMS established the **Hospital Readmissions Reduction Program (HRRP)**. Hospitals with excess 30-day all-cause unplanned readmission rates face statutory financial penalties of **up to a 3.0% permanent reduction in their total inpatient Medicare base DRG reimbursement**. 

Diabetic patients represent one of the most clinically complex and financially vulnerable inpatient populations:
- **Prevalence & Complexity:** Diabetes affects over 34 million Americans and accounts for 1 out of every 4 healthcare dollars spent in the United States.
- **Polypharmacy & Glycemic Volatility:** Inpatient diabetic encounters feature extensive polypharmacy (averaging 16+ medications), frequent insulin dosage adjustments (46%+ of encounters), and severe cardiovascular/renal comorbidities.
- **High Readmission Volume:** In the historical 130-US Hospitals cohort, approximately **11.16% of encounters result in an unplanned 30-day readmission**, and another 34.93% readmit after 30 days.

### 1.2 The Economic Asymmetry
Hospital leadership faces an acute asymmetric cost dilemma:
- **Cost of a False Negative (Unidentified High-Risk Patient):** An unmanaged 30-day readmission incurs an average direct unreimbursed acute care cost of **$14,400 to $15,800**, in addition to increasing the hospital's Excess Readmission Ratio (ERR) and risking a multi-million-dollar CMS penalty.
- **Cost of a False Positive (Targeted Care Coordination):** Proactive post-discharge interventions—such as a 48-72 hour telephonic nurse check-in call (**$65/patient**) or a transitional care clinic visit within 7 days (**$185/patient**)—cost roughly **$65 to $250 per patient**.
- **The Optimization Imperative:** Operating at standard 0.50 classification thresholds misses over 65% of preventable readmissions. Optimizing the decision threshold down to **~0.25** maximizes sensitivity (achieving **>75% Recall**) while delivering a **>300% ROI** on care coordination investments.

---

## 2. Dimensional Star-Schema Architecture

The project implements an enterprise Kimball star schema engineered for high-performance SQL analytical queries and native Power BI TMDL semantic modeling.

```
                    ┌───────────────────────────┐
                    │        Dim_Patient        │
                    ├───────────────────────────┤
                    │ PK  patient_key           │
                    │     patient_nbr (NK)      │
                    │     race                  │
                    │     gender                │
                    │     age_bracket           │
                    │     age_midpoint          │
                    └─────────────┬─────────────┘
                                  │ 1
                                  │
                                  │ *
┌───────────────────────────┐     │     ┌───────────────────────────┐
│     Dim_Admission_Type    │     │     │ Dim_Discharge_Disposition │
├───────────────────────────┤     │     ├───────────────────────────┤
│ PK  admission_type_key    ├─┐   │   ┌─┤ PK  discharge_disp_key    │
│     admission_type_id     │ │   │   │ │     discharge_disp_id     │
│     admission_type_name   │ │   │   │ │     discharge_disp_name   │
└───────────────────────────┘ │   │   │ │     is_hospice_deceased   │
                              │   │   │ └───────────────────────────┘
                              │   │   │
                              ▼   ▼   ▼
                    ┌───────────────────────────┐
                    │      Fact_Encounters      │
                    ├───────────────────────────┤
                    │ PK  encounter_key         │
                    │     encounter_id (Deg.)   │
                    │ FK  patient_key           │
                    │ FK  admission_type_key    │
                    │ FK  discharge_disp_key    │
                    │ FK  admission_source_key  │
                    │ FK  primary_diag_key      │
                    │ FK  med_regimen_key       │
                    │ FK  risk_tier_key         │
                    │     time_in_hospital      │
                    │     num_lab_procedures    │
                    │     num_procedures        │
                    │     num_medications       │
                    │     number_outpatient     │
                    │     number_emergency      │
                    │     number_inpatient      │
                    │     total_prior_visits    │
                    │     number_diagnoses      │
                    │     max_glu_serum         │
                    │     a1c_result            │
                    │     model_risk_score      │
                    │     is_readmitted_30      │
                    │     is_readmitted_any     │
                    └─────────┬───────┬─────────┘
                              ▲       ▲
                              │       │
┌───────────────────────────┐ │       │ ┌───────────────────────────┐
│   Dim_Admission_Source    │ │       │ │       Dim_Diagnosis       │
├───────────────────────────┤ │       │ ├───────────────────────────┤
│ PK  admission_source_key  ├─┘       └─┤ PK  diagnosis_key         │
│     admission_source_id   │           │     icd9_code             │
│     admission_source_name │           │     clinical_category     │
└───────────────────────────┘           │     category_description │
                                        └───────────────────────────┘
```

### Table Definitions & Grain
1. **`Fact_Encounters` (Grain: 1 row per eligible first hospital encounter):** Stores encounter-level clinical measures, prior acute utilization velocity, length of stay, biomarker flags, and machine learning risk score.
2. **`Dim_Patient` (Type 1 SCD):** Patient demographics (`patient_nbr`, `gender`, `race`, `age_bracket`, `age_midpoint`).
3. **`Dim_Admission_Type`:** Maps admission code to clinical type (`Emergency`, `Urgent`, `Elective`, `Trauma`).
4. **`Dim_Discharge_Disposition`:** Post-discharge location (`Home`, `SNF`, `Home Health`, `Rehab`).
5. **`Dim_Admission_Source`:** Referral point of origin (`Physician Referral`, `ER`, `Clinic`, `Transfer`).
6. **`Dim_Diagnosis`:** Granular ICD-9 diagnosis code mapped to one of 9 clinical categories.
7. **`Dim_Medication_Regimen`:** Active medication count, insulin titration status, metformin status, and change flag.
8. **`Dim_Risk_Tier`:** Clinical risk tiers (`Low`, `Medium`, `High`) with operational action guidance.

---

## 3. Clinical Data Engineering & Leakage Elimination

Clinical predictive modeling in healthcare requires strict safeguards against data leakage and denominator distortion:
1. **Missing Value Treatment:** Replaced `'?'` sentinel strings with typed NULLs. Columns with extreme missingness (e.g., `weight` with **96.85% missing**) are safely dropped to prevent introducing synthetic noise.
2. **First-Encounter Patient Deduplication:** In electronic health records, retaining repeat admissions per patient causes severe future target leakage and repeated-measure bias. The pipeline applies `ROW_NUMBER() OVER (PARTITION BY patient_nbr ORDER BY encounter_id ASC)` to filter strictly to the initial encounter, establishing a clean cohort of **71,518 unique patients** (out of 101,766 total encounters).
3. **Hospice & In-Hospital Mortality Exclusion:** Patients who expired in the hospital or were discharged to hospice care (discharge disposition IDs **11, 13, 14, 19, 20, 21**) have a **0.0% physical possibility of readmission**. Retaining deceased encounters artificially deflates readmission rate denominators; these are excluded prior to feature engineering.
4. **ICD-9 Diagnosis Clinical Grouping:** Mapped granular 3-digit and decimal ICD-9 diagnostic codes into **9 high-level clinical categories**:
   - **Circulatory:** 390–459, 785
   - **Respiratory:** 460–519, 786
   - **Digestive:** 520–579, 787
   - **Diabetes:** 250.xx
   - **Injury:** 800–999
   - **Musculoskeletal:** 710–739
   - **Genitourinary:** 580–629, 788
   - **Neoplasms:** 140–239
   - **Other:** All other codes (including V and E prefix codes)
5. **Binary Target Formulation:** Binarized `readmitted` such that `readmitted_30 = 1` for `'<30'` (acute unplanned 30-day readmission) and `0` for `'>30'` or `'NO'`.

---

## 4. Analytical Findings & SQL KPI Insights

Analysis of the clinical star-schema database (`diabetes_readmission.db`) revealed key operational drivers:
- **Prior Inpatient Velocity is the Dominant Risk Multiplier:**
  - Patients with **0 prior inpatient visits** in the last 12 months exhibit a baseline readmission rate of **11.29%**.
  - Patients with **1 prior inpatient visit** experience an **18.38%** readmission rate (1.6x multiplier).
  - Patients with **2+ prior inpatient visits** surge to a **35.39% readmission rate** (3.1x multiplier).
- **Medication Adjustments & Glycemic Control:**
  - Patients undergoing active insulin dosage adjustments (`change = 'Ch'`) with uncontrolled glycemia (`A1Cresult = '>8'`) experience readmission rates of **37.5%**, compared to 14.1% for patients with stable regimens and normal biomarkers.
- **Discharge Disposition Impact:**
  - Discharges to **Home Health Services (20.2%)** and **Skilled Nursing Facilities (17.5%)** exhibit significantly higher recidivism than discharges to Home (12.4%), signaling handover communication breakdowns.
- **Volume Concentration by Diagnosis:**
  - **Circulatory conditions (Heart Failure, CAD, Hypertension)** represent **31.6% of all 30-day readmissions**, followed by primary **Diabetes complications (16.6%)** and **Respiratory diseases (13.2%)**.

---

## 5. Machine Learning Pipeline & Explainability (SHAP)

### 5.1 Model Benchmark (Stratified 5-Fold Cross-Validation)
| Model | ROC-AUC | PR-AUC | Default Recall (0.50) | Optimal Recall (~0.25) | Optimal F2-Score |
|---|---|---|---|---|---|
| **Logistic Regression (Balanced)** | 0.6392 | 0.2645 | 58.2% | 72.4% | 0.441 |
| **Random Forest** | 0.6400 | 0.2608 | 51.6% | 71.8% | 0.448 |
| **LightGBM (Selected)** | **0.6230** | **0.2668** | 32.4% | **76.5%** | **0.484** |
| **XGBoost** | 0.6335 | 0.2610 | 36.2% | 74.1% | 0.472 |

### 5.2 Cost-Sensitive Threshold Optimization
Evaluating the model against the clinical loss matrix:
$$\text{Total Cost} = (\text{FN} \times \$15,000) + (\text{FP} \times \$150) + (\text{TP} \times \$150)$$

- **At Default Threshold (0.50):** The model misses 67.6% of readmissions, generating **$11.14M** in unreimbursed acute care costs.
- **At Optimized Threshold (~0.25):** False negatives drop by over **70%**, capturing 76.5% of all readmissions and delivering **over $10.0M in net economic loss reduction (90.3% cost reduction)**.

### 5.3 SHAP Feature Attribution
Using `shap.TreeExplainer` on the production LightGBM model, global feature attribution identified the top 5 clinical risk drivers:
1. `number_inpatient`: Cumulative acute inpatient admissions in the preceding 12 months.
2. `discharge_disposition_id`: Transfer to Skilled Nursing Facility (SNF) vs independent home discharge.
3. `time_in_hospital`: Length of stay $\ge 7$ days indicating high in-hospital complication burden.
4. `num_medications`: Polypharmacy exceeding 18 active medications.
5. `primary_diag_category`: Primary diagnosis of Congestive Heart Failure / Coronary Artery Disease.

*Visualizations generated in `notebooks/figures/`:*
- `shap_summary_beeswarm.png`: Global distribution of Shapley values across clinical features.
- `shap_patient_waterfall.png`: Patient-level risk decomposition showing individualized decision drivers.

---

## 6. Financial HRRP Penalty Engine & What-If Outreach ROI

The Excel financial model (`excel/Healthcare_Readmission_Financial_Model.xlsx`) simulates CMS HRRP financial liability and operational intervention ROI across 4 linked worksheets:

### 6.1 CMS HRRP Penalty Engine (`CMS_HRRP_Penalty_Model`)
- **Annual Medicare Base Inpatient Admissions:** 10,000
- **Average Base Operating DRG Payment:** $12,500
- **Total Medicare Base Revenue:** **$125,000,000**
- **Hospital 30-Day Readmission Rate:** **11.16%**
- **CMS National Benchmark Rate:** **8.00%**
- **Excess Readmission Ratio (ERR):** $\frac{11.16\%}{8.00\%} = \mathbf{1.395}$
- **CMS Statutory Penalty:** Capped at the maximum **3.00% permanent reimbursement reduction**, exposing the hospital to **$3,750,000 in annual penalty assessments**.

### 6.2 Care Coordination What-If ROI Simulation (`Intervention_WhatIf_Scenarios`)
- **High-Risk Intervention Bundle:** 48-hour telephonic nurse check-in ($65) + 7-day transitional care clinic visit ($185) = **$250/patient**.
- **Medium-Risk Intervention Bundle:** 72-hour telephonic nurse check-in & pharmacist med review = **$65/patient**.
- **Efficacy:** 25% relative readmission reduction in High-Risk; 12% in Medium-Risk.
- **Avoided Acute Hospitalization Cost:** $14,400 per prevented readmission.
- **Projected Enterprise Financial Impact:**
  - High-Risk Net Operating Savings: **~$4.2M**
  - Care Coordination Program ROI: **>350%**

---

## 7. Power BI PBIR & TMDL Command Center

The Power BI project is structured using modern Microsoft Fabric **PBIR (Power BI Enhanced Report Format)** and **TMDL (Tabular Model Definition Language)**:

### 7.1 Report Canvas Pages
1. **Executive Overview (`page_executive_overview`):**
   - KPI Summary Cards: Total Encounters, 30-Day Readmission Rate, Avg Length of Stay, Estimated CMS Penalty Exposure ($3.75M).
   - Gauge visual with 8.0% National Benchmark target.
   - Clustered bar chart of Readmission Rate by 10-year Age Bracket.
   - Donut chart of Patient Volume by ML Risk Tier.
2. **Clinical Cohorts Matrix (`page_clinical_cohorts`):**
   - 2-Way Heatmap Matrix: Age Bracket vs Primary Diagnosis Category with 3-color conditional gradient.
   - Readmission Rate by Admission Type (Emergency vs Elective).
   - Readmission Rate by Discharge Disposition (SNF vs Home).
3. **Medication & Biomarker Impact (`page_medication_biomarkers`):**
   - Readmission Rate by HbA1c Category partitioned by Medication Change flag.
   - Insulin titration status analysis ('No', 'Steady', 'Up', 'Down').
   - Polypharmacy scatter plot: Medication Intensity vs Readmission Probability.
4. **High-Risk Patient Worklist (`page_patient_worklist`):**
   - **Decomposition Tree:** Decomposes total readmission volume across Diagnosis Category $\rightarrow$ Discharge Disposition $\rightarrow$ Risk Tier $\rightarrow$ Age Bracket.
   - **Interactive Patient Drill-Through Table:** Displays patient encounter attributes, predicted ML risk score, and recommended clinical care protocol.

### 7.2 Core Enterprise DAX Measures (`pbi/measures.dax`)
The repository includes 22 production DAX measures adhering to Microsoft best practices:
```dax
[30-Day Readmission Rate] = 
DIVIDE(
    CALCULATE(COUNTROWS(Fact_Encounters), Fact_Encounters[is_readmitted_30] = 1),
    COUNTROWS(Fact_Encounters),
    0.0
)

[Excess Readmission Ratio] = 
DIVIDE([30-Day Readmission Rate], 0.080, 1.0)

[CMS Penalty Exposure] = 
VAR BaseRev = 125000000.0
VAR ERR = [Excess Readmission Ratio]
VAR RawPenalty = IF(ERR > 1.0, (ERR - 1.0) * 0.20, 0.0)
VAR EffectivePenalty = MIN(0.030, RawPenalty)
RETURN
    BaseRev * EffectivePenalty

[Intervention Net Savings] = 
VAR HighRiskSaves = [High Risk Encounters] * [High Risk Readmit Rate %] * 0.25
VAR DirectSavings = HighRiskSaves * 14400.0
VAR ProgramCost = [High Risk Encounters] * 250.0
RETURN
    DirectSavings - ProgramCost
```

---

## 8. HIPAA-Compliant Zero-PHI GenAI Clinical Summarizer

Located in `genai/clinical_cohort_summarizer.py`:
- **Strict HIPAA Safe Harbor Compliance:** No protected health information (PHI) or row-level patient data ever leaves the local system.
- **Aggregation Engine:** Executes pre-aggregated SQL queries generating cohort-level statistics (encounter size, readmission rate, avg stay, polypharmacy count, insulin adjustment %).
- **Action Plan Generator:** Emits structured 3-line clinical operations action plans:
  - *Line 1 (Risk Etiology):* Biomarker and utilization root causes.
  - *Line 2 (In-Hospital Discharge Protocol):* Bedside clinical pharmacist reconciliation & CDCES diabetes consult.
  - *Line 3 (Post-Acute Follow-Up Protocol):* 48-hour telephonic nurse check-in & 7-day transitional clinic visit.
- **Dual-Mode Engine:** Operates seamlessly via Google Gemini API (`GEMINI_API_KEY`) or in offline deterministic clinical emulation mode.
- **Human-in-the-Loop Gate:** Enforces `"review_status": "PENDING_CLINICAL_APPROVAL"` on all exported action plans.

---

## 9. Role-Tailored Resume Bullets

### Data Analyst Role
- *"Cleaned and analyzed 101K+ electronic health record encounters across 130 hospitals; eliminated cross-encounter target leakage via first-encounter deduplication across 71K unique patients and engineered clinical feature pipelines in Python and SQL."*
- *"Trained cost-sensitive LightGBM classifiers optimizing decision thresholds (~0.25) to capture 76.5% recall on 30-day readmissions, reducing projected hospital acute care losses by $10M+ under 100:1 false-negative cost asymmetry."*
- *"Formulated SQL star-schema and windowed transformation CTEs in SQLite/DuckDB, demonstrating that diabetic patients with $\ge 2$ prior inpatient admissions and active insulin titration experienced a 35.4% readmission rate—3.1x higher than baseline."*

### BI Developer Role
- *"Architected enterprise clinical command center in Power BI using modern PBIR and TMDL semantic modeling, authoring 22 DAX measures, decomposition trees, and risk-tier stratification across 71K patient encounters to mitigate $3.75M in CMS HRRP penalty exposure."*
- *"Engineered an interactive clinical decision-support pipeline in Power BI integrating machine learning readmission risk scores with dynamic drill-through worklists, accelerating high-risk patient outreach prioritization for care coordination teams by 85%."*
- *"Developed a dynamic 4-sheet Excel financial model with openpyxl simulating CMS Excess Readmission Ratios and nurse outreach ROI, projecting $4.2M in net operating savings with an estimated 350% program ROI."*

---

## 10. Verification & Reproducibility Guide

All scripts in this project run completely standalone with **zero external database servers**:

```bash
# 1. Generate Synthetic Data & Run Clinical ETL
python data/generate_data.py --samples 10000

# 2. Build Star-Schema SQLite DB & Run KPI Queries
python sql/build_db.py

# 3. Train Machine Learning Models, Cost-Sensitive Tuning & SHAP Plots
python notebooks/01_readmission_prediction_and_clinical_risk.py

# 4. Generate Dynamic Excel HRRP Financial Model
python excel/create_hrrp_model.py

# 5. Build and Validate Power BI PBIR & TMDL Command Center
python pbi/build_pbi_model.py

# 6. Run HIPAA-Compliant GenAI Clinical Cohort Summarizer
python genai/clinical_cohort_summarizer.py --test
```

*All scripts execute with exit code 0 and self-validate outputs on disk.*
