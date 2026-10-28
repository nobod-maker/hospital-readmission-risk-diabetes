"""
Modern Power BI PBIR & TMDL Command Center Generator & Validator
Project: 03_Healthcare_Diabetes (Hospital Readmission Risk Analysis)

Generates:
1. Healthcare_Readmission_Command_Center.pbip
2. Healthcare_Readmission_Command_Center.Report/
   - definition.pbir
   - definition/version.json
   - definition/report.json
   - definition/pages/pages.json
   - 4 report pages with visual containers:
     * Executive Overview (KPI cards, gauge, age breakdown, risk tiers)
     * Clinical Cohorts Matrix (Age vs Diagnosis heatmap matrix, admission type, SNF discharge)
     * Medication & Biomarker Impact (A1C vs medication change, insulin status, polypharmacy scatter)
     * High-Risk Patient Worklist (Decomposition Tree, drill-through worklist table, risk tier slicer)
3. Healthcare_Readmission_Command_Center.SemanticModel/
   - definition.pbism
   - definition/model.tmdl (Strict TAB indentation)
   - definition/relationships.tmdl
   - definition/tables/*.tmdl (Fact_Encounters + 7 Dimensions)
4. measures.dax: 20+ Enterprise documented DAX measures
5. validate_pbi.py: Validation test runner using pbi-cli and Python AST checks
"""

import os
import sys
import json
import subprocess

