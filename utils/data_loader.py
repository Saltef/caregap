import pandas as pd
import numpy as np
from pathlib import Path

# Paths based on your statcan.py output
ROOT = Path(__file__).parent.parent
PROCESSED_DIR = ROOT / "data" / "processed"
INPUT_DIR = ROOT / "inputData"

def get_projected_lhin_map(condition_name, target_year=2024):
    """
    Combines StatCan LHIN populations with Condition baseline rates.
    Uses target_year to scale the provincial burden.
    """
    # 1. Load Data
    df_burden = pd.read_csv(INPUT_DIR / "layer2_current_burden.csv")
    # StatCan fetcher creates this: LHIN, year, age_group, population
    df_pop = pd.read_csv(PROCESSED_DIR / "population_by_age_lhin.csv")
    
    # 2. Extract Baseline (2024) and Condition stats
    cond_stats = df_burden[df_burden['condition'] == condition_name].iloc[0]
    
    # 3. Aggregate LHIN data for the target year
    df_year = df_pop[df_pop['year'] == target_year].copy()
    if df_year.empty:
        # Fallback: If projection year isn't in LHIN file, use max year available
        df_year = df_pop[df_pop['year'] == df_pop['year'].max()].copy()

    # 4. Proxy Weights (Senior Skew)
    senior_groups = ['65–74', '75–84', '85+']
    lhin_summary = df_year.groupby('LHIN').apply(
        lambda x: pd.Series({
            'pop_total': x['population'].sum(),
            'pop_65_plus': x[x['age_group'].isin(senior_groups)]['population'].sum()
        })
    ).reset_index()

    # 5. Apply "Age Inflation" logic
    # Older regions get more weight for conditions like COPD
    senior_weighted = ['COPD', 'Stroke', 'Pneumonia', 'Heart Failure']
    
    if condition_name in senior_weighted:
        total_seniors = lhin_summary['pop_65_plus'].sum()
        lhin_summary['weight'] = lhin_summary['pop_65_plus'] / total_seniors
    else:
        lhin_summary['weight'] = lhin_summary['pop_total'] / lhin_summary['pop_total'].sum()

    # 6. Final Calculations
    lhin_summary['predicted_admissions'] = lhin_summary['weight'] * cond_stats['admissions']
    lhin_summary['predicted_cost'] = lhin_summary['weight'] * cond_stats['total_cost']
    
    return lhin_summary
