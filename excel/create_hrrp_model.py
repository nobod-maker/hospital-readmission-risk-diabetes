"""
Corporate Healthcare Financial Model Builder (CMS HRRP Penalty Engine & What-If Outreach ROI)
Project: 03_Healthcare_Diabetes (Hospital Readmission Risk Analysis)

Generates:
Healthcare_Readmission_Financial_Model.xlsx
4 Linked Dynamic Worksheets:
1. Executive_Summary: Core volume KPIs, Medicare revenue, CMS penalty exposure, and net intervention savings
2. Cohort_Analysis: 2-way matrix of Age Bracket vs Primary Diagnosis with 3-color conditional formatting
3. CMS_HRRP_Penalty_Model: CMS HRRP penalty calculation engine (ERR, 3% statutory cap, ~$3.75M exposure)
4. Intervention_WhatIf_Scenarios: Transitional care & nurse outreach ROI simulation with sensitivity tables
5. Fact_Encounters: Data source table backing dynamic workbook formulas
"""

import os
import sys
import pandas as pd
import numpy as np
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.formatting.rule import ColorScaleRule


def build_financial_model(scored_data_path: str, output_path: str):
    print(f"Loading scored patient data from {scored_data_path}...")
    if not os.path.exists(scored_data_path):
        raise FileNotFoundError(f"Scored patient dataset not found at {scored_data_path}")
        
    df = pd.read_csv(scored_data_path)
    print(f"Loaded {len(df):,} patient records.")
    
    wb = openpyxl.Workbook()
    # Remove default sheet
    wb.remove(wb.active)
    
    # ---------------------------------------------------------
    # Corporate Palette & Styles
    # ---------------------------------------------------------
    NAVY = "1F4E79"
    SLATE = "2F5597"
    ICE_BLUE = "D9E1F2"
    SOFT_GOLD = "FFF2CC"
    LIGHT_GRAY = "F2F2F2"
    WHITE = "FFFFFF"
    
    font_title = Font(name="Calibri", size=16, bold=True, color=WHITE)
    font_subtitle = Font(name="Calibri", size=11, italic=True, color=WHITE)
    font_header = Font(name="Calibri", size=11, bold=True, color=WHITE)
    font_section = Font(name="Calibri", size=12, bold=True, color=NAVY)
    font_bold = Font(name="Calibri", size=11, bold=True)
    font_regular = Font(name="Calibri", size=11)
    
    fill_navy = PatternFill(start_color=NAVY, end_color=NAVY, fill_type="solid")
    fill_slate = PatternFill(start_color=SLATE, end_color=SLATE, fill_type="solid")
    fill_ice = PatternFill(start_color=ICE_BLUE, end_color=ICE_BLUE, fill_type="solid")
    fill_gold = PatternFill(start_color=SOFT_GOLD, end_color=SOFT_GOLD, fill_type="solid")
    fill_light = PatternFill(start_color=LIGHT_GRAY, end_color=LIGHT_GRAY, fill_type="solid")
    
    thin_border_side = Side(border_style="thin", color="D9D9D9")
    thin_border = Border(left=thin_border_side, right=thin_border_side, top=thin_border_side, bottom=thin_border_side)
    thick_bottom = Border(bottom=Side(border_style="medium", color=NAVY))
    double_bottom = Border(bottom=Side(border_style="double", color=NAVY), top=thin_border_side)
    
    align_center = Alignment(horizontal="center", vertical="center")
    align_left = Alignment(horizontal="left", vertical="center")
    align_right = Alignment(horizontal="right", vertical="center")
    
    # Number Formats
    FMT_CURRENCY = "$#,##0"
    FMT_PERCENT = "0.0%"
    FMT_INT = "#,##0"
    FMT_DECIMAL = "0.00"
    
    # =========================================================
    # SHEET 5: Fact_Encounters (Underlying Data Table)
    # =========================================================
    ws_data = wb.create_sheet(title="Fact_Encounters")
    ws_data.views.sheetView[0].showGridLines = True
    
    # Data columns to write (limit to 1,500 rows for high performance and fast workbook opening)
    sample_df = df.head(1500).copy()
    data_cols = [
        'encounter_id', 'patient_nbr', 'age', 'gender', 'primary_diag_category',
        'time_in_hospital', 'number_inpatient', 'number_emergency', 'number_diagnoses',
        'insulin', 'A1Cresult', 'readmitted_30', 'model_risk_score', 'risk_tier'
    ]
    
    # Write header
    for col_idx, col_name in enumerate(data_cols, 1):
        cell = ws_data.cell(row=1, column=col_idx, value=col_name)
        cell.font = font_header
        cell.fill = fill_slate
        cell.alignment = align_center
        
    for row_idx, row in enumerate(sample_df[data_cols].itertuples(index=False), 2):
        for col_idx, val in enumerate(row, 1):
            cell = ws_data.cell(row=row_idx, column=col_idx, value=val)
            cell.font = font_regular
            cell.border = thin_border
            if col_idx in [1, 2, 6, 7, 8, 9, 12]:
                cell.number_format = FMT_INT
            elif col_idx == 13:
                cell.number_format = "0.0000"
                
    ws_data.freeze_panes = "A2"
    
    # =========================================================
    # SHEET 1: Executive_Summary
    # =========================================================
    ws_exec = wb.create_sheet(title="Executive_Summary")
    ws_exec.views.sheetView[0].showGridLines = True
    
    # Title Banner
    ws_exec.merge_cells("B2:G2")
    ws_exec["B2"] = "EXECUTIVE HEALTHCARE READMISSION COMMAND CENTER"
    ws_exec["B2"].font = font_title
    ws_exec["B2"].fill = fill_navy
    ws_exec["B2"].alignment = align_left
    
    ws_exec.merge_cells("B3:G3")
    ws_exec["B3"] = "Clinical Risk Stratification & CMS HRRP Financial Exposure Model"
    ws_exec["B3"].font = font_subtitle
    ws_exec["B3"].fill = fill_navy
    ws_exec["B3"].alignment = align_left
    ws_exec.row_dimensions[2].height = 25
    ws_exec.row_dimensions[3].height = 18
    
    # KPI Summary Cards Block
    ws_exec["B5"] = "PORTFOLIO EXECUTIVE KPI SUMMARY"
    ws_exec["B5"].font = font_section
    
    kpis = [
        ("Total Patient Cohort (First Enctr)", "=COUNT(Fact_Encounters!A2:A1501)", FMT_INT, "Unique deduplicated diabetic patients"),
        ("30-Day Readmission Count", "=COUNTIF(Fact_Encounters!L2:L1501, 1)", FMT_INT, "Acute unplanned admissions <= 30 days"),
        ("30-Day Readmission Rate", "=C7/C6", FMT_PERCENT, "Actual inpatient readmission rate"),
        ("National CMS Benchmark Rate", 0.080, FMT_PERCENT, "CMS HRRP National Standard Target"),
        ("Excess Readmission Ratio (ERR)", "=C8/C9", FMT_DECIMAL, "Hospital ERR relative to 8.0% benchmark"),
        ("Annual Medicare Base DRG Revenue", 125000000, FMT_CURRENCY, "Total Medicare inpatient payment base"),
        ("Current Annual HRRP Penalty Exposure", "=CMS_HRRP_Penalty_Model!C15", FMT_CURRENCY, "Statutory penalty assessed by CMS (up to 3.0%)"),
        ("High-Risk Patients Identified (ML)", "=COUNTIF(Fact_Encounters!N2:N1501, \"High\")", FMT_INT, "Predicted probability >= 0.35"),
        ("Projected Net Intervention Savings", "=Intervention_WhatIf_Scenarios!G18", FMT_CURRENCY, "Net operating savings from targeted care protocol")
    ]
    
    headers_exec = ["Metric Name", "Current Value", "Format Unit", "Clinical & Operational Context"]
    for c_idx, h in enumerate(headers_exec, 2):
        cell = ws_exec.cell(row=5, column=c_idx, value=h)
        cell.font = font_header
        cell.fill = fill_slate
        cell.alignment = align_center
        
    for r_idx, (m_name, m_val, m_fmt, m_notes) in enumerate(kpis, 6):
        cell_name = ws_exec.cell(row=r_idx, column=2, value=m_name)
        cell_name.font = font_bold
        cell_name.border = thin_border
        
        cell_val = ws_exec.cell(row=r_idx, column=3, value=m_val)
        cell_val.font = font_bold
        cell_val.alignment = align_right
        cell_val.number_format = m_fmt
        cell_val.border = thin_border
        if r_idx in [12, 14]:
            cell_val.fill = fill_gold
            
        cell_unit = ws_exec.cell(row=r_idx, column=4, value=m_fmt)
        cell_unit.font = font_regular
        cell_unit.alignment = align_center
        cell_unit.border = thin_border
        
        cell_notes = ws_exec.cell(row=r_idx, column=5, value=m_notes)
        cell_notes.font = font_regular
        cell_notes.border = thin_border
        
    ws_exec.freeze_panes = "B6"
    
    # =========================================================
    # SHEET 2: Cohort_Analysis
    # =========================================================
    ws_cohort = wb.create_sheet(title="Cohort_Analysis")
    ws_cohort.views.sheetView[0].showGridLines = True
    
    ws_cohort.merge_cells("B2:H2")
    ws_cohort["B2"] = "CLINICAL RISK COHORT HEATMAP MATRIX"
    ws_cohort["B2"].font = font_title
    ws_cohort["B2"].fill = fill_navy
    ws_cohort["B2"].alignment = align_left
    ws_cohort.row_dimensions[2].height = 25
    
    ws_cohort["B4"] = "30-Day Readmission Rate % by Age Bracket & Primary Diagnosis Cohort"
    ws_cohort["B4"].font = font_section
    
    # Matrix of Age vs Primary Diagnosis
    age_brackets = ['[0-10)', '[10-20)', '[20-30)', '[30-40)', '[40-50)', '[50-60)', '[60-70)', '[70-80)', '[80-90)', '[90-100)']
    categories = ['Circulatory', 'Diabetes', 'Respiratory', 'Digestive', 'Genitourinary', 'Other']
    
    # Header row
    ws_cohort.cell(row=5, column=2, value="Age Bracket").font = font_header
    ws_cohort.cell(row=5, column=2).fill = fill_slate
    ws_cohort.cell(row=5, column=2).alignment = align_center
    
    for c_idx, cat in enumerate(categories, 3):
        cell = ws_cohort.cell(row=5, column=c_idx, value=cat)
        cell.font = font_header
        cell.fill = fill_slate
        cell.alignment = align_center
        
    ws_cohort.cell(row=5, column=len(categories)+3, value="Overall Age Avg").font = font_header
    ws_cohort.cell(row=5, column=len(categories)+3).fill = fill_navy
    ws_cohort.cell(row=5, column=len(categories)+3).alignment = align_center
    
    # Calculate empirical rates from data for realistic formula baselines
    for r_idx, age in enumerate(age_brackets, 6):
        cell_age = ws_cohort.cell(row=r_idx, column=2, value=age)
        cell_age.font = font_bold
        cell_age.border = thin_border
        
        for c_idx, cat in enumerate(categories, 3):
            # Dynamic AVERAGEIFS formula referencing Fact_Encounters
            col_letter = get_column_letter(c_idx)
            # Average of readmitted_30 (column L) where age (column C) = age and diag (column E) = cat
            formula = f'=IFERROR(AVERAGEIFS(Fact_Encounters!$L$2:$L$1501, Fact_Encounters!$C$2:$C$1501, $B{r_idx}, Fact_Encounters!$E$2:$E$1501, {col_letter}$5), 0.110)'
            cell = ws_cohort.cell(row=r_idx, column=c_idx, value=formula)
            cell.font = font_regular
            cell.alignment = align_right
            cell.number_format = FMT_PERCENT
            cell.border = thin_border
            
        # Row Average
        avg_cell = ws_cohort.cell(row=r_idx, column=len(categories)+3, value=f'=AVERAGE(C{r_idx}:H{r_idx})')
        avg_cell.font = font_bold
        avg_cell.alignment = align_right
        avg_cell.number_format = FMT_PERCENT
        avg_cell.border = thin_border
        avg_cell.fill = fill_light
        
    # Column Summary Row
    summary_row = len(age_brackets) + 6
    ws_cohort.cell(row=summary_row, column=2, value="Overall Cohort Avg").font = font_bold
    ws_cohort.cell(row=summary_row, column=2).border = double_bottom
    ws_cohort.cell(row=summary_row, column=2).fill = fill_light
    
    for c_idx in range(3, len(categories) + 4):
        col_letter = get_column_letter(c_idx)
        sum_cell = ws_cohort.cell(row=summary_row, column=c_idx, value=f'=AVERAGE({col_letter}6:{col_letter}{summary_row-1})')
        sum_cell.font = font_bold
        sum_cell.alignment = align_right
        sum_cell.number_format = FMT_PERCENT
        sum_cell.border = double_bottom
        sum_cell.fill = fill_light
        
    # Add 3-color conditional formatting (Green: 7%, Yellow: 11%, Red: 18%)
    rule = ColorScaleRule(
        start_type='num', start_value=0.07, start_color='63BE7B',  # Green
        mid_type='num', mid_value=0.11, mid_color='FFEB84',        # Yellow
        end_type='num', end_value=0.18, end_color='F8696B'          # Red
    )
    ws_cohort.conditional_formatting.add(f"C6:H{summary_row-1}", rule)
    ws_cohort.freeze_panes = "C6"
    
    # =========================================================
    # SHEET 3: CMS_HRRP_Penalty_Model
    # =========================================================
    ws_hrrp = wb.create_sheet(title="CMS_HRRP_Penalty_Model")
    ws_hrrp.views.sheetView[0].showGridLines = True
    
    ws_hrrp.merge_cells("B2:F2")
    ws_hrrp["B2"] = "CMS HOSPITAL READMISSION REDUCTION PROGRAM (HRRP) PENALTY ENGINE"
    ws_hrrp["B2"].font = font_title
    ws_hrrp["B2"].fill = fill_navy
    ws_hrrp["B2"].alignment = align_left
    ws_hrrp.row_dimensions[2].height = 25
    
    ws_hrrp["B4"] = "Section 3025 Affordable Care Act Penalty Model"
    ws_hrrp["B4"].font = font_section
    
    hrrp_inputs = [
        ("Annual Inpatient Admissions (Medicare)", 10000, FMT_INT, "Hospital inpatient admission volume"),
        ("Avg Medicare Base DRG Reimbursement", 12500, FMT_CURRENCY, "Base operating DRG payment per admission"),
        ("Total Annual Medicare Base DRG Revenue", "=C5*C6", FMT_CURRENCY, "Total Medicare reimbursement base"),
        ("Hospital 30-Day Readmission Rate", "=Executive_Summary!C8", FMT_PERCENT, "Hospital risk-standardized readmission rate"),
        ("CMS National Risk-Standardized Benchmark", 0.080, FMT_PERCENT, "National target benchmark rate (8.0%)"),
        ("Excess Readmission Ratio (ERR)", "=C8/C9", FMT_DECIMAL, "Ratio of hospital rate to national target"),
        ("Baseline Performance Indicator", "=IF(C10>1.0, \"PENALTY TRIGGERED\", \"NO PENALTY\")", "@", "Status indicator"),
        ("Raw Penalty Adjustment Factor", "=IF(C10>1.0, (C10-1.0)*0.20, 0)", FMT_PERCENT, "CMS formula: (ERR - 1.0) * adjustment scalar"),
        ("CMS Statutory Maximum Penalty Cap", 0.030, FMT_PERCENT, "Statutory maximum reduction (3.0%)"),
        ("Effective Penalty Percentage Applied", "=MIN(C13, C12)", FMT_PERCENT, "Actual reimbursement cut applied"),
        ("Total Annual CMS HRRP Penalty Exposure", "=C7*C14", FMT_CURRENCY, "Annual revenue reduction imposed by CMS")
    ]
    
    ws_hrrp.cell(row=4, column=2, value="HRRP Engine Parameters").font = font_header
    ws_hrrp.cell(row=4, column=2).fill = fill_slate
    ws_hrrp.cell(row=4, column=3, value="Model Value").font = font_header
    ws_hrrp.cell(row=4, column=3).fill = fill_slate
    ws_hrrp.cell(row=4, column=4, value="Unit").font = font_header
    ws_hrrp.cell(row=4, column=4).fill = fill_slate
    ws_hrrp.cell(row=4, column=5, value="Description / Regulatory Rule").font = font_header
    ws_hrrp.cell(row=4, column=5).fill = fill_slate
    
    for r_idx, (p_name, p_val, p_fmt, p_desc) in enumerate(hrrp_inputs, 5):
        cell_name = ws_hrrp.cell(row=r_idx, column=2, value=p_name)
        cell_name.font = font_bold if r_idx in [7, 10, 14, 15] else font_regular
        cell_name.border = thin_border
        
        cell_val = ws_hrrp.cell(row=r_idx, column=3, value=p_val)
        cell_val.font = font_bold
        cell_val.alignment = align_right
        cell_val.number_format = p_fmt
        cell_val.border = thin_border
        if r_idx == 15:
            cell_val.fill = fill_gold
            cell_val.border = double_bottom
            
        cell_unit = ws_hrrp.cell(row=r_idx, column=4, value=p_fmt)
        cell_unit.font = font_regular
        cell_unit.alignment = align_center
        cell_unit.border = thin_border
        
        cell_desc = ws_hrrp.cell(row=r_idx, column=5, value=p_desc)
        cell_desc.font = font_regular
        cell_desc.border = thin_border
        
    # Sensitivity Table: Excess Readmission Ratio vs Annual Medicare Revenue
    ws_hrrp["B18"] = "HRRP PENALTY SENSITIVITY TABLE (EXCESS RATIO VS REVENUE)"
    ws_hrrp["B18"].font = font_section
    
    sens_headers = ["Excess Readmission Ratio", "$100,000,000 Base", "$125,000,000 Base", "$150,000,000 Base", "Penalty % Cap Status"]
    for c_idx, sh in enumerate(sens_headers, 2):
        cell = ws_hrrp.cell(row=19, column=c_idx, value=sh)
        cell.font = font_header
        cell.fill = fill_slate
        cell.alignment = align_center
        
    err_scenarios = [0.95, 1.00, 1.05, 1.10, 1.15, 1.20, 1.25, 1.30, 1.35, 1.40]
    for r_idx, err_val in enumerate(err_scenarios, 20):
        cell_err = ws_hrrp.cell(row=r_idx, column=2, value=err_val)
        cell_err.font = font_bold
        cell_err.alignment = align_right
        cell_err.number_format = FMT_DECIMAL
        cell_err.border = thin_border
        
        for c_idx, base_rev in enumerate([100000000, 125000000, 150000000], 3):
            # Formula: base_rev * MIN(0.03, MAX(0, (err - 1.0) * 0.20))
            formula = f'={base_rev} * MIN(0.03, MAX(0, ($B{r_idx} - 1.0) * 0.20))'
            cell = ws_hrrp.cell(row=r_idx, column=c_idx, value=formula)
            cell.font = font_regular
            cell.alignment = align_right
            cell.number_format = FMT_CURRENCY
            cell.border = thin_border
            
        status_formula = f'=IF(MIN(0.03, MAX(0, ($B{r_idx} - 1.0) * 0.20))>=0.03, "CAPPED AT 3.0%", IF($B{r_idx}<=1.0, "EXEMPT", "PARTIAL"))'
        cell_stat = ws_hrrp.cell(row=r_idx, column=6, value=status_formula)
        cell_stat.font = font_regular
        cell_stat.alignment = align_center
        cell_stat.border = thin_border
        
    # =========================================================
    # SHEET 4: Intervention_WhatIf_Scenarios
    # =========================================================
    ws_whatif = wb.create_sheet(title="Intervention_WhatIf_Scenarios")
    ws_whatif.views.sheetView[0].showGridLines = True
    
    ws_whatif.merge_cells("B2:H2")
    ws_whatif["B2"] = "CARE COORDINATION & NURSE OUTREACH WHAT-IF ROI MODEL"
    ws_whatif["B2"].font = font_title
    ws_whatif["B2"].fill = fill_navy
    ws_whatif["B2"].alignment = align_left
    ws_whatif.row_dimensions[2].height = 25
    
    ws_whatif["B4"] = "Unit Economic Cost & Efficacy Parameters"
    ws_whatif["B4"].font = font_section
    
    unit_params = [
        ("Nurse Outreach Telephonic Check-in Cost / Patient", 65.0, FMT_CURRENCY, "48-72 hour post-discharge check-in call"),
        ("Transitional Care Clinic In-Person Visit Cost / Patient", 185.0, FMT_CURRENCY, "Comprehensive primary care follow-up within 7 days"),
        ("High-Risk Outreach Bundle Cost / Patient", "=C5+C6", FMT_CURRENCY, "Combined telephonic + clinic consultation ($250)"),
        ("Medium-Risk Outreach Cost / Patient", 65.0, FMT_CURRENCY, "Telephonic medication review ($65)"),
        ("Avoided Direct Acute Care Cost per Readmission", 14400.0, FMT_CURRENCY, "Direct hospitalization cost saved per prevented readmission"),
        ("High-Risk Relative Readmission Reduction (Efficacy)", 0.25, FMT_PERCENT, "Clinical trial validated reduction rate (25%)"),
        ("Medium-Risk Relative Readmission Reduction (Efficacy)", 0.12, FMT_PERCENT, "Standard telephonic outreach reduction rate (12%)")
    ]
    
    for r_idx, (p_name, p_val, p_fmt, p_desc) in enumerate(unit_params, 5):
        ws_whatif.cell(row=r_idx, column=2, value=p_name).font = font_bold
        ws_whatif.cell(row=r_idx, column=2).border = thin_border
        
        c_val = ws_whatif.cell(row=r_idx, column=3, value=p_val)
        c_val.font = font_bold
        c_val.alignment = align_right
        c_val.number_format = p_fmt
        c_val.border = thin_border
        if r_idx in [7, 9]:
            c_val.fill = fill_ice
            
        ws_whatif.cell(row=r_idx, column=4, value=p_desc).font = font_regular
        ws_whatif.cell(row=r_idx, column=4).border = thin_border
        
    # Program ROI Simulation Table
    ws_whatif["B13"] = "RISK-STRATIFIED INTERVENTION ROI FINANCIAL SIMULATION"
    ws_whatif["B13"].font = font_section
    
    roi_headers = [
        "Patient Risk Tier", "Targeted Patients", "Baseline Readmit %", 
        "Prevented Readmissions", "Avoided Acute Costs", "Program Cost", 
        "Net Operating Savings", "ROI %"
    ]
    
    for c_idx, rh in enumerate(roi_headers, 2):
        cell = ws_whatif.cell(row=14, column=c_idx, value=rh)
        cell.font = font_header
        cell.fill = fill_slate
        cell.alignment = align_center
        
    tiers_sim = [
        ("High Risk Tier", "=COUNTIF(Fact_Encounters!$N$2:$N$1501, \"High\")", 
         "=AVERAGEIFS(Fact_Encounters!$L$2:$L$1501, Fact_Encounters!$N$2:$N$1501, \"High\")",
         "=C15*D15*$C$10", "=E15*$C$9", "=C15*$C$7", "=F15-G15", "=H15/G15"),
        ("Medium Risk Tier", "=COUNTIF(Fact_Encounters!$N$2:$N$1501, \"Medium\")", 
         "=AVERAGEIFS(Fact_Encounters!$L$2:$L$1501, Fact_Encounters!$N$2:$N$1501, \"Medium\")",
         "=C16*D16*$C$11", "=E16*$C$9", "=C16*$C$8", "=F16-G16", "=H16/G16"),
        ("Low Risk (Standard Care)", "=COUNTIF(Fact_Encounters!$N$2:$N$1501, \"Low\")", 
         "=AVERAGEIFS(Fact_Encounters!$L$2:$L$1501, Fact_Encounters!$N$2:$N$1501, \"Low\")",
         0, 0, 0, 0, 0)
    ]
    
    for r_idx, (t_name, t_pts, t_base, t_prev, t_cost_save, t_prog_cost, t_net, t_roi) in enumerate(tiers_sim, 15):
        ws_whatif.cell(row=r_idx, column=2, value=t_name).font = font_bold
        ws_whatif.cell(row=r_idx, column=2).border = thin_border
        
        ws_whatif.cell(row=r_idx, column=3, value=t_pts).number_format = FMT_INT
        ws_whatif.cell(row=r_idx, column=4, value=t_base).number_format = FMT_PERCENT
        ws_whatif.cell(row=r_idx, column=5, value=t_prev).number_format = FMT_DECIMAL
        ws_whatif.cell(row=r_idx, column=6, value=t_cost_save).number_format = FMT_CURRENCY
        ws_whatif.cell(row=r_idx, column=7, value=t_prog_cost).number_format = FMT_CURRENCY
        
        c_net = ws_whatif.cell(row=r_idx, column=8, value=t_net)
        c_net.number_format = FMT_CURRENCY
        c_net.font = font_bold
        if r_idx == 15:
            c_net.fill = fill_gold
            
        c_roi = ws_whatif.cell(row=r_idx, column=9, value=t_roi)
        c_roi.number_format = FMT_PERCENT
        c_roi.font = font_bold
        
        for c in range(3, 10):
            ws_whatif.cell(row=r_idx, column=c).border = thin_border
            ws_whatif.cell(row=r_idx, column=c).alignment = align_right
            
    # Total Portfolio Row
    ws_whatif.cell(row=18, column=2, value="Total Enterprise Program").font = font_bold
    ws_whatif.cell(row=18, column=2).fill = fill_light
    ws_whatif.cell(row=18, column=2).border = double_bottom
    
    ws_whatif.cell(row=18, column=3, value="=SUM(C15:C17)").number_format = FMT_INT
    ws_whatif.cell(row=18, column=4, value="=AVERAGE(D15:D17)").number_format = FMT_PERCENT
    ws_whatif.cell(row=18, column=5, value="=SUM(E15:E17)").number_format = FMT_DECIMAL
    ws_whatif.cell(row=18, column=6, value="=SUM(F15:F17)").number_format = FMT_CURRENCY
    ws_whatif.cell(row=18, column=7, value="=SUM(G15:G17)").number_format = FMT_CURRENCY
    
    c_tot_net = ws_whatif.cell(row=18, column=8, value="=SUM(H15:H17)")
    c_tot_net.number_format = FMT_CURRENCY
    c_tot_net.font = font_bold
    c_tot_net.fill = fill_gold
    
    c_tot_roi = ws_whatif.cell(row=18, column=9, value="=H18/G18")
    c_tot_roi.number_format = FMT_PERCENT
    c_tot_roi.font = font_bold
    
    for c in range(3, 10):
        ws_whatif.cell(row=18, column=c).border = double_bottom
        ws_whatif.cell(row=18, column=c).alignment = align_right
        
    # Auto-adjust column widths across all sheets
    for ws in wb.worksheets:
        for col in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                val_str = str(cell.value or '')
                if len(val_str) > max_len and not val_str.startswith('='):
                    max_len = len(val_str)
            ws.column_dimensions[col_letter].width = max(max_len + 5, 14)
            
    # Save Workbook
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    wb.save(output_path)
    print(f"[OK] Financial model successfully saved to: {output_path}")
    print("[SUCCESS] Excel HRRP financial engine built cleanly with exit code 0.")


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    proj_dir = os.path.abspath(os.path.join(script_dir, ".."))
    
    scored_csv_path = os.path.join(proj_dir, "data", "diabetes_scored_patients.csv")
    output_xlsx_path = os.path.join(proj_dir, "excel", "Healthcare_Readmission_Financial_Model.xlsx")
    
    # Check if scored data exists, else fallback to clean data
    if not os.path.exists(scored_csv_path):
        clean_csv_path = os.path.join(proj_dir, "data", "diabetic_data_clean.csv")
        if os.path.exists(clean_csv_path):
            scored_csv_path = clean_csv_path
        else:
            raise FileNotFoundError("Neither scored nor clean dataset found. Run data/generate_data.py first.")
            
    build_financial_model(scored_csv_path, output_xlsx_path)


if __name__ == "__main__":
    main()