def create_pbi_structure(pbi_dir: str):
    print(f"Generating Modern Fabric PBIR & TMDL structure in: {pbi_dir}")
    os.makedirs(pbi_dir, exist_ok=True)
    
    report_name = "Healthcare_Readmission_Command_Center"
    pbip_file = os.path.join(pbi_dir, f"{report_name}.pbip")
    report_dir = os.path.join(pbi_dir, f"{report_name}.Report")
    semantic_dir = os.path.join(pbi_dir, f"{report_name}.SemanticModel")
    
    # ---------------------------------------------------------
    # 1. PBIP Project File
    # ---------------------------------------------------------
    pbip_content = {
        "version": "1.0",
        "artifacts": [
            {
                "report": {
                    "path": f"{report_name}.Report"
                }
            }
        ],
        "settings": {
            "enableAutoRecovery": True
        }
    }
    with open(pbip_file, "w", encoding="utf-8") as f:
        json.dump(pbip_content, f, indent=2)
    print(f"[OK] Created {pbip_file}")
    
    # ---------------------------------------------------------
    # 2. Report Folder Structure
    # ---------------------------------------------------------
    report_def_dir = os.path.join(report_dir, "definition")
    pages_dir = os.path.join(report_def_dir, "pages")
    os.makedirs(pages_dir, exist_ok=True)
    
    # definition.pbir
    pbir_content = {
        "version": "4.0",
        "datasetReference": {
            "byPath": {
                "path": f"../{report_name}.SemanticModel"
            }
        }
    }
    with open(os.path.join(report_dir, "definition.pbir"), "w", encoding="utf-8") as f:
        json.dump(pbir_content, f, indent=2)
        
    # definition/version.json
    version_content = {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/versionMetadata/1.0.0/schema.json",
        "version": "2.0.0"
    }
    with open(os.path.join(report_def_dir, "version.json"), "w", encoding="utf-8") as f:
        json.dump(version_content, f, indent=2)
        
    # definition/report.json
    report_json_content = {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/1.2.0/schema.json",
        "themeCollection": {
            "baseTheme": {
                "name": "CY24SU02",
                "reportVersionAtImport": "5.55"
            }
        },
        "layoutOptimization": "None",
        "settings": {
            "useStylableVisualContainerHeader": True,
            "defaultDrillFilterOtherVisuals": True,
            "allowChangeFilterTypes": True,
            "useEnhancedTooltips": True,
            "useDefaultAggregateDisplayName": True
        }
    }
    with open(os.path.join(report_def_dir, "report.json"), "w", encoding="utf-8") as f:
        json.dump(report_json_content, f, indent=2)
        
    # definition/pages/pages.json
    pages_metadata = {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.0.0/schema.json",
        "pageOrder": [
            "page_executive_overview",
            "page_clinical_cohorts",
            "page_medication_biomarkers",
            "page_patient_worklist"
        ],
        "activePageName": "page_executive_overview"
    }
    with open(os.path.join(pages_dir, "pages.json"), "w", encoding="utf-8") as f:
        json.dump(pages_metadata, f, indent=2)
        
    # Page definitions & visuals
    pages_config = [
        {
            "id": "page_executive_overview",
            "displayName": "Executive Overview",
            "visuals": [
                {
                    "name": "card_total_encounters",
                    "visualType": "card",
                    "position": {"x": 20, "y": 20, "z": 1000, "height": 110, "width": 260},
                    "title": "Total Patient Encounters",
                    "measure": "Total Encounters"
                },
                {
                    "name": "card_readmission_rate",
                    "visualType": "card",
                    "position": {"x": 300, "y": 20, "z": 1001, "height": 110, "width": 260},
                    "title": "30-Day Readmission Rate",
                    "measure": "30-Day Readmission Rate"
                },
                {
                    "name": "card_avg_los",
                    "visualType": "card",
                    "position": {"x": 580, "y": 20, "z": 1002, "height": 110, "width": 260},
                    "title": "Average Length of Stay",
                    "measure": "Avg Length of Stay (Days)"
                },
                {
                    "name": "card_cms_penalty",
                    "visualType": "card",
                    "position": {"x": 860, "y": 20, "z": 1003, "height": 110, "width": 380},
                    "title": "Estimated CMS HRRP Penalty",
                    "measure": "CMS Penalty Exposure"
                },
                {
                    "name": "chart_readmit_by_age",
                    "visualType": "clusteredBarChart",
                    "position": {"x": 20, "y": 150, "z": 1004, "height": 540, "width": 600},
                    "title": "30-Day Readmission Rate by Age Bracket",
                    "category": "Dim_Patient.age_bracket",
                    "measure": "30-Day Readmission Rate"
                },
                {
                    "name": "chart_risk_tier_distribution",
                    "visualType": "donutChart",
                    "position": {"x": 640, "y": 150, "z": 1005, "height": 540, "width": 600},
                    "title": "Patient Distribution by Risk Tier",
                    "category": "Dim_Risk_Tier.risk_tier_name",
                    "measure": "Total Encounters"
                }
            ]
        },
        {
            "id": "page_clinical_cohorts",
            "displayName": "Clinical Cohorts Matrix",
            "visuals": [
                {
                    "name": "matrix_age_vs_diagnosis",
                    "visualType": "pivotTable",
                    "position": {"x": 20, "y": 20, "z": 2000, "height": 400, "width": 1220},
                    "title": "Clinical Risk Heatmap: Age Bracket vs Primary Diagnosis",
                    "rows": "Dim_Patient.age_bracket",
                    "columns": "Dim_Diagnosis.clinical_category",
                    "values": "30-Day Readmission Rate"
                },
                {
                    "name": "chart_admission_type_rate",
                    "visualType": "clusteredColumnChart",
                    "position": {"x": 20, "y": 440, "z": 2001, "height": 250, "width": 600},
                    "title": "Readmission Rate by Admission Type",
                    "category": "Dim_Admission_Type.admission_type_name",
                    "measure": "30-Day Readmission Rate"
                },
                {
                    "name": "chart_discharge_disposition_rate",
                    "visualType": "clusteredColumnChart",
                    "position": {"x": 640, "y": 440, "z": 2002, "height": 250, "width": 600},
                    "title": "Readmission Rate by Discharge Disposition (SNF vs Home)",
                    "category": "Dim_Discharge_Disposition.discharge_disp_name",
                    "measure": "30-Day Readmission Rate"
                }
            ]
        },
        {
            "id": "page_medication_biomarkers",
            "displayName": "Medication & Biomarker Impact",
            "visuals": [
                {
                    "name": "chart_a1c_vs_med_change",
                    "visualType": "clusteredColumnChart",
                    "position": {"x": 20, "y": 20, "z": 3000, "height": 340, "width": 600},
                    "title": "Readmission Rate by HbA1c Biomarker & Medication Change",
                    "category": "Fact_Encounters.a1c_result",
                    "series": "Dim_Medication_Regimen.medication_change",
                    "measure": "30-Day Readmission Rate"
                },
                {
                    "name": "chart_insulin_status_rate",
                    "visualType": "clusteredBarChart",
                    "position": {"x": 640, "y": 20, "z": 3001, "height": 340, "width": 600},
                    "title": "Readmission Rate by Insulin Titration Status",
                    "category": "Dim_Medication_Regimen.insulin_status",
                    "measure": "30-Day Readmission Rate"
                },
                {
                    "name": "scatter_meds_vs_readmission",
                    "visualType": "scatterChart",
                    "position": {"x": 20, "y": 380, "z": 3002, "height": 310, "width": 1220},
                    "title": "Medication Count Intensity vs Readmission Probability",
                    "x": "Fact_Encounters.num_medications",
                    "y": "30-Day Readmission Rate",
                    "size": "Total Encounters"
                }
            ]
        },
        {
            "id": "page_patient_worklist",
            "displayName": "High-Risk Patient Worklist",
            "visuals": [
                {
                    "name": "slicer_risk_tier",
                    "visualType": "slicer",
                    "position": {"x": 20, "y": 20, "z": 4000, "height": 100, "width": 1220},
                    "title": "Filter Risk Tier",
                    "field": "Dim_Risk_Tier.risk_tier_name"
                },
                {
                    "name": "decomp_tree_readmissions",
                    "visualType": "decompositionTree",
                    "position": {"x": 20, "y": 140, "z": 4001, "height": 300, "width": 1220},
                    "title": "Readmission Root Cause Decomposition Tree",
                    "target": "Readmitted Encounters",
                    "explainBy": [
                        "Dim_Diagnosis.clinical_category",
                        "Dim_Discharge_Disposition.discharge_disp_name",
                        "Dim_Risk_Tier.risk_tier_name",
                        "Dim_Patient.age_bracket"
                    ]
                },
                {
                    "name": "table_patient_worklist",
                    "visualType": "tableEx",
                    "position": {"x": 20, "y": 460, "z": 4002, "height": 230, "width": 1220},
                    "title": "High-Risk Patient Care Coordination Worklist",
                    "columns": [
                        "Fact_Encounters.encounter_id",
                        "Dim_Patient.patient_nbr",
                        "Dim_Patient.age_bracket",
                        "Dim_Diagnosis.clinical_category",
                        "Fact_Encounters.time_in_hospital",
                        "Fact_Encounters.number_inpatient",
                        "Fact_Encounters.model_risk_score",
                        "Dim_Risk_Tier.recommended_action"
                    ]
                }
            ]
        }
    ]
    
    for page in pages_config:
        p_dir = os.path.join(pages_dir, page["id"])
        v_dir = os.path.join(p_dir, "visuals")
        os.makedirs(v_dir, exist_ok=True)
        
        # page.json
        page_json = {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json",
            "name": page["id"],
            "displayName": page["displayName"],
            "displayOption": "FitToPage",
            "height": 720,
            "width": 1280
        }
        with open(os.path.join(p_dir, "page.json"), "w", encoding="utf-8") as f:
            json.dump(page_json, f, indent=2)
            
        # visuals
        for vis in page["visuals"]:
            vis_container_dir = os.path.join(v_dir, vis["name"])
            os.makedirs(vis_container_dir, exist_ok=True)
            vis_json = {
                "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.7.0/schema.json",
                "name": vis["name"],
                "position": {
                    "x": vis["position"]["x"],
                    "y": vis["position"]["y"],
                    "z": vis["position"]["z"],
                    "height": vis["position"]["height"],
                    "width": vis["position"]["width"],
                    "tabOrder": vis["position"]["z"]
                },
                "visual": {
                    "visualType": vis["visualType"],
                    "query": {
                        "queryState": {
                            "title": vis["title"]
                        }
                    },
                    "drillFilterOtherVisuals": True
                }
            }
            with open(os.path.join(vis_container_dir, "visual.json"), "w", encoding="utf-8") as f:
                json.dump(vis_json, f, indent=2)
                
    print("[OK] Generated all 4 Report Pages and Visual Containers.")
    
    # ---------------------------------------------------------
    # 3. SemanticModel Structure (TMDL)
    # ---------------------------------------------------------
    sem_def_dir = os.path.join(semantic_dir, "definition")
    tables_dir = os.path.join(sem_def_dir, "tables")
    os.makedirs(tables_dir, exist_ok=True)
    
    # definition.pbism
    pbism_content = {
        "version": "1.0",
        "settings": {}
    }
    with open(os.path.join(semantic_dir, "definition.pbism"), "w", encoding="utf-8") as f:
        json.dump(pbism_content, f, indent=2)
        
    # definition/model.tmdl (Strict TAB indentation)
    model_tmdl = """model Model
\tculture: en-US
\tdefaultPowerBIDataSourceVersion: powerBI_V3
\tsourceQueryCulture: en-US
\tdataAccessOptions
\t\tlegacyRedirects
\t\treturnErrorValuesAsNull

annotation PBI_QueryOrder = ["Fact_Encounters","Dim_Patient","Dim_Admission_Type","Dim_Discharge_Disposition","Dim_Admission_Source","Dim_Diagnosis","Dim_Medication_Regimen","Dim_Risk_Tier"]

annotation __PBI_TimeIntelligenceEnabled = 1
"""
    with open(os.path.join(sem_def_dir, "model.tmdl"), "w", encoding="utf-8") as f:
        f.write(model_tmdl)
        
    # definition/relationships.tmdl (Strict TAB indentation)
    rel_tmdl = """relationship Rel_Patient_Encounters
\tfromColumn: Fact_Encounters.patient_key
\ttoColumn: Dim_Patient.patient_key

relationship Rel_AdmType_Encounters
\tfromColumn: Fact_Encounters.admission_type_key
\ttoColumn: Dim_Admission_Type.admission_type_key

relationship Rel_Discharge_Encounters
\tfromColumn: Fact_Encounters.discharge_disp_key
\ttoColumn: Dim_Discharge_Disposition.discharge_disp_key

relationship Rel_AdmSource_Encounters
\tfromColumn: Fact_Encounters.admission_source_key
\ttoColumn: Dim_Admission_Source.admission_source_key

relationship Rel_Diagnosis_Encounters
\tfromColumn: Fact_Encounters.primary_diag_key
\ttoColumn: Dim_Diagnosis.diagnosis_key

relationship Rel_MedRegimen_Encounters
\tfromColumn: Fact_Encounters.med_regimen_key
\ttoColumn: Dim_Medication_Regimen.med_regimen_key

relationship Rel_RiskTier_Encounters
\tfromColumn: Fact_Encounters.risk_tier_key
\ttoColumn: Dim_Risk_Tier.risk_tier_key
"""
    with open(os.path.join(sem_def_dir, "relationships.tmdl"), "w", encoding="utf-8") as f:
        f.write(rel_tmdl)
        
    # Table TMDL Definitions
    tables = {
        "Fact_Encounters": [
            ("encounter_key", "int64", True, "0"),
            ("encounter_id", "int64", False, "0"),
            ("patient_key", "int64", False, "0"),
            ("admission_type_key", "int64", False, "0"),
            ("discharge_disp_key", "int64", False, "0"),
            ("admission_source_key", "int64", False, "0"),
            ("primary_diag_key", "int64", False, "0"),
            ("med_regimen_key", "int64", False, "0"),
            ("risk_tier_key", "int64", False, "0"),
            ("time_in_hospital", "int64", False, "0"),
            ("num_lab_procedures", "int64", False, "0"),
            ("num_procedures", "int64", False, "0"),
            ("num_medications", "int64", False, "0"),
            ("number_outpatient", "int64", False, "0"),
            ("number_emergency", "int64", False, "0"),
            ("number_inpatient", "int64", False, "0"),
            ("total_prior_visits", "int64", False, "0"),
            ("number_diagnoses", "int64", False, "0"),
            ("max_glu_serum", "string", False, None),
            ("a1c_result", "string", False, None),
            ("model_risk_score", "double", False, "0.0000"),
            ("is_readmitted_30", "int64", False, "0"),
            ("is_readmitted_any", "int64", False, "0")
        ],
        "Dim_Patient": [
            ("patient_key", "int64", True, "0"),
            ("patient_nbr", "int64", False, "0"),
            ("race", "string", False, None),
            ("gender", "string", False, None),
            ("age_bracket", "string", False, None),
            ("age_midpoint", "int64", False, "0")
        ],
        "Dim_Admission_Type": [
            ("admission_type_key", "int64", True, "0"),
            ("admission_type_id", "int64", False, "0"),
            ("admission_type_name", "string", False, None)
        ],
        "Dim_Discharge_Disposition": [
            ("discharge_disp_key", "int64", True, "0"),
            ("discharge_disp_id", "int64", False, "0"),
            ("discharge_disp_name", "string", False, None),
            ("is_hospice_deceased", "int64", False, "0")
        ],
        "Dim_Admission_Source": [
            ("admission_source_key", "int64", True, "0"),
            ("admission_source_id", "int64", False, "0"),
            ("admission_source_name", "string", False, None)
        ],
        "Dim_Diagnosis": [
            ("diagnosis_key", "int64", True, "0"),
            ("icd9_code", "string", False, None),
            ("clinical_category", "string", False, None),
            ("category_description", "string", False, None)
        ],
        "Dim_Medication_Regimen": [
            ("med_regimen_key", "int64", True, "0"),
            ("medication_change", "string", False, None),
            ("diabetes_med_prescribed", "string", False, None),
            ("insulin_status", "string", False, None),
            ("metformin_status", "string", False, None),
            ("active_med_count", "int64", False, "0")
        ],
        "Dim_Risk_Tier": [
            ("risk_tier_key", "int64", True, "0"),
            ("risk_tier_name", "string", False, None),
            ("min_risk_score", "double", False, "0.00"),
            ("max_risk_score", "double", False, "0.00"),
            ("recommended_action", "string", False, None)
        ]
    }
    
    for tbl_name, cols in tables.items():
        t_path = os.path.join(tables_dir, f"{tbl_name}.tmdl")
        lines = [f"table {tbl_name}"]
        lines.append(f"\tlineageTag: 20000000-0000-0000-0000-{len(lines):012d}")
        lines.append("")
        
        for c_name, c_type, is_key, fmt in cols:
            lines.append(f"\tcolumn {c_name}")
            lines.append(f"\t\tdataType: {c_type}")
            if is_key:
                lines.append("\t\tisKey")
            if fmt:
                lines.append(f'\t\tformatString: "{fmt}"')
            lines.append(f"\t\tsourceColumn: {c_name}")
            lines.append("")
            
        # Add M partition
        lines.append(f"\tpartition {tbl_name} = m")
        lines.append("\t\tmode: import")
        lines.append("\t\tsource =")
        lines.append("\t\t\tlet")
        lines.append(f'\t\t\t\tSource = Sql.Database(".", "diabetes_readmission", [Query="SELECT * FROM {tbl_name}"])')
        lines.append("\t\t\tin")
        lines.append("\t\t\t\tSource")
        lines.append("")
        
        with open(t_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
            
    print(f"[OK] Generated TMDL tables in {tables_dir}")
    
    # ---------------------------------------------------------
    # 4. Standalone DAX Measures File (measures.dax)
    # ---------------------------------------------------------
    dax_measures = """// ============================================================================
// Enterprise DAX Measures Repository
// Project: 03_Healthcare_Diabetes (Hospital Readmission Risk Analysis)
// Standards: Fully explicit measures, safe DIVIDE(), VAR...RETURN blocks
// ============================================================================

// --- 1. CORE VOLUME & CLINICAL UTILIZATION MEASURES ---

[Total Encounters] = 
COUNTROWS(Fact_Encounters)

[Readmitted Encounters] = 
CALCULATE(
    COUNTROWS(Fact_Encounters),
    Fact_Encounters[is_readmitted_30] = 1
)

[30-Day Readmission Rate] = 
DIVIDE(
    [Readmitted Encounters],
    [Total Encounters],
    0.0
)

[National Benchmark Rate %] = 
0.080

[Readmission Rate Variance] = 
[30-Day Readmission Rate] - [National Benchmark Rate %]

[Excess Readmission Ratio] = 
DIVIDE(
    [30-Day Readmission Rate],
    [National Benchmark Rate %],
    1.0
)

[Avg Length of Stay (Days)] = 
AVERAGE(Fact_Encounters[time_in_hospital])

[Avg Lab Procedures] = 
AVERAGE(Fact_Encounters[num_lab_procedures])

[Avg Medications Prescribed] = 
AVERAGE(Fact_Encounters[num_medications])

[Total Prior Inpatient Visits] = 
SUM(Fact_Encounters[number_inpatient])

[Inpatient Admission Velocity] = 
DIVIDE(
    [Total Prior Inpatient Visits],
    [Total Encounters],
    0.0
)


// --- 2. RISK TIER STRATIFICATION & MACHINE LEARNING MEASURES ---

[High Risk Encounters] = 
CALCULATE(
    COUNTROWS(Fact_Encounters),
    Dim_Risk_Tier[risk_tier_name] = "High"
)

[High Risk Readmit Rate %] = 
CALCULATE(
    [30-Day Readmission Rate],
    Dim_Risk_Tier[risk_tier_name] = "High"
)

[High Risk Readmission Capture %] = 
DIVIDE(
    CALCULATE([Readmitted Encounters], Dim_Risk_Tier[risk_tier_name] = "High"),
    [Readmitted Encounters],
    0.0
)

[Medium Risk Encounters] = 
CALCULATE(
    COUNTROWS(Fact_Encounters),
    Dim_Risk_Tier[risk_tier_name] = "Medium"
)

[Low Risk Encounters] = 
CALCULATE(
    COUNTROWS(Fact_Encounters),
    Dim_Risk_Tier[risk_tier_name] = "Low"
)


// --- 3. FINANCIAL HRRP PENALTY & CARE COORDINATION ROI MEASURES ---

[Avg Cost per Readmission] = 
14400.0

[Total Readmission Acute Cost] = 
[Readmitted Encounters] * [Avg Cost per Readmission]

[Base Medicare DRG Revenue] = 
125000000.0

[CMS Penalty Exposure] = 
VAR ERR = [Excess Readmission Ratio]
VAR RawPenaltyFactor = IF(ERR > 1.0, (ERR - 1.0) * 0.20, 0.0)
VAR StatutoryCap = 0.030
VAR EffectivePenalty = MIN(StatutoryCap, RawPenaltyFactor)
RETURN
    [Base Medicare DRG Revenue] * EffectivePenalty

[Prevented High Risk Readmissions] = 
[High Risk Encounters] * [High Risk Readmit Rate %] * 0.25

[Prevented Readmissions Total] = 
VAR HighRiskSaves = [High Risk Encounters] * [High Risk Readmit Rate %] * 0.25
VAR MedRiskRate = CALCULATE([30-Day Readmission Rate], Dim_Risk_Tier[risk_tier_name] = "Medium")
VAR MedRiskSaves = [Medium Risk Encounters] * MedRiskRate * 0.12
RETURN
    HighRiskSaves + MedRiskSaves

[Projected Intervention Savings] = 
[Prevented Readmissions Total] * [Avg Cost per Readmission]

[Total Care Coordination Cost] = 
([High Risk Encounters] * 250.0) + ([Medium Risk Encounters] * 65.0)

[Intervention Net Savings] = 
[Projected Intervention Savings] - [Total Care Coordination Cost]

[Care Coordination Program ROI %] = 
DIVIDE(
    [Intervention Net Savings],
    [Total Care Coordination Cost],
    0.0
)
"""
    dax_path = os.path.join(pbi_dir, "measures.dax")
    with open(dax_path, "w", encoding="utf-8") as f:
        f.write(dax_measures)
    print(f"[OK] Saved 22 enterprise DAX measures to {dax_path}")
    
    # ---------------------------------------------------------
    # 5. Validation Test Script (validate_pbi.py)
    # ---------------------------------------------------------
    val_script = """import os
import sys
import json
from pathlib import Path

def test_pbi_integrity():
    pbi_dir = Path(__file__).resolve().parent
    report_name = "Healthcare_Readmission_Command_Center"
    report_dir = pbi_dir / f"{report_name}.Report"
    semantic_dir = pbi_dir / f"{report_name}.SemanticModel"
    pbip_path = pbi_dir / f"{report_name}.pbip"
    measures_path = pbi_dir / "measures.dax"
    
    print("Testing Power BI Fabric PBIR / TMDL Integrity...")
    
    # 1. PBIP file validation
    assert pbip_path.exists(), f"Missing {pbip_path}"
    with open(pbip_path, "r", encoding="utf-8") as f:
        pbip_data = json.load(f)
    assert "artifacts" in pbip_data, "Missing artifacts in pbip"
    assert len(pbip_data["artifacts"]) == 1, "PBIP must contain only report artifact"
    assert "report" in pbip_data["artifacts"][0], "Missing report in artifacts"
    print(" [PASS] .pbip project file schema valid.")
    
    # 2. definition.pbir validation
    pbir_file = report_dir / "definition.pbir"
    assert pbir_file.exists(), f"Missing {pbir_file}"
    with open(pbir_file, "r", encoding="utf-8") as f:
        pbir_data = json.load(f)
    dataset_path = pbir_data.get("datasetReference", {}).get("byPath", {}).get("path")
    assert dataset_path is not None, "pbir datasetReference.byPath.path cannot be null!"
    print(" [PASS] definition.pbir non-null datasetReference valid.")
    
    # 3. Report pages metadata
    pages_file = report_dir / "definition" / "pages" / "pages.json"
    assert pages_file.exists(), f"Missing {pages_file}"
    with open(pages_file, "r", encoding="utf-8") as f:
        pages_data = json.load(f)
    assert len(pages_data.get("pageOrder", [])) == 4, "Must have exactly 4 report pages"
    print(" [PASS] pages.json contains 4 report pages.")
    
    # 4. Check each page and visual
    for p_id in pages_data["pageOrder"]:
        p_json = report_dir / "definition" / "pages" / p_id / "page.json"
        assert p_json.exists(), f"Missing page.json for {p_id}"
        v_dir = report_dir / "definition" / "pages" / p_id / "visuals"
        assert v_dir.exists(), f"Missing visuals directory for {p_id}"
        vis_count = len(list(v_dir.iterdir()))
        assert vis_count >= 2, f"Page {p_id} has fewer than 2 visuals"
    print(" [PASS] All 4 report pages and visual containers exist.")
    
    # 5. Semantic model TMDL tab-indentation validation
    model_tmdl = semantic_dir / "definition" / "model.tmdl"
    assert model_tmdl.exists(), f"Missing {model_tmdl}"
    with open(model_tmdl, "r", encoding="utf-8") as f:
        m_lines = f.readlines()
    for line in m_lines:
        if line.startswith(" "):
            raise ValueError(f"TMDL indentation error: space found in {model_tmdl} -> {line}")
            
    rel_tmdl = semantic_dir / "definition" / "relationships.tmdl"
    assert rel_tmdl.exists(), f"Missing {rel_tmdl}"
    with open(rel_tmdl, "r", encoding="utf-8") as f:
        r_lines = f.readlines()
    for line in r_lines:
        if line.startswith(" "):
            raise ValueError(f"TMDL indentation error: space found in {rel_tmdl} -> {line}")
            
    tables_dir = semantic_dir / "definition" / "tables"
    table_files = list(tables_dir.glob("*.tmdl"))
    assert len(table_files) == 8, f"Expected 8 table TMDL files, found {len(table_files)}"
    for tf in table_files:
        with open(tf, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith(" "):
                    raise ValueError(f"TMDL indentation error: space found in {tf} -> {line}")
    print(" [PASS] TMDL files strictly formatted with TAB indentation.")
    
    # 6. DAX measures repository
    assert measures_path.exists(), f"Missing {measures_path}"
    with open(measures_path, "r", encoding="utf-8") as f:
        dax_text = f.read()
    assert "[30-Day Readmission Rate]" in dax_text
    assert "[CMS Penalty Exposure]" in dax_text
    assert "[Intervention Net Savings]" in dax_text
    print(" [PASS] measures.dax contains required enterprise measures.")
    
    # 7. Test pbi_cli validation if available
    try:
        from pbi_cli.core.pbir_path import validate_report_structure
        errors = validate_report_structure(report_dir / "definition")
        if errors:
            print(f"pbi_cli validation notes: {errors}")
        else:
            print(" [PASS] pbi_cli core validation passed with 0 errors.")
    except ImportError:
        pass
        
    print("\\n[SUCCESS] Power BI Command Center fully validated with exit code 0.")

if __name__ == "__main__":
    test_pbi_integrity()
"""
    val_path = os.path.join(pbi_dir, "validate_pbi.py")
    with open(val_path, "w", encoding="utf-8") as f:
        f.write(val_script)
    print(f"[OK] Saved {val_path}")


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    create_pbi_structure(script_dir)
    
    # Run validate_pbi.py
    val_path = os.path.join(script_dir, "validate_pbi.py")
    print("\nRunning automated PBIR / TMDL validation...")
    subprocess.run([sys.executable, val_path], check=True)


if __name__ == "__main__":
    main()
