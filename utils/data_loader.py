import pandas as pd
import numpy as np
from pathlib import Path

def get_age_proxy_data(condition_name):
    base_path = Path("inputData")
    
    # Load your layers
    df_burden = pd.read_csv(base_path / "layer2_current_burden.csv")
    df_statcan = pd.read_csv(base_path / "statcan_regional_age.csv")
    
    # Get the specific condition stats
    cond_stats = df_burden[df_burden['condition'] == condition_name].iloc[0]
    
    # PREVALENCE WEIGHTING LOGIC
    # High-intensity conditions for seniors (65+)
    senior_weighted = ['COPD', 'Stroke', 'Heart Failure', 'Chronic Kidney Disease', 'Pneumonia']
    
    if condition_name in senior_weighted:
        # Calculate regional share of the provincial 65+ population
        total_seniors = df_statcan['pop_65_plus'].sum()
        df_statcan['weight'] = df_statcan['pop_65_plus'] / total_seniors
    else:
        # For general conditions (Mental Health, Diabetes), use total population share
        df_statcan['weight'] = df_statcan['pop_total'] / df_statcan['pop_total'].sum()
    
    # Apply proxy to predict regional volume and cost
    df_statcan['predicted_admissions'] = df_statcan['weight'] * cond_stats['admissions']
    df_statcan['predicted_ed_visits'] = df_statcan['weight'] * cond_stats['ed_visits']
    df_statcan['predicted_cost'] = df_statcan['weight'] * cond_stats['total_cost']
    
    return df_statcan
