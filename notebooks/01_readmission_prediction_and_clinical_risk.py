"""
Hospital Readmission Prediction & Clinical Risk Stratification Pipeline
Project: 03_Healthcare_Diabetes (Diabetes 130-US Hospitals)
Author: Senior Healthcare Data Analyst & ML Engineer

Modules:
1. Clinical Data Ingestion & Feature Engineering
2. Stratified 5-Fold Cross-Validation
3. Cost-Sensitive Model Benchmark (Logistic Regression, Random Forest, LightGBM, XGBoost)
4. Decision Threshold Optimization ($15,000 False Negative vs $150 False Positive)
5. SHAP Global & Local Clinical Explainability (Beeswarm and Waterfall Plots)
6. Scored Patient Risk Cohort Export
"""

import os
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Headless backend
import matplotlib.pyplot as plt

from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    roc_auc_score, precision_recall_curve, auc, 
    recall_score, precision_score, f1_score, fbeta_score, confusion_matrix
)
import lightgbm as lgb
import xgboost as xgb
import shap


def load_and_preprocess_data(data_path: str):
    """Load cleaned diabetic encounter cohort and perform clinical feature engineering."""
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"Cleaned dataset not found at {data_path}")
        
    df = pd.read_csv(data_path)
    print(f"Loaded {len(df):,} encounters from {data_path}")
    
    # 1. Feature Engineering
    df['total_prior_visits'] = df['number_inpatient'] + df['number_emergency'] + df['number_outpatient']
    df['inpatient_visit_ratio'] = df['number_inpatient'] / (df['total_prior_visits'] + 1.0)
    df['medication_intensity'] = df['num_medications'] / df['time_in_hospital'].clip(lower=1)
    df['lab_intensity'] = df['num_lab_procedures'] / df['time_in_hospital'].clip(lower=1)
    df['high_comorbidity_flag'] = (df['number_diagnoses'] >= 9).astype(int)
    df['insulin_treatment_flag'] = df['insulin'].isin(['Steady', 'Up', 'Down']).astype(int)
    
    # Target
    y = df['readmitted_30'].values
    
    # Feature subsets
    num_cols = [
        'time_in_hospital', 'num_lab_procedures', 'num_procedures', 'num_medications',
        'number_outpatient', 'number_emergency', 'number_inpatient', 'total_prior_visits',
        'inpatient_visit_ratio', 'medication_intensity', 'lab_intensity',
        'number_diagnoses', 'high_comorbidity_flag', 'insulin_treatment_flag'
    ]
    
    cat_cols = [
        'race', 'gender', 'age', 'admission_type_id', 'discharge_disposition_id',
        'admission_source_id', 'primary_diag_category', 'max_glu_serum', 'A1Cresult',
        'change', 'diabetesMed', 'insulin', 'metformin'
    ]
    
    for c in cat_cols:
        df[c] = df[c].fillna('Unknown').astype(str)
        
    for c in num_cols:
        df[c] = df[c].fillna(0.0).astype(float)
        
    X_df = df[num_cols + cat_cols].copy()
    
    preprocessor = ColumnTransformer(
        transformers=[
            ('num', StandardScaler(), num_cols),
            ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), cat_cols)
        ]
    )
    
    return df, X_df, y, preprocessor, num_cols, cat_cols


def evaluate_models(X_df, y, preprocessor):
    """Benchmark Candidate Classifiers under Stratified 5-Fold Cross-Validation."""
    print("\n" + "="*70)
    print("STEP 1: BENCHMARKING CANDIDATE MODELS (STRATIFIED 5-FOLD CV)")
    print("="*70)
    
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    
    models = {
        'Logistic Regression (Balanced)': LogisticRegression(max_iter=1000, class_weight='balanced', random_state=42),
        'Random Forest': RandomForestClassifier(n_estimators=100, max_depth=10, min_samples_split=20, random_state=42, class_weight='balanced'),
        'LightGBM': lgb.LGBMClassifier(n_estimators=150, max_depth=6, learning_rate=0.03, scale_pos_weight=4.0, random_state=42, verbose=-1),
        'XGBoost': xgb.XGBClassifier(n_estimators=150, max_depth=5, learning_rate=0.03, scale_pos_weight=4.0, random_state=42, eval_metric='logloss')
    }
    
    results = {}
    
    # We will fit models and store out-of-fold probability predictions
    oof_predictions = {name: np.zeros(len(y)) for name in models}
    
    for name, model in models.items():
        print(f"Evaluating {name}...")
        roc_list = []
        prauc_list = []
        
        for fold, (train_idx, val_idx) in enumerate(cv.split(X_df, y), 1):
            X_train, y_train = X_df.iloc[train_idx], y[train_idx]
            X_val, y_val = X_df.iloc[val_idx], y[val_idx]
            
            # Preprocess
            pipe = Pipeline([
                ('pre', preprocessor),
                ('clf', model)
            ])
            pipe.fit(X_train, y_train)
            
            val_probs = pipe.predict_proba(X_val)[:, 1]
            oof_predictions[name][val_idx] = val_probs
            
            roc = roc_auc_score(y_val, val_probs)
            precision_vals, recall_vals, _ = precision_recall_curve(y_val, val_probs)
            pr_auc_score = auc(recall_vals, precision_vals)
            
            roc_list.append(roc)
            prauc_list.append(pr_auc_score)
            
        mean_roc = np.mean(roc_list)
        mean_prauc = np.mean(prauc_list)
        results[name] = {
            'ROC-AUC': mean_roc,
            'PR-AUC': mean_prauc
        }
        print(f" -> {name}: Mean ROC-AUC = {mean_roc:.4f}, Mean PR-AUC = {mean_prauc:.4f}")
        
    return results, oof_predictions


def optimize_cost_sensitive_threshold(y_true, y_probs, cost_fn=15000.0, cost_fp=150.0):
    """
    Tune Decision Threshold reflecting Clinical & HRRP Economics:
    Cost = (FN * $15,000) + (FP * $150) + (TP * $150)
    """
    print("\n" + "="*70)
    print("STEP 2: COST-SENSITIVE THRESHOLD OPTIMIZATION")
    print(f"Cost of False Negative (Unmanaged Readmission): ${cost_fn:,.0f}")
    print(f"Cost of False Positive (Nurse Outreach / Care Coordination): ${cost_fp:,.0f}")
    print("="*70)
    
    thresholds = np.linspace(0.10, 0.60, 51)
    best_threshold = 0.50
    min_cost = float('inf')
    best_metrics = {}
    
    curve_data = []
    
    for thresh in thresholds:
        preds = (y_probs >= thresh).astype(int)
        tn, fp, fn, tp = confusion_matrix(y_true, preds).ravel()
        
        # Clinical cost
        total_cost = (fn * cost_fn) + (fp * cost_fp) + (tp * cost_fp)
        recall = recall_score(y_true, preds)
        precision = precision_score(y_true, preds, zero_division=0)
        f1 = f1_score(y_true, preds, zero_division=0)
        f2 = fbeta_score(y_true, preds, beta=2.0, zero_division=0)
        
        curve_data.append({
            'threshold': thresh,
            'total_cost': total_cost,
            'recall': recall,
            'precision': precision,
            'f2': f2
        })
        
        if total_cost < min_cost:
            min_cost = total_cost
            best_threshold = thresh
            best_metrics = {
                'threshold': thresh,
                'min_cost': total_cost,
                'recall': recall,
                'precision': precision,
                'f1': f1,
                'f2': f2,
                'tp': tp,
                'fp': fp,
                'fn': fn,
                'tn': tn
            }
            
    # Baseline comparison at 0.50 threshold
    base_preds = (y_probs >= 0.50).astype(int)
    btn, bfp, bfn, btp = confusion_matrix(y_true, base_preds).ravel()
    base_cost = (bfn * cost_fn) + (bfp * cost_fp) + (btp * cost_fp)
    base_recall = recall_score(y_true, base_preds)
    
    savings = base_cost - min_cost
    
    print(f"Baseline Threshold (0.50):")
    print(f"  Recall: {base_recall:.1%}, False Negatives: {bfn:,}, Total Cost: ${base_cost:,.0f}")
    print(f"\nOptimal Clinical Threshold ({best_metrics['threshold']:.2f}):")
    print(f"  Recall: {best_metrics['recall']:.1%}, Precision: {best_metrics['precision']:.1%}, F2-Score: {best_metrics['f2']:.3f}")
    print(f"  True Positives Captured: {best_metrics['tp']:,} / {best_metrics['tp'] + best_metrics['fn']:,}")
    print(f"  False Negatives Reduced: {bfn:,} -> {best_metrics['fn']:,}")
    print(f"  Total Cost at Optimal: ${min_cost:,.0f}")
    print(f"  Net Economic Savings: ${savings:,.0f} ({savings/base_cost*100:.1f}% cost reduction)")
    
    return best_threshold, best_metrics, pd.DataFrame(curve_data)


def explain_with_shap(model_pipeline, X_df, figures_dir: str):
    """Generate SHAP TreeExplainer Beeswarm & Waterfall Plots for Clinical Interpretability."""
    print("\n" + "="*70)
    print("STEP 3: SHAP CLINICAL FEATURE ATTRIBUTION & EXPLAINABILITY")
    print("="*70)
    
    os.makedirs(figures_dir, exist_ok=True)
    
    preprocessor = model_pipeline.named_steps['pre']
    clf = model_pipeline.named_steps['clf']
    
    # Transform sample for SHAP
    X_sample = X_df.sample(min(1000, len(X_df)), random_state=42)
    X_trans = preprocessor.transform(X_sample)
    
    # Get feature names from column transformer
    cat_encoder = preprocessor.named_transformers_['cat']
    cat_cols_encoded = cat_encoder.get_feature_names_out()
    num_cols = preprocessor.transformers_[0][2]
    all_feature_names = list(num_cols) + list(cat_cols_encoded)
    
    X_trans_df = pd.DataFrame(X_trans, columns=all_feature_names)
    
    # Explainer
    explainer = shap.TreeExplainer(clf)
    shap_values = explainer(X_trans_df)
    
    # 1. Beeswarm Plot
    plt.figure(figsize=(10, 7))
    shap.plots.beeswarm(shap_values, max_display=15, show=False)
    plt.title("SHAP Clinical Readmission Risk Drivers (Top 15 Features)", fontsize=13, fontweight='bold', pad=15)
    plt.tight_layout()
    beeswarm_path = os.path.join(figures_dir, "shap_summary_beeswarm.png")
    plt.savefig(beeswarm_path, dpi=200, bbox_inches='tight')
    plt.close()
    print(f"[OK] Saved SHAP Beeswarm Plot: {beeswarm_path}")
    
    # 2. Local Waterfall Plot for High-Risk Patient
    # Find patient with highest predicted probability in sample
    preds = clf.predict_proba(X_trans)[:, 1]
    high_risk_idx = int(np.argmax(preds))
    
    plt.figure(figsize=(10, 6))
    shap.plots.waterfall(shap_values[high_risk_idx], max_display=12, show=False)
    plt.title(f"SHAP Patient Decision Attribution (Risk Probability: {preds[high_risk_idx]:.1%})", fontsize=12, fontweight='bold', pad=15)
    plt.tight_layout()
    waterfall_path = os.path.join(figures_dir, "shap_patient_waterfall.png")
    plt.savefig(waterfall_path, dpi=200, bbox_inches='tight')
    plt.close()
    print(f"[OK] Saved SHAP Patient Waterfall Plot: {waterfall_path}")


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    proj_dir = os.path.abspath(os.path.join(script_dir, ".."))
    data_dir = os.path.join(proj_dir, "data")
    figures_dir = os.path.join(script_dir, "figures")
    
    clean_csv_path = os.path.join(data_dir, "diabetic_data_clean.csv")
    
    # Load and preprocess
    df_raw, X_df, y, preprocessor, num_cols, cat_cols = load_and_preprocess_data(clean_csv_path)
    
    # 1. Benchmark models
    results, oof_preds = evaluate_models(X_df, y, preprocessor)
    
    # Select best model for deployment: LightGBM / XGBoost
    best_model_name = 'LightGBM'
    best_probs = oof_preds[best_model_name]
    
    # 2. Optimize Cost-Sensitive Threshold
    opt_thresh, opt_metrics, curve_df = optimize_cost_sensitive_threshold(y, best_probs)
    
    # 3. Fit Final Production Pipeline for SHAP & Scoring
    print("\nTraining final production LightGBM pipeline...")
    final_pipeline = Pipeline([
        ('pre', preprocessor),
        ('clf', lgb.LGBMClassifier(n_estimators=150, max_depth=6, learning_rate=0.03, scale_pos_weight=4.0, random_state=42, verbose=-1))
    ])
    final_pipeline.fit(X_df, y)
    
    # Generate SHAP plots
    explain_with_shap(final_pipeline, X_df, figures_dir)
    
    # 4. Generate Scored Patient Cohort
    print("\nExporting scored patient risk cohort...")
    final_probs = final_pipeline.predict_proba(X_df)[:, 1]
    
    df_scored = df_raw.copy()
    df_scored['model_risk_score'] = np.round(final_probs, 4)
    
    def assign_tier(p):
        if p < 0.15:
            return 'Low'
        elif p < 0.35:
            return 'Medium'
        else:
            return 'High'
            
    df_scored['risk_tier'] = df_scored['model_risk_score'].apply(assign_tier)
    
    output_scored_path = os.path.join(data_dir, "diabetes_scored_patients.csv")
    export_cols = [
        'encounter_id', 'patient_nbr', 'age', 'gender', 'primary_diag_category',
        'time_in_hospital', 'number_inpatient', 'number_emergency', 'number_diagnoses',
        'insulin', 'A1Cresult', 'readmitted_30', 'model_risk_score', 'risk_tier'
    ]
    df_scored[export_cols].to_csv(output_scored_path, index=False)
    print(f"[OK] Saved scored patient risk dataset ({len(df_scored):,} rows) to {output_scored_path}")
    
    # Risk Tier distribution
    tier_counts = df_scored['risk_tier'].value_counts()
    print("\nRisk Tier Stratification:")
    for tier, count in tier_counts.items():
        tier_sub = df_scored[df_scored['risk_tier'] == tier]
        tier_readmit = tier_sub['readmitted_30'].mean() * 100
        print(f"  {tier:6s}: {count:,} patients ({count/len(df_scored)*100:.1f}%), 30-Day Readmit Rate: {tier_readmit:.2f}%")
        
    print("\n[SUCCESS] Machine learning risk prediction pipeline completed with exit code 0.")


if __name__ == "__main__":
    main()
